"""Modèle CompteurDocument — Auto-incrément des numéros."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from src.models.database import Base


class CompteurDocument(Base):
    """Compteur de numérotation des documents."""
    __tablename__ = "compteurs_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_document = Column(String(50), nullable=False)
    annee_scolaire = Column(String(15), nullable=False)
    dernier_numero = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("type_document", "annee_scolaire", name="uq_type_annee"),
    )

    def __repr__(self):
        return f"<CompteurDocument(type='{self.type_document}', annee='{self.annee_scolaire}', n={self.dernier_numero})>"

    def incrementer(self):
        self.dernier_numero += 1
        return self.dernier_numero
