"""
========================================================================
DRENAET-RH — StructureService
========================================================================
Service métier pour la gestion des structures (établissements).

Une "Structure" représente un établissement rattaché à la DRENAET :
- CAFOP (Centre d'Animation et de Formation Pédagogique)
- IEPP (Inspection de l'Enseignement Préscolaire et Primaire)
- Écoles primaires / maternelles
- Lycées / Collèges
- Services centraux (SRH, SG, etc.)

Responsabilités :
- CRUD structures
- Recherche par nom, type, localité
- Compter les agents affectés (impact avant suppression)

Note : la suppression d'une structure est bloquée si des agents y sont rattachés.
"""

from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError

from src.models import get_session, Structure, Personnel


# ========================================================================
# EXCEPTIONS
# ========================================================================
class StructureException(Exception):
    """Exception de base pour StructureService."""
    pass


class NomStructureExistantError(StructureException):
    """Une structure avec ce nom existe déjà."""
    pass


class StructureIntrouvableError(StructureException):
    """La structure n'existe pas."""
    pass


class StructureAvecAgentsError(StructureException):
    """Impossible de supprimer une structure qui contient encore des agents."""
    pass


# ========================================================================
# CONSTANTES
# ========================================================================
TYPES_STRUCTURE = [
    "CAFOP",       # Centre d'Animation et de Formation Pédagogique
    "IEPP",        # Inspection de l'Enseignement Préscolaire et Primaire
    "Ecole",       # École primaire ou maternelle
    "Lycee",       # Lycée
    "College",     # Collège
    "Service",     # Service central (SRH, SG, ...)
    "Autre",
]

CHAMPS_OBLIGATOIRES = ["nom", "type"]


# ========================================================================
class StructureService:
    """Service métier pour la gestion des structures."""

    # ====================================================================
    # CREATE
    # ====================================================================
    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une nouvelle structure.

        Args:
            data: dict avec au moins {"nom": ..., "type": ..., "localite": ...}

        Raises:
            StructureException: champs obligatoires manquants
            NomStructureExistantError: le nom existe déjà
        """
        for champ in CHAMPS_OBLIGATOIRES:
            if not data.get(champ):
                raise StructureException(
                    f"Le champ '{champ}' est obligatoire."
                )

        nom = str(data["nom"]).strip()
        data["nom"] = nom

        with get_session() as db:
            existant = db.query(Structure).filter_by(nom=nom).first()
            if existant:
                raise NomStructureExistantError(
                    f"Une structure nommée '{nom}' existe déjà (ID={existant.id})."
                )

            structure = Structure(
                nom=nom,
                type=data.get("type"),
                localite=data.get("localite"),
            )

            try:
                db.add(structure)
                db.flush()
                return StructureService._to_dict(structure)
            except IntegrityError as e:
                db.rollback()
                raise StructureException(f"Erreur SQL : {e.orig}") from e

    # ====================================================================
    # READ
    # ====================================================================
    @staticmethod
    def get_by_id(structure_id: int) -> Optional[Dict[str, Any]]:
        with get_session() as db:
            s = db.query(Structure).filter_by(id=structure_id).first()
            return StructureService._to_dict(s) if s else None

    @staticmethod
    def get_by_nom(nom: str) -> Optional[Dict[str, Any]]:
        nom = str(nom).strip()
        with get_session() as db:
            s = db.query(Structure).filter_by(nom=nom).first()
            return StructureService._to_dict(s) if s else None

    @staticmethod
    def get_or_create(nom: str, type: str = "Autre", localite: str = None) -> Dict[str, Any]:
        """
        Récupère une structure par son nom, ou la crée si absente.
        Très utile pendant l'import Excel.
        """
        nom = str(nom).strip()
        with get_session() as db:
            s = db.query(Structure).filter_by(nom=nom).first()
            if s:
                return StructureService._to_dict(s)

            s = Structure(nom=nom, type=type, localite=localite)
            db.add(s)
            db.flush()
            return StructureService._to_dict(s)

    @staticmethod
    def list_all(
        include_agent_count: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retourne toutes les structures triées par nom."""
        with get_session() as db:
            rows = db.query(Structure).order_by(Structure.nom).all()
            result = [StructureService._to_dict(s) for s in rows]

            if include_agent_count:
                counts = dict(
                    db.query(Personnel.structure_id, func.count(Personnel.id))
                    .group_by(Personnel.structure_id)
                    .all()
                )
                for r in result:
                    r["nb_agents"] = counts.get(r["id"], 0)

            return result

    @staticmethod
    def search(
        query: str = "",
        type_filter: str = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Recherche paginée de structures."""
        with get_session() as db:
            q = db.query(Structure)

            if query and query.strip():
                q_str = f"%{query.strip()}%"
                q = q.filter(
                    or_(
                        Structure.nom.ilike(q_str),
                        Structure.localite.ilike(q_str),
                    )
                )
            if type_filter:
                q = q.filter_by(type=type_filter)

            total = q.count()
            offset = max(0, (page - 1)) * page_size
            rows = q.order_by(Structure.nom).offset(offset).limit(page_size).all()
            return [StructureService._to_dict(s) for s in rows], total

    @staticmethod
    def count_agents_in_structure(structure_id: int) -> int:
        """Compte les agents affectés à une structure."""
        with get_session() as db:
            return db.query(Personnel).filter_by(structure_id=structure_id).count()

    # ====================================================================
    # UPDATE
    # ====================================================================
    @staticmethod
    def update(structure_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_session() as db:
            s = db.query(Structure).filter_by(id=structure_id).first()
            if not s:
                raise StructureIntrouvableError(
                    f"Structure ID={structure_id} introuvable."
                )

            # Vérifier unicité du nouveau nom si changé
            if "nom" in data and data["nom"] and data["nom"] != s.nom:
                autre = db.query(Structure).filter_by(nom=data["nom"]).first()
                if autre and autre.id != structure_id:
                    raise NomStructureExistantError(
                        f"Une autre structure nommée '{data['nom']}' existe déjà."
                    )
                s.nom = data["nom"]

            if "type" in data:
                s.type = data["type"]
            if "localite" in data:
                s.localite = data["localite"]

            db.flush()
            return StructureService._to_dict(s)

    # ====================================================================
    # DELETE
    # ====================================================================
    @staticmethod
    def delete(structure_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Supprime une structure.

        Args:
            structure_id: ID de la structure
            force: si True, autorise la suppression même s'il reste des agents
                   (les agents auront structure_id=NULL)

        Raises:
            StructureAvecAgentsError: si des agents y sont rattachés et force=False
        """
        with get_session() as db:
            s = db.query(Structure).filter_by(id=structure_id).first()
            if not s:
                raise StructureIntrouvableError(
                    f"Structure ID={structure_id} introuvable."
                )

            nb_agents = db.query(Personnel).filter_by(structure_id=structure_id).count()
            if nb_agents > 0 and not force:
                raise StructureAvecAgentsError(
                    f"Impossible de supprimer '{s.nom}' : "
                    f"{nb_agents} agent(s) y sont encore rattachés."
                )

            snapshot = StructureService._to_dict(s)
            snapshot["nb_agents_avant_suppression"] = nb_agents

            db.delete(s)
            db.flush()
            return snapshot

    # ====================================================================
    # HELPERS
    # ====================================================================
    @staticmethod
    def _to_dict(s: Structure) -> Dict[str, Any]:
        if not s:
            return None
        return {
            "id": s.id,
            "nom": s.nom,
            "type": s.type,
            "localite": s.localite,
        }