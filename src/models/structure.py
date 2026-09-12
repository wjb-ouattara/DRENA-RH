"""Modèle Structure (établissement/service)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from src.models.database import Base


class Structure(Base):
    """Structure / Établissement de la DRENAET."""
    __tablename__ = "structures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(200), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)
    code = Column(String(20), nullable=True)
    localite = Column(String(100), nullable=True)
    adresse = Column(String(500), nullable=True)
    telephone = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    iepp_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    agents = relationship("Personnel", back_populates="structure", lazy="dynamic")

    def __repr__(self):
        return f"<Structure(id={self.id}, nom='{self.nom}', type='{self.type}')>"

    def __str__(self):
        return self.nom

    def to_dict(self):
        return {
            "id": self.id, "nom": self.nom, "type": self.type, "code": self.code,
            "localite": self.localite, "adresse": self.adresse,
            "telephone": self.telephone, "email": self.email,
            "nb_agents": self.agents.count() if self.agents else 0,
        }
