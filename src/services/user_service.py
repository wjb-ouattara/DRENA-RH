"""
========================================================================
DRENAET-RH — UserService
========================================================================
Service de gestion des comptes utilisateurs (Administration).

⚠️ CONCEPTION DÉFENSIVE / ADAPTATIVE ⚠️
Ce service a été écrit SANS accès direct au fichier src/models/utilisateur.py
existant. Pour ne PRENDRE AUCUN RISQUE de casser le système d'authentification
en place, il :

1. Réutilise la fonction de hashage de mots de passe déjà présente dans
   auth_service.py (si elle existe), plutôt que d'en écrire une nouvelle.
   Fallback sur bcrypt (confirmé par BCRYPT_ROUNDS=12 dans config/settings.py)
   UNIQUEMENT si aucune fonction n'est trouvée.

2. Détecte automatiquement le nom du champ "mot de passe hashé" du modèle
   Utilisateur en testant plusieurs noms courants (mot_de_passe_hash,
   password_hash, mot_de_passe, password...).

3. Lève une erreur explicite et compréhensible si la détection échoue,
   plutôt que de planter silencieusement ou corrompre des données.

Si tu vois une erreur "SchemaUtilisateurInconnuError" au premier lancement,
partage le contenu de src/models/utilisateur.py pour un ajustement précis.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import or_

from src.models import get_session
from src.models.utilisateur import Utilisateur


# ========================================================================
# EXCEPTIONS
# ========================================================================
class UserServiceException(Exception):
    pass


class SchemaUtilisateurInconnuError(UserServiceException):
    """Le schéma du modèle Utilisateur n'a pas pu être déterminé automatiquement."""
    pass


class LoginExistantError(UserServiceException):
    pass


class UtilisateurIntrouvableError(UserServiceException):
    pass


class ChampObligatoireError(UserServiceException):
    pass


# ========================================================================
# DÉTECTION ADAPTATIVE DU CHAMP MOT DE PASSE
# ========================================================================
_PASSWORD_FIELD_CANDIDATES = [
    "mot_de_passe_hash", "password_hash", "mdp_hash",
    "mot_de_passe", "password", "mdp",
]

_ACTIF_FIELD_CANDIDATES = ["actif", "is_active", "active", "enabled"]

_ROLE_VALUES = ["admin", "operateur"]


def _detect_password_field() -> str:
    for f in _PASSWORD_FIELD_CANDIDATES:
        if hasattr(Utilisateur, f):
            return f
    raise SchemaUtilisateurInconnuError(
        "Impossible de déterminer le champ 'mot de passe' du modèle Utilisateur. "
        f"Champs testés : {_PASSWORD_FIELD_CANDIDATES}. "
        "Merci de partager le contenu de src/models/utilisateur.py pour ajustement."
    )


def _detect_actif_field() -> Optional[str]:
    """Retourne None si le modèle n'a pas de notion d'actif/inactif (tous actifs par défaut)."""
    for f in _ACTIF_FIELD_CANDIDATES:
        if hasattr(Utilisateur, f):
            return f
    return None


PASSWORD_FIELD = None  # résolu paresseusement au premier appel
ACTIF_FIELD = None
_ACTIF_RESOLVED = False


def _get_password_field() -> str:
    global PASSWORD_FIELD
    if PASSWORD_FIELD is None:
        PASSWORD_FIELD = _detect_password_field()
    return PASSWORD_FIELD


def _get_actif_field() -> Optional[str]:
    global ACTIF_FIELD, _ACTIF_RESOLVED
    if not _ACTIF_RESOLVED:
        ACTIF_FIELD = _detect_actif_field()
        _ACTIF_RESOLVED = True
    return ACTIF_FIELD


# ========================================================================
# HASHAGE — réutilise auth_service.py si possible
# ========================================================================
def _hash_password(plain_password: str) -> str:
    """Hash un mot de passe, en réutilisant la logique existante si possible."""
    try:
        from src.services.auth_service import hash_password as existing_hash
        return existing_hash(plain_password)
    except ImportError:
        pass

    # Fallback bcrypt (cohérent avec BCRYPT_ROUNDS=12 de config/settings.py)
    try:
        import bcrypt
        from config import settings as app_config
        rounds = getattr(app_config, "BCRYPT_ROUNDS", 12)
        return bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)
        ).decode("utf-8")
    except ImportError:
        raise UserServiceException(
            "Impossible de hasher le mot de passe : ni auth_service.hash_password "
            "ni le module bcrypt ne sont disponibles."
        )


# ========================================================================
class UserService:
    """Service de gestion des comptes utilisateurs."""

    ROLES_VALIDES = _ROLE_VALUES

    # ====================================================================
    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        """Liste tous les utilisateurs (sans exposer le mot de passe hashé)."""
        with get_session() as db:
            users = db.query(Utilisateur).order_by(Utilisateur.login).all()
            return [UserService._to_dict(u) for u in users]

    # ====================================================================
    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        with get_session() as db:
            u = db.query(Utilisateur).filter_by(id=user_id).first()
            return UserService._to_dict(u) if u else None

    @staticmethod
    def get_by_login(login: str) -> Optional[Dict[str, Any]]:
        with get_session() as db:
            u = db.query(Utilisateur).filter_by(login=login.strip()).first()
            return UserService._to_dict(u) if u else None

    # ====================================================================
    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouvel utilisateur.

        Args:
            data: {"login", "password", "nom_complet", "role"}
        """
        login = str(data.get("login", "")).strip()
        password = data.get("password", "")
        nom_complet = str(data.get("nom_complet", "")).strip()
        role = data.get("role", "operateur")

        if not login:
            raise ChampObligatoireError("Le login est obligatoire.")
        if not password or len(password) < 6:
            raise ChampObligatoireError("Le mot de passe doit contenir au moins 6 caractères.")
        if not nom_complet:
            raise ChampObligatoireError("Le nom complet est obligatoire.")
        if role not in UserService.ROLES_VALIDES:
            raise ChampObligatoireError(
                f"Rôle invalide : {role}. Valeurs acceptées : {UserService.ROLES_VALIDES}"
            )

        pwd_field = _get_password_field()
        hashed = _hash_password(password)

        with get_session() as db:
            existing = db.query(Utilisateur).filter_by(login=login).first()
            if existing:
                raise LoginExistantError(f"Le login '{login}' est déjà utilisé.")

            kwargs = {
                "login": login,
                "nom_complet": nom_complet,
                "role": role,
                pwd_field: hashed,
            }
            actif_field = _get_actif_field()
            if actif_field:
                kwargs[actif_field] = True

            user = Utilisateur(**kwargs)
            db.add(user)
            db.flush()
            return UserService._to_dict(user)

    # ====================================================================
    @staticmethod
    def update(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour un utilisateur (nom_complet, role, actif).
        Ne modifie PAS le mot de passe ici (voir reset_password).
        """
        with get_session() as db:
            user = db.query(Utilisateur).filter_by(id=user_id).first()
            if not user:
                raise UtilisateurIntrouvableError(f"Utilisateur ID={user_id} introuvable.")

            if "nom_complet" in data and data["nom_complet"]:
                user.nom_complet = data["nom_complet"].strip()

            if "role" in data and data["role"]:
                if data["role"] not in UserService.ROLES_VALIDES:
                    raise ChampObligatoireError(f"Rôle invalide : {data['role']}")
                user.role = data["role"]

            actif_field = _get_actif_field()
            if actif_field and "actif" in data:
                setattr(user, actif_field, bool(data["actif"]))

            db.flush()
            return UserService._to_dict(user)

    # ====================================================================
    @staticmethod
    def reset_password(user_id: int, new_password: str) -> Dict[str, Any]:
        """Change le mot de passe d'un utilisateur (réinitialisation par l'admin)."""
        if not new_password or len(new_password) < 6:
            raise ChampObligatoireError("Le mot de passe doit contenir au moins 6 caractères.")

        pwd_field = _get_password_field()
        hashed = _hash_password(new_password)

        with get_session() as db:
            user = db.query(Utilisateur).filter_by(id=user_id).first()
            if not user:
                raise UtilisateurIntrouvableError(f"Utilisateur ID={user_id} introuvable.")
            setattr(user, pwd_field, hashed)
            db.flush()
            return UserService._to_dict(user)

    # ====================================================================
    @staticmethod
    def toggle_actif(user_id: int) -> Dict[str, Any]:
        """Active/désactive un compte (empêche la connexion sans le supprimer)."""
        actif_field = _get_actif_field()
        if not actif_field:
            raise UserServiceException(
                "Le modèle Utilisateur n'a pas de champ actif/inactif détecté. "
                "Utilisez plutôt la suppression si le modèle ne le supporte pas."
            )

        with get_session() as db:
            user = db.query(Utilisateur).filter_by(id=user_id).first()
            if not user:
                raise UtilisateurIntrouvableError(f"Utilisateur ID={user_id} introuvable.")
            current = getattr(user, actif_field)
            setattr(user, actif_field, not current)
            db.flush()
            return UserService._to_dict(user)

    # ====================================================================
    @staticmethod
    def delete(user_id: int, current_user_login: str = None) -> Dict[str, Any]:
        """
        Supprime un utilisateur.

        Protection : un utilisateur ne peut pas se supprimer lui-même.
        """
        with get_session() as db:
            user = db.query(Utilisateur).filter_by(id=user_id).first()
            if not user:
                raise UtilisateurIntrouvableError(f"Utilisateur ID={user_id} introuvable.")

            if current_user_login and user.login == current_user_login:
                raise UserServiceException("Vous ne pouvez pas supprimer votre propre compte.")

            snapshot = UserService._to_dict(user)
            db.delete(user)
            db.flush()
            return snapshot

    # ====================================================================
    @staticmethod
    def count_admins() -> int:
        """Compte le nombre d'administrateurs (protection anti-verrouillage)."""
        with get_session() as db:
            return db.query(Utilisateur).filter_by(role="admin").count()

    # ====================================================================
    @staticmethod
    def _to_dict(user: Utilisateur) -> Dict[str, Any]:
        if not user:
            return None
        actif_field = _get_actif_field()
        actif = getattr(user, actif_field) if actif_field else True

        return {
            "id": user.id,
            "login": user.login,
            "nom_complet": getattr(user, "nom_complet", None),
            "role": getattr(user, "role", None),
            "actif": actif,
        }