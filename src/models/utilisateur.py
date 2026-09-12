"""Modèle Utilisateur — Authentification."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import validates
from src.models.database import Base


class Utilisateur(Base):
    """Utilisateur authentifié de l'application."""
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String(200), nullable=False)

    nom_complet = Column(String(200), nullable=False)
    email = Column(String(150), nullable=True)

    role = Column(String(20), default="operateur", nullable=False)

    actif = Column(Boolean, default=True, nullable=False)
    doit_changer_mdp = Column(Boolean, default=False, nullable=False)

    tentatives_login = Column(Integer, default=0, nullable=False)
    bloque_jusqu_a = Column(DateTime, nullable=True)

    derniere_connexion = Column(DateTime, nullable=True)
    nb_connexions = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @validates("login")
    def validate_login(self, key, value):
        if value:
            value = value.strip().lower()
            if not value:
                raise ValueError("Le login ne peut pas être vide.")
            if " " in value:
                raise ValueError("Le login ne doit pas contenir d'espaces.")
        return value

    @validates("role")
    def validate_role(self, key, value):
        roles_valides = {"admin", "operateur", "consultation"}
        if value not in roles_valides:
            raise ValueError(f"Rôle invalide : {value}. Doit être dans {roles_valides}")
        return value

    def __repr__(self):
        return f"<Utilisateur(login='{self.login}', role='{self.role}')>"

    def __str__(self):
        return f"{self.nom_complet} ({self.login})"

    @property
    def est_admin(self):
        return self.role == "admin"

    @property
    def est_bloque(self):
        if self.bloque_jusqu_a is None:
            return False
        return datetime.utcnow() < self.bloque_jusqu_a

    def to_dict(self):
        return {
            "id": self.id,
            "login": self.login,
            "nom_complet": self.nom_complet,
            "email": self.email,
            "role": self.role,
            "actif": self.actif,
            "derniere_connexion": self.derniere_connexion.isoformat() if self.derniere_connexion else None,
            "nb_connexions": self.nb_connexions,
        }
