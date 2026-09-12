"""
========================================================================
DRENAET-RH — MergeStrategy
========================================================================
Stratégies de fusion entre les données Excel et la BD existante.

4 stratégies disponibles (l'utilisateur choisit à chaque import) :

1. UPSERT (défaut) : créer si absent, mettre à jour si présent
   → Comportement classique, cas d'usage 90% du temps
   → Cas d'usage : import mensuel classique

2. INSERT_ONLY : créer si absent, ignorer si présent
   → PROTÈGE les modifications manuelles faites dans le logiciel
   → Cas d'usage : ajouter de nouveaux agents sans écraser les existants

3. UPDATE_ONLY : mettre à jour si présent, ignorer si absent
   → Ne crée AUCUN nouvel agent
   → Cas d'usage : corriger en masse certains champs sur des agents connus

4. REPLACE : vider une structure puis réimporter (avec confirmation forte)
   → DESTRUCTIF - à utiliser avec précaution
   → Cas d'usage : reset complet d'un établissement (rare)

Chaque stratégie retourne une DÉCISION par row (sans écrire en BD).
L'écriture réelle est faite par ImportService en 2 phases (dry-run + réel).
"""

from enum import Enum
from typing import Dict, List, Any, Optional


# ========================================================================
# ÉNUMÉRATION DES STRATÉGIES
# ========================================================================
class Strategy(Enum):
    UPSERT = "UPSERT"
    INSERT_ONLY = "INSERT_ONLY"
    UPDATE_ONLY = "UPDATE_ONLY"
    REPLACE = "REPLACE"

    @classmethod
    def from_string(cls, value: str) -> "Strategy":
        """Convertit une string en Strategy enum."""
        v = str(value).strip().upper()
        for s in cls:
            if s.value == v:
                return s
        raise ValueError(f"Stratégie inconnue : {value}. Valeurs : {[s.value for s in cls]}")


# ========================================================================
# ÉNUMÉRATION DES ACTIONS
# ========================================================================
class Action(Enum):
    CREATE = "CREATE"           # créer un nouvel agent
    UPDATE = "UPDATE"           # mettre à jour un agent existant
    SKIP_EXISTS = "SKIP_EXISTS"  # ignorer car l'agent existe déjà
    SKIP_NOT_FOUND = "SKIP_NOT_FOUND"  # ignorer car l'agent n'existe pas
    SKIP_NO_CHANGE = "SKIP_NO_CHANGE"  # ignorer car aucun changement détecté


# ========================================================================
# DÉCISION (résultat par row)
# ========================================================================
class MergeDecision:
    """Décision prise par MergeStrategy pour une row donnée."""

    def __init__(
        self,
        action: Action,
        row_data: Dict[str, Any],
        existing_agent: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, List]] = None,
        reason: Optional[str] = None,
    ):
        """
        Args:
            action: décision prise (CREATE/UPDATE/SKIP_*)
            row_data: données de la ligne Excel (déjà validées)
            existing_agent: si trouvé en BD, l'agent existant (dict complet)
            changes: si UPDATE, dict {champ: [avant, après]}
            reason: raison humainement lisible
        """
        self.action = action
        self.row_data = row_data
        self.existing_agent = existing_agent
        self.changes = changes or {}
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "matricule": self.row_data.get("matricule"),
            "row_number": self.row_data.get("_row_number"),
            "existing_agent_id": self.existing_agent.get("id") if self.existing_agent else None,
            "existing_agent": self.existing_agent,
            "row_data": self.row_data,
            "changes": self.changes,
            "reason": self.reason,
        }


# ========================================================================
# CLASSE DE BASE
# ========================================================================
class MergeStrategy:
    """Décide QUOI faire de chaque row Excel (sans écrire en BD)."""

    # Champs à comparer pour détecter des changements
    # (on ne compare pas structure_id direct car on résout structure par nom)
    FIELDS_TO_COMPARE = [
        "nom", "prenoms", "sexe", "date_naissance", "lieu_naissance",
        "situation_matrimoniale", "telephone", "email", "residence",
        "emploi", "grade", "fonction", "date_prise_service",
        "date_affectation", "statut",
    ]

    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    # ====================================================================
    def decide(
        self,
        excel_row: Dict[str, Any],
        existing_agent: Optional[Dict[str, Any]],
    ) -> MergeDecision:
        """
        Décide quoi faire d'une row Excel.

        Args:
            excel_row: row validée par DataValidator (avec matricule normalisé)
            existing_agent: agent existant en BD (None si pas trouvé)

        Returns:
            MergeDecision avec action + données
        """
        # Cas 1 : l'agent existe en BD
        if existing_agent:
            return self._decide_existing(excel_row, existing_agent)
        # Cas 2 : l'agent n'existe pas
        return self._decide_new(excel_row)

    # ====================================================================
    def _decide_new(self, excel_row: Dict[str, Any]) -> MergeDecision:
        """Décide pour un nouvel agent (non trouvé en BD)."""
        if self.strategy in (Strategy.UPSERT, Strategy.INSERT_ONLY, Strategy.REPLACE):
            return MergeDecision(
                action=Action.CREATE,
                row_data=excel_row,
                reason="Nouvel agent à créer",
            )
        # UPDATE_ONLY : on ignore les nouveaux
        return MergeDecision(
            action=Action.SKIP_NOT_FOUND,
            row_data=excel_row,
            reason="Stratégie UPDATE_ONLY : nouvel agent ignoré",
        )

    # ====================================================================
    def _decide_existing(
        self,
        excel_row: Dict[str, Any],
        existing: Dict[str, Any],
    ) -> MergeDecision:
        """Décide pour un agent existant en BD."""
        # INSERT_ONLY : on protège l'existant, on ne fait rien
        if self.strategy == Strategy.INSERT_ONLY:
            return MergeDecision(
                action=Action.SKIP_EXISTS,
                row_data=excel_row,
                existing_agent=existing,
                reason="Stratégie INSERT_ONLY : agent existant protégé",
            )

        # Pour UPSERT, UPDATE_ONLY et REPLACE : on va potentiellement update
        # → détecter les changements réels
        changes = self._detect_changes(excel_row, existing)

        if not changes:
            return MergeDecision(
                action=Action.SKIP_NO_CHANGE,
                row_data=excel_row,
                existing_agent=existing,
                reason="Aucun changement détecté",
            )

        return MergeDecision(
            action=Action.UPDATE,
            row_data=excel_row,
            existing_agent=existing,
            changes=changes,
            reason=f"{len(changes)} champ(s) modifié(s)",
        )

    # ====================================================================
    def _detect_changes(
        self,
        excel_row: Dict[str, Any],
        existing: Dict[str, Any],
    ) -> Dict[str, List]:
        """
        Compare les valeurs Excel avec l'existant BD.

        Returns:
            {"champ": [ancienne_valeur, nouvelle_valeur], ...}
            Vide si aucun changement.
        """
        changes = {}
        for field in self.FIELDS_TO_COMPARE:
            if field not in excel_row:
                continue

            new_value = excel_row.get(field)
            old_value = existing.get(field)

            # Normaliser pour comparaison (None ≡ "")
            if new_value in ("", None) and old_value in ("", None):
                continue

            if self._values_differ(old_value, new_value):
                changes[field] = [
                    self._serialize(old_value),
                    self._serialize(new_value),
                ]

        # Comparer aussi la structure (via structure_nom si dispo)
        if "structure" in excel_row:
            excel_struct = str(excel_row["structure"]).strip().lower()
            existing_struct = str(existing.get("structure_nom", "")).strip().lower()
            if excel_struct and excel_struct != existing_struct:
                changes["structure"] = [
                    existing.get("structure_nom"),
                    excel_row["structure"],
                ]

        return changes

    def _values_differ(self, a: Any, b: Any) -> bool:
        """Compare 2 valeurs en tenant compte des cas date/string."""
        from datetime import date, datetime
        if a == b:
            return False
        # Cas date vs string ISO
        if isinstance(a, (date, datetime)) and isinstance(b, str):
            return a.isoformat() != b
        if isinstance(b, (date, datetime)) and isinstance(a, str):
            return b.isoformat() != a
        # Cas str vs str : insensible à espaces multiples et casse
        if isinstance(a, str) and isinstance(b, str):
            return " ".join(a.split()).lower() != " ".join(b.split()).lower()
        return True

    def _serialize(self, value: Any) -> Any:
        """Sérialise pour JSON (dates → ISO)."""
        from datetime import date, datetime
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    # ====================================================================
    @staticmethod
    def get_available_strategies() -> List[Dict[str, str]]:
        """
        Retourne la liste des stratégies disponibles avec descriptions
        (utilisé pour peupler le combo box de l'UI).
        """
        return [
            {
                "value": Strategy.UPSERT.value,
                "label": "UPSERT — Créer OU mettre à jour",
                "description": (
                    "Les nouveaux agents sont créés. "
                    "Les agents existants sont mis à jour avec les nouvelles valeurs. "
                    "Recommandé pour les imports mensuels classiques."
                ),
                "warning_level": "info",
            },
            {
                "value": Strategy.INSERT_ONLY.value,
                "label": "INSERT ONLY — Créer uniquement",
                "description": (
                    "Seuls les NOUVEAUX agents sont créés. "
                    "Les agents déjà présents sont IGNORÉS (aucune modification). "
                    "Protège les modifications manuelles faites dans le logiciel."
                ),
                "warning_level": "info",
            },
            {
                "value": Strategy.UPDATE_ONLY.value,
                "label": "UPDATE ONLY — Mettre à jour uniquement",
                "description": (
                    "Seuls les agents existants sont mis à jour. "
                    "Les nouveaux agents dans le fichier sont IGNORÉS. "
                    "Utile pour corriger en masse certains champs."
                ),
                "warning_level": "info",
            },
            {
                "value": Strategy.REPLACE.value,
                "label": "REPLACE — Remplacement complet (DESTRUCTIF)",
                "description": (
                    "⚠️ ATTENTION : supprime TOUS les agents d'une structure "
                    "puis les recrée à partir du fichier. "
                    "Les modifications manuelles seront PERDUES. "
                    "À utiliser uniquement en cas de refonte complète."
                ),
                "warning_level": "danger",
            },
        ]