"""
========================================================================
DRENAET-RH — ImportService
========================================================================
Orchestrateur principal du pipeline d'import Excel.

Architecture en 2 PHASES :

┌─── PHASE 1 : DRY-RUN (simulation) ────────────────────────────────┐
│                                                                    │
│  1. ExcelReader        → lit le fichier                            │
│  2. ColumnMapper       → mappe les colonnes                        │
│  3. DataValidator      → valide/normalise chaque ligne             │
│  4. MergeStrategy      → décide CREATE/UPDATE/SKIP par ligne       │
│  5. Rapport détaillé   → SANS ÉCRITURE BD                          │
│                                                                    │
│  Retourne : ImportPreviewReport                                    │
└────────────────────────────────────────────────────────────────────┘
                    ↓
       User confirme dans l'UI ?
                    ↓
┌─── PHASE 2 : EXÉCUTION RÉELLE ────────────────────────────────────┐
│                                                                    │
│  1. Rejoue les décisions du dry-run                                │
│  2. Écrit dans SQLite via PersonnelService (avec audit trail)      │
│  3. Enregistre ImportLog + ImportDetail                            │
│                                                                    │
│  Retourne : ImportExecutionReport                                  │
└────────────────────────────────────────────────────────────────────┘
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.models import get_session
from src.models.import_log import ImportLog, ImportDetail

from src.services.personnel_service import (
    PersonnelService,
    PersonnelException,
    MatriculeExistantError,
)
from src.services.structure_service import StructureService

from src.services.import_pipeline.excel_reader import ExcelReader
from src.services.import_pipeline.column_mapper import ColumnMapper
from src.services.import_pipeline.data_validator import DataValidator
from src.services.import_pipeline.merge_strategy import (
    MergeStrategy, Strategy, Action, MergeDecision
)


# ========================================================================
# RAPPORTS
# ========================================================================
class ImportPreviewReport:
    """Rapport de la PHASE 1 (dry-run)."""

    def __init__(self):
        self.file_info: Dict[str, Any] = {}
        self.sheet_name: str = ""
        self.strategy: str = ""

        self.column_mapping: Dict[str, str] = {}
        self.unmapped_columns: List[str] = []
        self.missing_required_fields: List[str] = []
        self.warnings: List[str] = []

        self.nb_lignes_lues: int = 0
        self.nb_a_creer: int = 0
        self.nb_a_modifier: int = 0
        self.nb_a_ignorer: int = 0
        self.nb_erreurs: int = 0

        # Détail des décisions
        self.decisions: List[Dict[str, Any]] = []
        # Détail des erreurs de validation
        self.errors: List[Dict[str, Any]] = []
        # Résumé des types de changements
        self.changement_summary: Dict[str, int] = {}

        self.duree_ms: int = 0
        self.can_proceed: bool = False  # True si l'import peut être confirmé

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_info": self.file_info,
            "sheet_name": self.sheet_name,
            "strategy": self.strategy,
            "column_mapping": self.column_mapping,
            "unmapped_columns": self.unmapped_columns,
            "missing_required_fields": self.missing_required_fields,
            "warnings": self.warnings,
            "nb_lignes_lues": self.nb_lignes_lues,
            "nb_a_creer": self.nb_a_creer,
            "nb_a_modifier": self.nb_a_modifier,
            "nb_a_ignorer": self.nb_a_ignorer,
            "nb_erreurs": self.nb_erreurs,
            "decisions": self.decisions,
            "errors": self.errors,
            "changement_summary": self.changement_summary,
            "duree_ms": self.duree_ms,
            "can_proceed": self.can_proceed,
        }


class ImportExecutionReport:
    """Rapport de la PHASE 2 (exécution réelle)."""

    def __init__(self):
        self.import_log_id: Optional[int] = None
        self.nb_crees: int = 0
        self.nb_modifies: int = 0
        self.nb_ignores: int = 0
        self.nb_erreurs: int = 0
        self.statut: str = "SUCCESS"  # SUCCESS | PARTIAL | FAILED
        self.duree_ms: int = 0
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "import_log_id": self.import_log_id,
            "nb_crees": self.nb_crees,
            "nb_modifies": self.nb_modifies,
            "nb_ignores": self.nb_ignores,
            "nb_erreurs": self.nb_erreurs,
            "statut": self.statut,
            "duree_ms": self.duree_ms,
            "errors": self.errors,
        }


# ========================================================================
# SERVICE PRINCIPAL
# ========================================================================
class ImportService:
    """Service d'orchestration du pipeline d'import Excel."""

    # ====================================================================
    # PHASE 1 : DRY-RUN
    # ====================================================================
    @staticmethod
    def dry_run(
        file_path: str,
        sheet_name: Optional[str] = None,
        strategy: str = "UPSERT",
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> ImportPreviewReport:
        """
        Simule un import sans écrire en BD.

        Args:
            file_path: chemin du fichier Excel
            sheet_name: feuille à traiter (None = première feuille)
            strategy: UPSERT / INSERT_ONLY / UPDATE_ONLY / REPLACE
            custom_mapping: mapping manuel {champ_canonique: nom_colonne_excel}
                (utilisé pour corriger le mapping auto)

        Returns:
            ImportPreviewReport complet
        """
        report = ImportPreviewReport()
        report.strategy = strategy
        t0 = time.time()

        # 1. Lire le fichier
        with ExcelReader(file_path) as reader:
            report.file_info = reader.get_file_info()

            # Choisir la feuille
            sheets = reader.get_sheet_names()
            if not sheets:
                report.errors.append({"raison": "Aucune feuille dans le fichier"})
                report.duree_ms = int((time.time() - t0) * 1000)
                return report

            selected_sheet = sheet_name or sheets[0]
            report.sheet_name = selected_sheet

            try:
                headers, rows = reader.read_sheet(selected_sheet)
            except Exception as e:
                report.errors.append({"raison": f"Lecture feuille échouée : {e}"})
                report.duree_ms = int((time.time() - t0) * 1000)
                return report

            report.nb_lignes_lues = len(rows)

        # 2. Mapping des colonnes
        mapper = ColumnMapper()
        map_result = mapper.auto_map(headers)

        # Appliquer le mapping personnalisé si fourni
        if custom_mapping:
            for canonical, excel_col in custom_mapping.items():
                map_result["mapping"][canonical] = excel_col
            # Recalculer missing_required_fields
            from src.services.import_pipeline.column_mapper import CHAMPS_OBLIGATOIRES
            map_result["missing_required_fields"] = [
                c for c in CHAMPS_OBLIGATOIRES
                if c not in map_result["mapping"]
            ]

        report.column_mapping = map_result["mapping"]
        report.unmapped_columns = map_result["unmapped_excel_columns"]
        report.missing_required_fields = map_result["missing_required_fields"]
        report.warnings = map_result["warnings"]

        # Si champs obligatoires manquants, on s'arrête là
        if report.missing_required_fields:
            report.can_proceed = False
            report.duree_ms = int((time.time() - t0) * 1000)
            return report

        # 3. Valider + décider pour chaque row
        try:
            strategy_enum = Strategy.from_string(strategy)
        except ValueError as e:
            report.errors.append({"raison": str(e)})
            report.duree_ms = int((time.time() - t0) * 1000)
            return report

        validator = DataValidator()
        merger = MergeStrategy(strategy_enum)

        for excel_row in rows:
            # Appliquer le mapping
            mapped_row = mapper.apply_mapping(excel_row, report.column_mapping)

            # Valider
            valid_row, validation_errors = validator.validate_row(mapped_row)

            if validation_errors:
                report.nb_erreurs += 1
                report.errors.append({
                    "row_number": excel_row.get("_row_number"),
                    "matricule": mapped_row.get("matricule"),
                    "raisons": validation_errors,
                })
                continue

            # Chercher l'agent existant
            existing = PersonnelService.get_by_matricule(valid_row["matricule"])

            # Décider
            decision = merger.decide(valid_row, existing)
            report.decisions.append(decision.to_dict())

            # Compter
            if decision.action == Action.CREATE:
                report.nb_a_creer += 1
            elif decision.action == Action.UPDATE:
                report.nb_a_modifier += 1
                # Comptabiliser les types de changements
                for field in decision.changes.keys():
                    report.changement_summary[field] = (
                        report.changement_summary.get(field, 0) + 1
                    )
            else:
                report.nb_a_ignorer += 1

        report.duree_ms = int((time.time() - t0) * 1000)
        report.can_proceed = report.nb_erreurs == 0 or (
            report.nb_a_creer + report.nb_a_modifier > 0
        )
        return report

    # ====================================================================
    # PHASE 2 : EXÉCUTION RÉELLE
    # ====================================================================
    @staticmethod
    def execute(
        preview_report: ImportPreviewReport,
        user_login: str,
        user_role: str = None,
        commentaire: str = None,
    ) -> ImportExecutionReport:
        """
        Exécute réellement l'import en se basant sur le rapport de dry-run.

        Args:
            preview_report: rapport retourné par dry_run()
            user_login: qui effectue l'import
            user_role: rôle utilisateur (admin, operateur)
            commentaire: note optionnelle

        Returns:
            ImportExecutionReport avec compteurs finaux
        """
        exec_report = ImportExecutionReport()
        t0 = time.time()

        if not preview_report.can_proceed:
            exec_report.statut = "FAILED"
            exec_report.errors.append(
                "Le dry-run a échoué (champs obligatoires manquants ou erreurs bloquantes)"
            )
            exec_report.duree_ms = int((time.time() - t0) * 1000)
            return exec_report

        # 1. Créer l'entrée ImportLog (statut initial : en cours)
        with get_session() as db:
            import_log = ImportLog(
                nom_fichier=preview_report.file_info.get("nom_fichier", "?"),
                hash_fichier=preview_report.file_info.get("hash_sha256", ""),
                taille_fichier_octets=preview_report.file_info.get("taille_octets"),
                utilisateur_login=user_login,
                utilisateur_role=user_role,
                strategie=preview_report.strategy,
                feuille_excel=preview_report.sheet_name,
                nb_lignes_lues=preview_report.nb_lignes_lues,
                statut="IN_PROGRESS",
                commentaire=commentaire,
            )
            db.add(import_log)
            db.flush()
            exec_report.import_log_id = import_log.id
            import_log_id = import_log.id

        # 2. Rejouer les décisions du dry-run
        for decision_dict in preview_report.decisions:
            action = decision_dict["action"]
            row_number = decision_dict["row_number"]

            # Retrouver la row complète depuis les décisions du preview
            # (dans la vraie vie, on relit le fichier - ici simplifié)
            # ⚠️ Pour un import 100% robuste, il faudrait re-parser le fichier
            #    et re-valider. Ici on suppose que le dry-run est frais (juste avant).

            # Note : on stocke les données minimales dans decision_dict.
            # Pour un vrai import, il faut re-parser le fichier ici.
            # Simplification : on va re-parser dans une V2 optimisée.

            try:
                if action == "CREATE":
                    ImportService._execute_create(
                        decision_dict, user_login, user_role, import_log_id
                    )
                    exec_report.nb_crees += 1

                elif action == "UPDATE":
                    ImportService._execute_update(
                        decision_dict, user_login, user_role, import_log_id
                    )
                    exec_report.nb_modifies += 1

                else:
                    # SKIP_*
                    exec_report.nb_ignores += 1
                    ImportService._log_detail(
                        import_log_id, row_number,
                        decision_dict.get("matricule"),
                        "SKIPPED",
                        {"raison": decision_dict.get("reason", "")},
                    )

            except Exception as e:
                exec_report.nb_erreurs += 1
                exec_report.errors.append(
                    f"Ligne {row_number} ({decision_dict.get('matricule')}) : {e}"
                )
                ImportService._log_detail(
                    import_log_id, row_number,
                    decision_dict.get("matricule"),
                    "ERROR",
                    {"erreur": str(e)},
                    message_erreur=str(e),
                )

        # 3. Mettre à jour ImportLog avec les compteurs finaux
        exec_report.duree_ms = int((time.time() - t0) * 1000)

        if exec_report.nb_erreurs == 0 and preview_report.nb_erreurs == 0:
            exec_report.statut = "SUCCESS"
        elif exec_report.nb_crees + exec_report.nb_modifies > 0:
            exec_report.statut = "PARTIAL"
        else:
            exec_report.statut = "FAILED"

        with get_session() as db:
            log = db.query(ImportLog).filter_by(id=import_log_id).first()
            if log:
                log.nb_crees = exec_report.nb_crees
                log.nb_modifies = exec_report.nb_modifies
                log.nb_ignores = exec_report.nb_ignores
                log.nb_erreurs = exec_report.nb_erreurs
                log.statut = exec_report.statut
                log.duree_ms = exec_report.duree_ms
                log.rapport_json = json.dumps(
                    exec_report.to_dict(),
                    ensure_ascii=False,
                    default=str,
                )
                db.flush()

        return exec_report

    # ====================================================================
    # HELPERS PRIVÉS
    # ====================================================================
    @staticmethod
    def _resolve_structure_id(structure_name: Any) -> Optional[int]:
        """
        Résout un nom de structure en structure_id.
        Utilise get_or_create : crée la structure si absente.
        """
        if not structure_name:
            return None
        struct = StructureService.get_or_create(
            nom=str(structure_name).strip(),
            type="Autre",
        )
        return struct["id"]

    @staticmethod
    def _prepare_data_for_service(row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prépare les données brutes pour PersonnelService.
        Résout la structure (nom → structure_id) et filtre les champs.
        """
        # Résoudre la structure
        structure_id = ImportService._resolve_structure_id(
            row_data.get("structure")
        )

        # Champs supportés par PersonnelService
        data = {
            "matricule": row_data.get("matricule"),
            "nom": row_data.get("nom"),
            "prenoms": row_data.get("prenoms"),
            "sexe": row_data.get("sexe"),
            "date_naissance": row_data.get("date_naissance"),
            "lieu_naissance": row_data.get("lieu_naissance"),
            "situation_matrimoniale": row_data.get("situation_matrimoniale"),
            "telephone": row_data.get("telephone"),
            "email": row_data.get("email"),
            "residence": row_data.get("residence"),
            "emploi": row_data.get("emploi"),
            "grade": row_data.get("grade"),
            "fonction": row_data.get("fonction"),
            "structure_id": structure_id,
            "date_prise_service": row_data.get("date_prise_service"),
            "date_affectation": row_data.get("date_affectation"),
            "statut": row_data.get("statut", "Actif"),
        }
        # Retirer les None pour ne pas écraser les valeurs existantes lors d'UPDATE
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def _execute_create(
        decision_dict: Dict[str, Any],
        user_login: str,
        user_role: str,
        import_log_id: int,
    ):
        """Exécute un CREATE via PersonnelService."""
        row_data = decision_dict.get("row_data", {})
        data = ImportService._prepare_data_for_service(row_data)

        created = PersonnelService.create(
            data=data,
            user_login=user_login,
            user_role=user_role,
            source="IMPORT",
            import_log_id=import_log_id,
            commentaire=f"Import Excel (ligne {decision_dict.get('row_number')})",
        )

        ImportService._log_detail(
            import_log_id,
            decision_dict.get("row_number"),
            created.get("matricule"),
            "CREATED",
            {"valeurs_initiales": data},
        )

    @staticmethod
    def _execute_update(
        decision_dict: Dict[str, Any],
        user_login: str,
        user_role: str,
        import_log_id: int,
    ):
        """Exécute un UPDATE via PersonnelService."""
        row_data = decision_dict.get("row_data", {})
        existing_agent = decision_dict.get("existing_agent")
        if not existing_agent:
            raise ValueError("existing_agent manquant pour UPDATE")

        agent_id = existing_agent.get("id")
        data = ImportService._prepare_data_for_service(row_data)
        # On ne modifie pas le matricule
        data.pop("matricule", None)

        PersonnelService.update(
            agent_id=agent_id,
            data=data,
            user_login=user_login,
            user_role=user_role,
            source="IMPORT",
            import_log_id=import_log_id,
            commentaire=f"Import Excel (ligne {decision_dict.get('row_number')})",
        )

        ImportService._log_detail(
            import_log_id,
            decision_dict.get("row_number"),
            row_data.get("matricule"),
            "UPDATED",
            {"changements": decision_dict.get("changes", {})},
        )

    @staticmethod
    def _log_detail(
        import_log_id: int,
        row_number: int,
        matricule: str,
        action: str,
        changements: Dict[str, Any],
        message_erreur: str = None,
    ):
        """Enregistre un ImportDetail."""
        with get_session() as db:
            detail = ImportDetail(
                import_log_id=import_log_id,
                numero_ligne_excel=row_number,
                matricule=matricule,
                action=action,
                changements_json=json.dumps(changements, ensure_ascii=False, default=str),
                message_erreur=message_erreur,
            )
            db.add(detail)
            db.flush()