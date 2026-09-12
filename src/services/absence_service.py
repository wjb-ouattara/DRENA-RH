"""
========================================================================
DRENAET-RH — AbsenceService
========================================================================
Service métier pour la gestion des absences.

Responsabilités :
- CRUD des absences (create / update / delete / search)
- Calcul automatique du nombre de jours ouvrés (weekends exclus)
- Calcul du statut automatique (Planifiée / En cours / Terminée)
- Suivi de quota annuel (30 jours ouvrés/an, uniquement "Congé annuel")
- Création automatique depuis un document généré (hook)

Le quota N'EST PAS BLOQUANT : c'est une alerte informative pour le
Chef SRH, qui garde toujours la main sur la décision finale.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from sqlalchemy import or_, func

from src.models import get_session
from src.models.absence import (
    Absence, TYPES_ABSENCE, TYPES_AVEC_QUOTA, QUOTA_JOURS_OUVRES_PAR_AN,
)
from src.models.personnel import Personnel
from src.services.settings_service import SettingsService


# ========================================================================
class AbsenceException(Exception):
    """Exception de base pour AbsenceService."""
    pass


class AbsenceIntrouvableError(AbsenceException):
    pass


class DatesInvalidesError(AbsenceException):
    pass


# ========================================================================
class AbsenceService:
    """Service métier pour la gestion des absences."""

    # ====================================================================
    # CALCULS UTILITAIRES
    # ====================================================================
    @staticmethod
    def count_business_days(date_debut: date, date_fin: date) -> int:
        """
        Compte le nombre de jours ouvrés entre 2 dates (inclus), en
        excluant les samedis et dimanches.

        Exemple : du lundi au vendredi de la même semaine = 5 jours.
        """
        if date_fin < date_debut:
            raise DatesInvalidesError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        nb_jours = 0
        current = date_debut
        while current <= date_fin:
            if current.weekday() < 5:  # 0=lundi ... 4=vendredi
                nb_jours += 1
            current += timedelta(days=1)
        return nb_jours

    @staticmethod
    def compute_statut(date_debut: date, date_fin: date) -> str:
        """Calcule le statut automatique selon la date du jour."""
        today = date.today()
        if today < date_debut:
            return "Planifiée"
        if today > date_fin:
            return "Terminée"
        return "En cours"

    # ====================================================================
    # CREATE
    # ====================================================================
    @staticmethod
    def create(
        data: Dict[str, Any],
        user_login: str,
        source: str = "MANUAL",
        document_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle absence.

        Args:
            data: {"personnel_id", "type_absence", "date_debut", "date_fin", "motif"}
            user_login: qui crée l'entrée
            source: "MANUAL" | "DOCUMENT"
            document_id: si source=DOCUMENT, l'ID du document généré lié

        Returns:
            dict de l'absence créée (incluant une clé "quota_warning" si applicable)
        """
        personnel_id = data.get("personnel_id")
        type_absence = data.get("type_absence")
        date_debut = data.get("date_debut")
        date_fin = data.get("date_fin")

        if not personnel_id:
            raise AbsenceException("personnel_id est obligatoire.")
        if type_absence not in TYPES_ABSENCE:
            raise AbsenceException(
                f"Type d'absence invalide : {type_absence}. "
                f"Valeurs acceptées : {TYPES_ABSENCE}"
            )
        if not date_debut or not date_fin:
            raise AbsenceException("date_debut et date_fin sont obligatoires.")
        if date_fin < date_debut:
            raise DatesInvalidesError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        nb_jours = AbsenceService.count_business_days(date_debut, date_fin)
        statut = AbsenceService.compute_statut(date_debut, date_fin)

        with get_session() as db:
            agent = db.query(Personnel).filter_by(id=personnel_id).first()
            if not agent:
                raise AbsenceException(f"Agent introuvable (ID={personnel_id}).")

            absence = Absence(
                personnel_id=personnel_id,
                type_absence=type_absence,
                date_debut=date_debut,
                date_fin=date_fin,
                nb_jours_ouvres=nb_jours,
                motif=data.get("motif"),
                statut=statut,
                source=source,
                document_id=document_id,
                created_by=user_login,
            )
            db.add(absence)
            db.flush()
            result = absence.to_dict()

        # Vérifier le quota APRÈS création (pour inclure cette absence dans le calcul)
        if type_absence in TYPES_AVEC_QUOTA:
            quota_status = AbsenceService.get_quota_status(
                personnel_id, annee=date_debut.year
            )
            result["quota_warning"] = quota_status if quota_status["depassement"] else None
            result["quota_status"] = quota_status

        return result

    @staticmethod
    def create_from_document(
        personnel_id: int,
        type_absence: str,
        date_debut: date,
        date_fin: date,
        motif: str,
        document_id: int,
        user_login: str,
    ) -> Dict[str, Any]:
        """
        Hook appelé depuis les formulaires de documents (Autorisation
        d'Absence, Titre de Congés) après génération réussie du PDF.

        Crée automatiquement l'entrée Absence liée au document.
        Ne lève jamais d'exception bloquante : en cas d'échec, retourne
        un dict avec "error" pour que le formulaire puisse logguer sans
        interrompre le flux (le PDF a déjà été généré avec succès).
        """
        try:
            return AbsenceService.create(
                data={
                    "personnel_id": personnel_id,
                    "type_absence": type_absence,
                    "date_debut": date_debut,
                    "date_fin": date_fin,
                    "motif": motif,
                },
                user_login=user_login,
                source="DOCUMENT",
                document_id=document_id,
            )
        except Exception as e:
            return {"error": str(e)}

    # ====================================================================
    # READ
    # ====================================================================
    @staticmethod
    def get_by_id(absence_id: int) -> Optional[Dict[str, Any]]:
        with get_session() as db:
            a = db.query(Absence).filter_by(id=absence_id).first()
            return a.to_dict() if a else None

    @staticmethod
    def search(
        query: str = "",
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recherche paginée des absences.

        filters supportés : personnel_id, type_absence, statut,
                             date_debut_min, date_debut_max
        """
        with get_session() as db:
            q = db.query(Absence).join(Personnel)

            if filters:
                if filters.get("personnel_id"):
                    q = q.filter(Absence.personnel_id == filters["personnel_id"])
                if filters.get("type_absence"):
                    q = q.filter(Absence.type_absence == filters["type_absence"])
                if filters.get("statut"):
                    q = q.filter(Absence.statut == filters["statut"])
                if filters.get("date_debut_min"):
                    q = q.filter(Absence.date_debut >= filters["date_debut_min"])
                if filters.get("date_debut_max"):
                    q = q.filter(Absence.date_debut <= filters["date_debut_max"])

            if query and query.strip():
                q_str = f"%{query.strip()}%"
                q = q.filter(
                    or_(
                        Personnel.matricule.ilike(q_str),
                        Personnel.nom.ilike(q_str),
                        Personnel.prenoms.ilike(q_str),
                    )
                )

            total = q.count()
            q = q.order_by(Absence.date_debut.desc())
            offset = max(0, (page - 1)) * page_size
            rows = q.offset(offset).limit(page_size).all()

            return [a.to_dict() for a in rows], total

    # ====================================================================
    # UPDATE
    # ====================================================================
    @staticmethod
    def update(absence_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_session() as db:
            absence = db.query(Absence).filter_by(id=absence_id).first()
            if not absence:
                raise AbsenceIntrouvableError(f"Absence ID={absence_id} introuvable.")

            if "type_absence" in data:
                if data["type_absence"] not in TYPES_ABSENCE:
                    raise AbsenceException(f"Type invalide : {data['type_absence']}")
                absence.type_absence = data["type_absence"]

            date_debut = data.get("date_debut", absence.date_debut)
            date_fin = data.get("date_fin", absence.date_fin)

            if date_fin < date_debut:
                raise DatesInvalidesError(
                    "La date de fin doit être postérieure ou égale à la date de début."
                )

            absence.date_debut = date_debut
            absence.date_fin = date_fin
            absence.nb_jours_ouvres = AbsenceService.count_business_days(date_debut, date_fin)

            if "motif" in data:
                absence.motif = data["motif"]

            if "statut" in data and data["statut"] == "Annulée":
                absence.statut = "Annulée"
            else:
                absence.statut = AbsenceService.compute_statut(date_debut, date_fin)

            db.flush()
            return absence.to_dict()

    # ====================================================================
    # DELETE
    # ====================================================================
    @staticmethod
    def delete(absence_id: int) -> Dict[str, Any]:
        with get_session() as db:
            absence = db.query(Absence).filter_by(id=absence_id).first()
            if not absence:
                raise AbsenceIntrouvableError(f"Absence ID={absence_id} introuvable.")
            snapshot = absence.to_dict()
            db.delete(absence)
            db.flush()
            return snapshot

    # ====================================================================
    # QUOTA
    # ====================================================================
    @staticmethod
    def get_quota_status(personnel_id: int, annee: Optional[int] = None) -> Dict[str, Any]:
        """
        Calcule l'état du quota de congés annuels pour un agent sur une année.

        Returns:
            {
                "annee": 2026,
                "quota_total": 30,
                "jours_pris": 18,
                "jours_restants": 12,
                "pourcentage": 60.0,
                "depassement": False,
            }
        """
        annee = annee or date.today().year

        with get_session() as db:
            absences = (
                db.query(Absence)
                .filter(
                    Absence.personnel_id == personnel_id,
                    Absence.type_absence == "Congé annuel",
                    Absence.statut != "Annulée",
                )
                .all()
            )
            # Ne compter que les jours qui tombent dans l'année demandée
            jours_pris = 0
            for a in absences:
                if a.date_debut.year == annee or a.date_fin.year == annee:
                    jours_pris += a.nb_jours_ouvres

        quota_total = SettingsService.get_quota_conges_annuel()
        jours_restants = quota_total - jours_pris
        pourcentage = round((jours_pris / quota_total) * 100, 1) if quota_total else 0

        return {
            "annee": annee,
            "quota_total": quota_total,
            "jours_pris": jours_pris,
            "jours_restants": jours_restants,
            "pourcentage": min(pourcentage, 100.0),
            "depassement": jours_pris > quota_total,
        }

    @staticmethod
    def get_quota_status_all_agents(annee: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retourne le statut de quota pour TOUS les agents (vue d'ensemble)."""
        annee = annee or date.today().year

        with get_session() as db:
            agents = db.query(Personnel).order_by(Personnel.nom).all()
            result = []
            for agent in agents:
                status = AbsenceService.get_quota_status(agent.id, annee)
                if status["jours_pris"] > 0:  # n'afficher que ceux avec des congés
                    status["personnel_id"] = agent.id
                    status["matricule"] = agent.matricule
                    status["nom_complet"] = agent.nom_complet
                    result.append(status)

        return result

    # ====================================================================
    # STATISTIQUES
    # ====================================================================
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Statistiques globales pour le Dashboard."""
        with get_session() as db:
            total = db.query(Absence).count()
            en_cours = db.query(Absence).filter_by(statut="En cours").count()
            planifiees = db.query(Absence).filter_by(statut="Planifiée").count()

            par_type = dict(
                db.query(Absence.type_absence, func.count(Absence.id))
                .group_by(Absence.type_absence)
                .all()
            )

            return {
                "total_absences": total,
                "en_cours": en_cours,
                "planifiees": planifiees,
                "par_type": par_type,
            }