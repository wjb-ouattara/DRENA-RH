"""
========================================================================
DRENAET-RH — Modèle AuditLog (Historique des modifications d'agents)
========================================================================
Trace TOUTES les modifications faites sur les agents :
- Création (avec valeurs initiales)
- Modification (valeur AVANT + valeur APRÈS pour chaque champ modifié)
- Suppression (avec snapshot des données au moment de la suppression)

Cet audit trail permet :
- De savoir QUI a modifié QUOI et QUAND
- De reconstruire l'historique d'un agent
- De détecter les changements suspects
- De se conformer aux exigences administratives

Note : Chaque changement génère UNE ligne (pas une ligne par champ modifié).
Le détail des changements est stocké en JSON pour préserver la flexibilité.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from src.models.database import Base


class AuditLog(Base):
    """Journal d'audit des modifications sur le personnel."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Type d'action : "CREATE" | "UPDATE" | "DELETE"
    action = Column(String(20), nullable=False, index=True)

    # Référence à l'agent concerné (matricule car l'ID peut être supprimé)
    # On garde le matricule et le nom pour audit même après hard-delete
    personnel_matricule = Column(String(20), nullable=False, index=True)
    personnel_nom_complet = Column(String(200), nullable=False)

    # Détails du changement (format JSON)
    # Pour CREATE : {"valeurs_initiales": {"nom": "BABO", "emploi": "...", ...}}
    # Pour UPDATE : {"changements": {"telephone": ["07 07", "08 08"], "fonction": [...]}}
    # Pour DELETE : {"snapshot": {"nom": "BABO", "emploi": "...", ...}}
    changements_json = Column(Text, nullable=False)

    # Qui et quand
    utilisateur_login = Column(String(50), nullable=False)
    utilisateur_role = Column(String(20), nullable=True)
    date_action = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # Source de la modification
    # "MANUAL" (via UI) | "IMPORT" (via import Excel) | "API" (futur) | "SYSTEM" (seed)
    source = Column(String(20), default="MANUAL", nullable=False)

    # Si source=IMPORT, on lie à l'import concerné (pour retrouver le contexte)
    import_log_id = Column(Integer, nullable=True, index=True)

    # Notes optionnelles (raison de la modification par exemple)
    commentaire = Column(Text, nullable=True)

    # Index composite pour recherches fréquentes
    __table_args__ = (
        Index("ix_audit_matricule_date", "personnel_matricule", "date_action"),
        Index("ix_audit_utilisateur_date", "utilisateur_login", "date_action"),
    )

    # ====================================================================
    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"matricule='{self.personnel_matricule}', "
            f"date={self.date_action}, user='{self.utilisateur_login}')>"
        )

    def __str__(self):
        return f"[{self.date_action.strftime('%d/%m/%Y %H:%M')}] {self.action} - {self.personnel_matricule} par {self.utilisateur_login}"

    def to_dict(self) -> dict:
        """Convertit l'entrée en dict (pour l'affichage UI)."""
        import json
        try:
            changements = json.loads(self.changements_json)
        except (json.JSONDecodeError, TypeError):
            changements = {}

        return {
            "id": self.id,
            "action": self.action,
            "personnel_matricule": self.personnel_matricule,
            "personnel_nom_complet": self.personnel_nom_complet,
            "changements": changements,
            "utilisateur_login": self.utilisateur_login,
            "utilisateur_role": self.utilisateur_role,
            "date_action": self.date_action.isoformat() if self.date_action else None,
            "source": self.source,
            "import_log_id": self.import_log_id,
            "commentaire": self.commentaire,
        }