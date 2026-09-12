"""
========================================================================
DRENAET-RH — Modèle Settings (paramètres clé/valeur)
========================================================================
Stockage flexible des paramètres modifiables depuis l'interface :
- Identité DRENAET (nom officiel, adresse, contact...)
- Directeur Régional (nom, titre, procuration)
- Quota de congés annuel

Design "clé/valeur" plutôt que colonnes fixes : permet d'ajouter de
nouveaux paramètres plus tard sans migration de schéma.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from src.models.database import Base


class Settings(Base):
    """Un paramètre de configuration (clé/valeur)."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cle = Column(String(100), nullable=False, unique=True, index=True)
    valeur = Column(Text, nullable=True)
    categorie = Column(String(50), nullable=True, index=True)
    date_modification = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    modifie_par = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<Settings(cle='{self.cle}', valeur='{self.valeur}')>"