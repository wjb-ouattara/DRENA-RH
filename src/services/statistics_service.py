"""
========================================================================
DRENAET-RH — StatisticsService
========================================================================
Service d'agrégation de données pour le module Statistiques.

Toutes les méthodes retournent des structures simples (dicts/listes)
prêtes à être injectées dans les widgets graphiques (pas d'objets ORM
exposés en dehors du service).
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy import func

from src.models import get_session
from src.models.personnel import Personnel
from src.models.structure import Structure
from src.models.absence import Absence


class StatisticsService:
    """Service d'agrégation de statistiques pour le Dashboard."""

    # ====================================================================
    # KPI GLOBAUX
    # ====================================================================
    @staticmethod
    def get_kpi_summary() -> Dict[str, Any]:
        """4 indicateurs clés pour les cartes du haut."""
        with get_session() as db:
            total_agents = db.query(Personnel).count()
            hommes = db.query(Personnel).filter_by(sexe="M").count()
            femmes = db.query(Personnel).filter_by(sexe="F").count()

            absences_en_cours = db.query(Absence).filter_by(statut="En cours").count()

            # Documents générés ce mois (import différé pour éviter dépendance circulaire)
            nb_documents_mois = 0
            try:
                from src.models.document import DocumentGenere
                today = date.today()
                debut_mois = today.replace(day=1)
                nb_documents_mois = (
                    db.query(DocumentGenere)
                    .filter(DocumentGenere.date_generation >= debut_mois)
                    .count()
                )
            except Exception:
                pass

            ratio_femmes = round((femmes / total_agents) * 100, 1) if total_agents else 0

            return {
                "total_agents": total_agents,
                "hommes": hommes,
                "femmes": femmes,
                "ratio_femmes_pct": ratio_femmes,
                "absences_en_cours": absences_en_cours,
                "documents_ce_mois": nb_documents_mois,
            }

    # ====================================================================
    # PERSONNEL PAR STRUCTURE
    # ====================================================================
    @staticmethod
    def get_personnel_par_structure(top_n: int = 8) -> List[Dict[str, Any]]:
        """Retourne le top N des structures par nombre d'agents."""
        with get_session() as db:
            rows = (
                db.query(Structure.nom, func.count(Personnel.id).label("nb"))
                .join(Personnel, Personnel.structure_id == Structure.id)
                .group_by(Structure.nom)
                .order_by(func.count(Personnel.id).desc())
                .limit(top_n)
                .all()
            )
            return [{"label": nom, "value": nb} for nom, nb in rows]

    # ====================================================================
    # PERSONNEL PAR SEXE
    # ====================================================================
    @staticmethod
    def get_personnel_par_sexe() -> List[Dict[str, Any]]:
        with get_session() as db:
            hommes = db.query(Personnel).filter_by(sexe="M").count()
            femmes = db.query(Personnel).filter_by(sexe="F").count()
            return [
                {"label": "Hommes", "value": hommes, "color": "#3B82F6"},
                {"label": "Femmes", "value": femmes, "color": "#EC4899"},
            ]

    # ====================================================================
    # PERSONNEL PAR STATUT
    # ====================================================================
    @staticmethod
    def get_personnel_par_statut() -> List[Dict[str, Any]]:
        with get_session() as db:
            rows = (
                db.query(Personnel.statut, func.count(Personnel.id))
                .group_by(Personnel.statut)
                .all()
            )
            colors = {
                "Actif": "#10B981", "Inactif": "#94A3B8", "En congé": "#F59E0B",
                "Muté": "#3B82F6", "Retraité": "#8B5CF6",
            }
            return [
                {"label": statut or "?", "value": nb, "color": colors.get(statut, "#64748B")}
                for statut, nb in rows
            ]

    # ====================================================================
    # ABSENCES PAR TYPE
    # ====================================================================
    @staticmethod
    def get_absences_par_type(annee: int = None) -> List[Dict[str, Any]]:
        """Répartition des absences par type sur une année (année en cours par défaut)."""
        annee = annee or date.today().year
        with get_session() as db:
            rows = (
                db.query(Absence.type_absence, func.count(Absence.id))
                .filter(func.strftime("%Y", Absence.date_debut) == str(annee))
                .group_by(Absence.type_absence)
                .all()
            )
            colors = {
                "Congé annuel": "#10B981", "Congé maladie": "#DC2626",
                "Congé maternité": "#EC4899", "Autorisation d'absence": "#4338CA",
                "Mission": "#7C3AED", "Autre": "#64748B",
            }
            return [
                {"label": t, "value": nb, "color": colors.get(t, "#64748B")}
                for t, nb in rows
            ]

    # ====================================================================
    # DOCUMENTS PAR TYPE
    # ====================================================================
    @staticmethod
    def get_documents_par_type(top_n: int = 8) -> List[Dict[str, Any]]:
        """Répartition des documents générés par type."""
        try:
            from src.models.document import DocumentGenere
        except Exception:
            return []

        with get_session() as db:
            rows = (
                db.query(DocumentGenere.type_document, func.count(DocumentGenere.id))
                .group_by(DocumentGenere.type_document)
                .order_by(func.count(DocumentGenere.id).desc())
                .limit(top_n)
                .all()
            )
            return [{"label": t or "?", "value": nb} for t, nb in rows]

    # ====================================================================
    # ÉVOLUTION MENSUELLE DES ABSENCES (12 derniers mois)
    # ====================================================================
    @staticmethod
    def get_absences_evolution_mensuelle() -> List[Dict[str, Any]]:
        """Nombre d'absences démarrées par mois, sur les 12 derniers mois."""
        today = date.today()
        months = []
        for i in range(11, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))

        with get_session() as db:
            all_absences = db.query(Absence.date_debut).all()

        counts = {f"{y:04d}-{m:02d}": 0 for y, m in months}
        for (d,) in all_absences:
            key = f"{d.year:04d}-{d.month:02d}"
            if key in counts:
                counts[key] += 1

        mois_labels_fr = [
            "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
            "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc",
        ]
        result = []
        for y, m in months:
            key = f"{y:04d}-{m:02d}"
            result.append({"label": mois_labels_fr[m - 1], "value": counts[key]})
        return result