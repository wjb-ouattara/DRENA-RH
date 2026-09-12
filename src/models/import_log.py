"""
========================================================================
DRENAET-RH — Modèles ImportLog et ImportDetail
========================================================================
Journal complet des imports Excel effectués dans le logiciel.

DEUX tables :
- import_logs : un enregistrement par IMPORT (fichier Excel traité)
- import_details : un enregistrement par LIGNE Excel traitée dans cet import

Utilité :
- Traçabilité totale : qui a importé quel fichier, quand, avec quelle stratégie
- Détection des re-imports (même hash de fichier)
- Statistiques d'imports (nombre d'agents créés/mis à jour par période)
- Historique des erreurs pour améliorer les futurs imports
- Possibilité d'annuler un import récent (via son ID)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.models.database import Base


# ========================================================================
class ImportLog(Base):
    """Un enregistrement pour chaque import Excel effectué."""
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identité du fichier
    nom_fichier = Column(String(255), nullable=False)
    hash_fichier = Column(String(64), nullable=False, index=True)  # SHA-256
    taille_fichier_octets = Column(Integer, nullable=True)

    # Métadonnées de l'import
    date_import = Column(DateTime, default=datetime.now, nullable=False, index=True)
    utilisateur_login = Column(String(50), nullable=False)
    utilisateur_role = Column(String(20), nullable=True)

    # Stratégie utilisée (parmi UPSERT, INSERT_ONLY, UPDATE_ONLY, REPLACE)
    strategie = Column(String(20), nullable=False)

    # Feuille traitée dans le fichier Excel
    feuille_excel = Column(String(100), nullable=True)

    # Compteurs (calculés à la fin de l'import)
    nb_lignes_lues = Column(Integer, default=0, nullable=False)
    nb_crees = Column(Integer, default=0, nullable=False)
    nb_modifies = Column(Integer, default=0, nullable=False)
    nb_ignores = Column(Integer, default=0, nullable=False)
    nb_erreurs = Column(Integer, default=0, nullable=False)

    # Statut final
    # "SUCCESS" : tout est ok
    # "PARTIAL" : import réussi mais avec des lignes ignorées ou en erreur
    # "FAILED"  : import échoué (fichier invalide, erreur critique)
    # "DRY_RUN" : simulation uniquement, aucune écriture BD
    statut = Column(String(20), nullable=False)

    # Durée d'exécution (millisecondes)
    duree_ms = Column(Integer, nullable=True)

    # Rapport détaillé (JSON) pour affichage UI
    rapport_json = Column(Text, nullable=True)

    # Notes optionnelles
    commentaire = Column(Text, nullable=True)

    # Relation vers les détails ligne par ligne
    details = relationship(
        "ImportDetail",
        back_populates="import_log",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<ImportLog(id={self.id}, fichier='{self.nom_fichier}', "
            f"date={self.date_import}, statut='{self.statut}')>"
        )

    def to_dict(self) -> dict:
        """Convertit en dict pour l'affichage UI."""
        import json
        try:
            rapport = json.loads(self.rapport_json) if self.rapport_json else {}
        except (json.JSONDecodeError, TypeError):
            rapport = {}

        return {
            "id": self.id,
            "nom_fichier": self.nom_fichier,
            "hash_fichier": self.hash_fichier,
            "date_import": self.date_import.isoformat() if self.date_import else None,
            "utilisateur_login": self.utilisateur_login,
            "utilisateur_role": self.utilisateur_role,
            "strategie": self.strategie,
            "feuille_excel": self.feuille_excel,
            "nb_lignes_lues": self.nb_lignes_lues,
            "nb_crees": self.nb_crees,
            "nb_modifies": self.nb_modifies,
            "nb_ignores": self.nb_ignores,
            "nb_erreurs": self.nb_erreurs,
            "statut": self.statut,
            "duree_ms": self.duree_ms,
            "rapport": rapport,
            "commentaire": self.commentaire,
        }


# ========================================================================
class ImportDetail(Base):
    """Détail ligne par ligne d'un import (traçabilité)."""
    __tablename__ = "import_details"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Rattachement à l'import parent
    import_log_id = Column(
        Integer,
        ForeignKey("import_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position dans le fichier Excel
    numero_ligne_excel = Column(Integer, nullable=False)

    # Matricule concerné (peut être None si erreur de parsing)
    matricule = Column(String(20), nullable=True, index=True)

    # Résultat pour cette ligne
    # "CREATED" | "UPDATED" | "SKIPPED" | "ERROR" | "PREVIEW" (dry-run)
    action = Column(String(20), nullable=False)

    # Détail des changements (JSON)
    # Pour CREATED : {"valeurs_initiales": {...}}
    # Pour UPDATED : {"changements": {"champ": ["avant", "après"], ...}}
    # Pour SKIPPED : {"raison": "matricule déjà présent"}
    # Pour ERROR   : {"erreur": "date invalide", "champ_erreur": "date_naissance"}
    changements_json = Column(Text, nullable=True)

    # Message d'erreur (si action=ERROR)
    message_erreur = Column(Text, nullable=True)

    # Relation vers l'import parent
    import_log = relationship("ImportLog", back_populates="details")

    # Index composite pour recherches fréquentes
    __table_args__ = (
        Index("ix_detail_import_action", "import_log_id", "action"),
    )

    def __repr__(self):
        return (
            f"<ImportDetail(id={self.id}, import={self.import_log_id}, "
            f"ligne={self.numero_ligne_excel}, matricule='{self.matricule}', "
            f"action='{self.action}')>"
        )

    def to_dict(self) -> dict:
        """Convertit en dict pour l'affichage UI."""
        import json
        try:
            changements = json.loads(self.changements_json) if self.changements_json else {}
        except (json.JSONDecodeError, TypeError):
            changements = {}

        return {
            "id": self.id,
            "import_log_id": self.import_log_id,
            "numero_ligne_excel": self.numero_ligne_excel,
            "matricule": self.matricule,
            "action": self.action,
            "changements": changements,
            "message_erreur": self.message_erreur,
        }