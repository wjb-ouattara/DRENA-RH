"""
========================================================================
DRENAET-RH — AuditService
========================================================================
Service pour enregistrer les modifications d'agents dans l'audit trail.

Toutes les méthodes acceptent une session SQLAlchemy déjà ouverte
(paramètre `db`) pour être appelées depuis PersonnelService
dans la même transaction.

Ainsi, si le CREATE/UPDATE/DELETE échoue, l'audit log est aussi rollback :
on ne perd pas la cohérence.
"""

import json
from datetime import date, datetime
from typing import Dict, Any, Optional, List, Tuple

from sqlalchemy.orm import Session

from src.models import get_session
from src.models.audit_log import AuditLog


# ========================================================================
class AuditService:
    """Service de gestion de l'audit trail des modifications personnel."""

    # ====================================================================
    # ÉCRITURE (appelées depuis PersonnelService dans la même transaction)
    # ====================================================================
    @staticmethod
    def log_create(
        db: Session,
        matricule: str,
        nom_complet: str,
        valeurs_initiales: Dict[str, Any],
        user_login: str,
        user_role: str = None,
        source: str = "MANUAL",
        import_log_id: int = None,
        commentaire: str = None,
    ) -> AuditLog:
        """Enregistre la création d'un agent."""
        entry = AuditLog(
            action="CREATE",
            personnel_matricule=matricule,
            personnel_nom_complet=nom_complet,
            changements_json=json.dumps(
                {"valeurs_initiales": AuditService._sanitize(valeurs_initiales)},
                ensure_ascii=False,
            ),
            utilisateur_login=user_login,
            utilisateur_role=user_role,
            source=source,
            import_log_id=import_log_id,
            commentaire=commentaire,
        )
        db.add(entry)
        db.flush()
        return entry

    @staticmethod
    def log_update(
        db: Session,
        matricule: str,
        nom_complet: str,
        changements: Dict[str, List],
        user_login: str,
        user_role: str = None,
        source: str = "MANUAL",
        import_log_id: int = None,
        commentaire: str = None,
    ) -> AuditLog:
        """
        Enregistre la modification d'un agent.

        changements = {"telephone": ["07 07", "08 08"], "fonction": [...]}
        """
        entry = AuditLog(
            action="UPDATE",
            personnel_matricule=matricule,
            personnel_nom_complet=nom_complet,
            changements_json=json.dumps(
                {"changements": AuditService._sanitize(changements)},
                ensure_ascii=False,
            ),
            utilisateur_login=user_login,
            utilisateur_role=user_role,
            source=source,
            import_log_id=import_log_id,
            commentaire=commentaire,
        )
        db.add(entry)
        db.flush()
        return entry

    @staticmethod
    def log_delete(
        db: Session,
        matricule: str,
        nom_complet: str,
        snapshot: Dict[str, Any],
        user_login: str,
        user_role: str = None,
        source: str = "MANUAL",
        import_log_id: int = None,
        commentaire: str = None,
    ) -> AuditLog:
        """Enregistre la suppression d'un agent (avec snapshot)."""
        entry = AuditLog(
            action="DELETE",
            personnel_matricule=matricule,
            personnel_nom_complet=nom_complet,
            changements_json=json.dumps(
                {"snapshot": AuditService._sanitize(snapshot)},
                ensure_ascii=False,
            ),
            utilisateur_login=user_login,
            utilisateur_role=user_role,
            source=source,
            import_log_id=import_log_id,
            commentaire=commentaire,
        )
        db.add(entry)
        db.flush()
        return entry

    # ====================================================================
    # LECTURE (consultation de l'historique)
    # ====================================================================
    @staticmethod
    def get_history_for_agent(
        matricule: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retourne l'historique complet d'un agent (par matricule).

        Retourne les entrées triées de la plus récente à la plus ancienne.
        """
        matricule = str(matricule).strip().upper()
        with get_session() as db:
            entries = (
                db.query(AuditLog)
                .filter_by(personnel_matricule=matricule)
                .order_by(AuditLog.date_action.desc())
                .limit(limit)
                .all()
            )
            return [e.to_dict() for e in entries]

    @staticmethod
    def get_recent_activity(
        limit: int = 50,
        action: Optional[str] = None,
        user_login: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne l'activité récente (dernières modifications).

        Args:
            limit: nombre max de résultats
            action: filtrer par type d'action (CREATE / UPDATE / DELETE)
            user_login: filtrer par utilisateur

        Utilisé pour le module Administration / Dashboard.
        """
        with get_session() as db:
            q = db.query(AuditLog)
            if action:
                q = q.filter_by(action=action)
            if user_login:
                q = q.filter_by(utilisateur_login=user_login)
            entries = (
                q.order_by(AuditLog.date_action.desc())
                .limit(limit)
                .all()
            )
            return [e.to_dict() for e in entries]

    @staticmethod
    def count_by_action() -> Dict[str, int]:
        """Compte les entrées d'audit par type d'action (pour stats)."""
        from sqlalchemy import func
        with get_session() as db:
            rows = (
                db.query(AuditLog.action, func.count(AuditLog.id))
                .group_by(AuditLog.action)
                .all()
            )
            return dict(rows)

    @staticmethod
    def search(
        query: str = "",
        action: str = None,
        source: str = None,
        user_login: str = None,
        date_debut: date = None,
        date_fin: date = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recherche paginée dans l'audit trail.

        Utilisé par l'écran Administration → Journal des modifications.
        """
        with get_session() as db:
            q = db.query(AuditLog)

            if query and query.strip():
                q_str = f"%{query.strip()}%"
                from sqlalchemy import or_
                q = q.filter(
                    or_(
                        AuditLog.personnel_matricule.ilike(q_str),
                        AuditLog.personnel_nom_complet.ilike(q_str),
                    )
                )

            if action:
                q = q.filter_by(action=action)
            if source:
                q = q.filter_by(source=source)
            if user_login:
                q = q.filter_by(utilisateur_login=user_login)
            if date_debut:
                q = q.filter(AuditLog.date_action >= date_debut)
            if date_fin:
                q = q.filter(AuditLog.date_action <= date_fin)

            total = q.count()

            offset = max(0, (page - 1)) * page_size
            entries = (
                q.order_by(AuditLog.date_action.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )
            return [e.to_dict() for e in entries], total

    # ====================================================================
    # HELPERS PRIVÉS
    # ====================================================================
    @staticmethod
    def _sanitize(data: Any) -> Any:
        """Convertit les dates en strings pour JSON."""
        if isinstance(data, dict):
            return {k: AuditService._sanitize(v) for k, v in data.items()}
        if isinstance(data, list):
            return [AuditService._sanitize(x) for x in data]
        if isinstance(data, (date, datetime)):
            return data.isoformat()
        return data