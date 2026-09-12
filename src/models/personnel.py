"""Modèle Personnel — Table maîtresse des agents."""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from src.models.database import Base


class Personnel(Base):
    """Agent de la DRENAET."""
    __tablename__ = "personnel"

    # --- Clé primaire ---
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Identification officielle ---
    matricule = Column(String(20), unique=True, nullable=False, index=True)

    # --- Identité ---
    nom = Column(String(100), nullable=False, index=True)
    prenoms = Column(String(200), nullable=False)
    sexe = Column(String(1), nullable=False)  # "M" ou "F"
    date_naissance = Column(Date, nullable=True)
    lieu_naissance = Column(String(150), nullable=True)
    nationalite = Column(String(50), default="Ivoirienne", nullable=True)
    situation_matrimoniale = Column(String(30), nullable=True)
    cni = Column(String(30), nullable=True)
    cnps = Column(String(30), nullable=True)

    # --- Profession ---
    emploi = Column(String(100), nullable=False)
    fonction = Column(String(100), nullable=True)
    grade = Column(String(50), nullable=True)
    structure_id = Column(Integer, ForeignKey("structures.id"), nullable=False)
    date_prise_service = Column(Date, nullable=True)
    date_affectation = Column(Date, nullable=True)

    # --- Contact ---
    telephone = Column(String(30), nullable=True)
    telephone_2 = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    adresse = Column(Text, nullable=True)
    residence = Column(String(150), nullable=True)

    # --- Contact urgence ---
    contact_urgence_nom = Column(String(200), nullable=True)
    contact_urgence_lien = Column(String(50), nullable=True)
    contact_urgence_tel = Column(String(30), nullable=True)

    # --- Statut ---
    statut = Column(String(30), default="Actif", nullable=False)
    photo_path = Column(String(500), nullable=True)
    observations = Column(Text, nullable=True)

    # --- Métadonnées ---
    actif = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relations ---
    structure = relationship("Structure", back_populates="agents")
    documents = relationship("DocumentGenere", back_populates="personnel", lazy="dynamic",
                              foreign_keys="DocumentGenere.personnel_id")
    absences = relationship("Absence", back_populates="personnel", lazy="dynamic")

    # ================================================
    def __repr__(self):
        return f"<Personnel(matricule='{self.matricule}', nom='{self.nom_complet}')>"

    def __str__(self):
        return f"{self.matricule} - {self.nom_complet}"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenoms}"

    @property
    def civilite(self):
        return "M." if self.sexe == "M" else "Mme/Mlle"

    @property
    def age(self):
        if not self.date_naissance:
            return None
        today = date.today()
        age = today.year - self.date_naissance.year
        if (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day):
            age -= 1
        return age

    @property
    def anciennete_jours(self):
        if not self.date_prise_service:
            return None
        return (date.today() - self.date_prise_service).days

    @property
    def anciennete_annees(self):
        days = self.anciennete_jours
        return round(days / 365.25, 1) if days is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "matricule": self.matricule,
            "nom": self.nom,
            "prenoms": self.prenoms,
            "nom_complet": self.nom_complet,
            "sexe": self.sexe,
            "civilite": self.civilite,
            "date_naissance": self.date_naissance.isoformat() if self.date_naissance else None,
            "age": self.age,
            "emploi": self.emploi,
            "fonction": self.fonction,
            "structure": self.structure.nom if self.structure else None,
            "structure_id": self.structure_id,
            "telephone": self.telephone,
            "email": self.email,
            "residence": self.residence,
            "statut": self.statut,
            "anciennete_annees": self.anciennete_annees,
            "actif": self.actif,
        }

    def to_doc_context(self):
        """Variables pour injection dans templates Word."""
        return {
            "matricule": self.matricule or "",
            "civilite": self.civilite,
            "nom_complet": self.nom_complet,
            "nom": self.nom or "",
            "prenoms": self.prenoms or "",
            "emploi": self.emploi or "",
            "fonction": self.fonction or "",
            "structure": self.structure.nom if self.structure else "",
            "telephone": self.telephone or "",
            "residence": self.residence or (self.structure.localite if self.structure else ""),
        }
