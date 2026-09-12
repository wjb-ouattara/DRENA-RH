"""
========================================================================
DRENAET-RH — Modèle Absence
========================================================================
Suivi des absences et congés des agents (cadres administratifs).

Une Absence peut être créée de 2 façons :
- AUTOMATIQUEMENT : quand un document (Autorisation d'Absence ou Titre de
  Congés) est généré, une entrée Absence est créée en lien (document_id renseigné)
- MANUELLEMENT : saisie directe dans le module Absences, sans document PDF

Le nombre de jours est calculé automatiquement en JOURS OUVRÉS
(les samedis et dimanches sont exclus du décompte).

Un quota de 30 jours ouvrés/an s'applique uniquement au type
"Congé annuel". Les autres types sont trackés mais sans quota bloquant.
"""

from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.models.database import Base


# Types d'absence disponibles
TYPES_ABSENCE = [
    "Congé annuel",
    "Congé maladie",
    "Congé maternité",
    "Autorisation d'absence",
    "Mission",
    "Autre",
]

# Types soumis à un quota annuel
TYPES_AVEC_QUOTA = {"Congé annuel"}
QUOTA_JOURS_OUVRES_PAR_AN = 30

STATUTS_ABSENCE = ["Planifiée", "En cours", "Terminée", "Annulée"]


class Absence(Base):
    """Une absence ou un congé d'un agent."""
    __tablename__ = "absences"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Agent concerné
    personnel_id = Column(
        Integer,
        ForeignKey("personnel.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Pas de backref ici : le modèle Personnel a déjà sa propre relation
    # "absences" définie ailleurs. On accède aux absences d'un agent via
    # AbsenceService.search(filters={"personnel_id": ...}) pour éviter
    # tout conflit de mapping SQLAlchemy.
    personnel = relationship("Personnel", foreign_keys=[personnel_id])

    # Type et détails
    type_absence = Column(String(50), nullable=False, index=True)
    date_debut = Column(Date, nullable=False, index=True)
    date_fin = Column(Date, nullable=False)
    nb_jours_ouvres = Column(Integer, nullable=False)
    motif = Column(Text, nullable=True)

    # Statut (calculé automatiquement, "Annulée" peut être forcé manuellement)
    statut = Column(String(20), nullable=False, default="Planifiée", index=True)

    # Traçabilité de la source
    # "MANUAL" : saisie directe dans le module Absences
    # "DOCUMENT" : créée automatiquement lors de la génération d'un document PDF
    source = Column(String(20), nullable=False, default="MANUAL")
    document_id = Column(
        Integer,
        ForeignKey("documents_generes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Métadonnées
    created_by = Column(String(50), nullable=False)
    date_creation = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        Index("ix_absence_personnel_dates", "personnel_id", "date_debut", "date_fin"),
    )

    # ====================================================================
    def __repr__(self):
        return (
            f"<Absence(id={self.id}, personnel_id={self.personnel_id}, "
            f"type='{self.type_absence}', {self.date_debut}->{self.date_fin}, "
            f"statut='{self.statut}')>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "personnel_id": self.personnel_id,
            "matricule": self.personnel.matricule if self.personnel else None,
            "nom_complet": self.personnel.nom_complet if self.personnel else None,
            "type_absence": self.type_absence,
            "date_debut": self.date_debut.isoformat() if self.date_debut else None,
            "date_fin": self.date_fin.isoformat() if self.date_fin else None,
            "nb_jours_ouvres": self.nb_jours_ouvres,
            "motif": self.motif,
            "statut": self.statut,
            "source": self.source,
            "document_id": self.document_id,
            "created_by": self.created_by,
            "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        }