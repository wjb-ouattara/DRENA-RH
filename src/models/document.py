"""Modèle DocumentGenere — Historique des documents générés."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from src.models.database import Base


class DocumentGenere(Base):
    """Document administratif généré par l'application."""
    __tablename__ = "documents_generes"
    __table_args__ = (
        # Le même numéro peut exister pour des types différents (ex: 1/MENAET... AUT et 1/MENAET... OM)
        # Mais doit rester unique au sein d'un même type et d'une même année scolaire
        UniqueConstraint("numero", "type_document", "annee_scolaire",
                          name="uq_doc_numero_type_annee"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(100), nullable=False, index=True)
    type_document = Column(String(50), nullable=False, index=True)
    annee_scolaire = Column(String(15), nullable=False, index=True)

    personnel_id = Column(
        Integer,
        ForeignKey("personnel.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interim_personnel_id = Column(
    Integer,
    ForeignKey("personnel.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    )

    parametres_json = Column(Text, nullable=True)
    chemin_docx = Column(String(500), nullable=True)
    chemin_pdf = Column(String(500), nullable=True)

    date_generation = Column(DateTime, default=datetime.utcnow, nullable=False)
    genere_par = Column(String(100), nullable=True)
    observations = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    personnel = relationship("Personnel", back_populates="documents",
                              foreign_keys=[personnel_id])
    interim = relationship("Personnel", foreign_keys=[interim_personnel_id])

    def __repr__(self):
        return f"<DocumentGenere(numero='{self.numero}', type='{self.type_document}')>"

    def __str__(self):
        return f"{self.numero} ({self.type_document})"

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "type_document": self.type_document,
            "annee_scolaire": self.annee_scolaire,
            "personnel": self.personnel.nom_complet if self.personnel else None,
            "matricule": self.personnel.matricule if self.personnel else None,
            "date_generation": self.date_generation.isoformat() if self.date_generation else None,
            "genere_par": self.genere_par,
            "chemin_docx": self.chemin_docx,
            "chemin_pdf": self.chemin_pdf,
        }