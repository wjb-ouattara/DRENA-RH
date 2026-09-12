"""
========================================================================
DRENAET-RH — Service d'authentification
========================================================================
Gère :
- Le login / logout
- Le hashage et la vérification des mots de passe (bcrypt)
- Le suivi des tentatives de login (blocage temporaire)
- La traçabilité des connexions
- Les sessions utilisateurs
"""

import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from src.models import get_session, Utilisateur

logger = logging.getLogger(__name__)


# ========================================================================
# Helpers bcrypt
# ========================================================================
def hash_password(password: str) -> str:
    """Hash un mot de passe en clair avec bcrypt."""
    if not password or len(password) < 4:
        raise ValueError("Le mot de passe doit faire au moins 4 caractères.")
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(password_clear: str, password_hash: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond au hash."""
    if not password_clear or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password_clear.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Erreur vérification password : {e}")
        return False


# ========================================================================
# Session utilisateur en mémoire
# ========================================================================
class UserSession:
    """
    Représente la session d'un utilisateur connecté.
    Singleton : un seul utilisateur connecté à la fois sur l'app desktop.
    """
    _instance: Optional["UserSession"] = None

    def __init__(self):
        self.user_id: Optional[int] = None
        self.login: Optional[str] = None
        self.nom_complet: Optional[str] = None
        self.role: Optional[str] = None
        self.connected_at: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None

    @classmethod
    def get_instance(cls) -> "UserSession":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def login_user(self, user: Utilisateur) -> None:
        """Enregistre la connexion d'un utilisateur dans la session."""
        self.user_id = user.id
        self.login = user.login
        self.nom_complet = user.nom_complet
        self.role = user.role
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    def logout(self) -> None:
        """Vide la session (déconnexion)."""
        self.user_id = None
        self.login = None
        self.nom_complet = None
        self.role = None
        self.connected_at = None
        self.last_activity = None

    def touch(self) -> None:
        """Met à jour la dernière activité (pour le timeout)."""
        self.last_activity = datetime.utcnow()

    @property
    def is_timed_out(self) -> bool:
        """Renvoie True si la session a expiré par inactivité."""
        if self.last_activity is None:
            return False
        elapsed = datetime.utcnow() - self.last_activity
        return elapsed > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)


# ========================================================================
# AUTHENTIFICATION
# ========================================================================
class AuthService:
    """Service de gestion de l'authentification."""

    @staticmethod
    def authenticate(login: str, password: str) -> tuple[bool, str, Optional[Utilisateur]]:
        """
        Tente d'authentifier un utilisateur.

        Returns:
            (success: bool, message: str, user: Utilisateur | None)
        """
        if not login or not password:
            return False, "Identifiants manquants.", None

        login = login.strip().lower()

        with get_session() as db:
            user = db.query(Utilisateur).filter_by(login=login).first()

            # Utilisateur inexistant
            if user is None:
                logger.info(f"Tentative login échouée : login '{login}' inconnu")
                return False, "Identifiants incorrects.", None

            # Compte désactivé
            if not user.actif:
                logger.warning(f"Tentative login sur compte désactivé : {login}")
                return False, "Ce compte a été désactivé.", None

            # Compte bloqué temporairement
            if user.est_bloque:
                temps_restant = (user.bloque_jusqu_a - datetime.utcnow()).total_seconds() / 60
                msg = f"Compte bloqué temporairement. Réessayez dans {int(temps_restant)+1} minute(s)."
                logger.warning(f"Tentative login sur compte bloqué : {login}")
                return False, msg, None

            # Vérification du mot de passe
            if not verify_password(password, user.mot_de_passe_hash):
                user.tentatives_login += 1
                logger.info(f"Tentative login échouée pour '{login}' "
                            f"(tentatives = {user.tentatives_login}/{settings.MAX_LOGIN_ATTEMPTS})")

                # Blocage si trop de tentatives
                if user.tentatives_login >= settings.MAX_LOGIN_ATTEMPTS:
                    user.bloque_jusqu_a = datetime.utcnow() + timedelta(minutes=15)
                    msg = f"Trop de tentatives. Compte bloqué 15 minutes."
                    logger.warning(f"Compte '{login}' bloqué pour tentatives excessives")
                    return False, msg, None

                restant = settings.MAX_LOGIN_ATTEMPTS - user.tentatives_login
                return False, f"Identifiants incorrects. {restant} tentative(s) restante(s).", None

            # Succès : reset du compteur, update connexion
            user.tentatives_login = 0
            user.bloque_jusqu_a = None
            user.derniere_connexion = datetime.utcnow()
            user.nb_connexions += 1

            # Détacher l'objet pour pouvoir l'utiliser hors session
            db.flush()
            db.refresh(user)
            db.expunge(user)

            # Mise à jour de la session globale
            UserSession.get_instance().login_user(user)

            logger.info(f"✓ Login réussi : {login} ({user.role})")
            return True, "Connexion réussie.", user

    @staticmethod
    def logout() -> None:
        """Déconnecte l'utilisateur courant."""
        session = UserSession.get_instance()
        if session.is_authenticated:
            logger.info(f"Logout : {session.login}")
            session.logout()

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """
        Permet à un utilisateur de changer son propre mot de passe.

        Returns:
            (success, message)
        """
        if len(new_password) < 6:
            return False, "Le nouveau mot de passe doit faire au moins 6 caractères."
        if new_password == old_password:
            return False, "Le nouveau mot de passe doit être différent de l'ancien."

        with get_session() as db:
            user = db.query(Utilisateur).filter_by(id=user_id).first()
            if not user:
                return False, "Utilisateur introuvable."

            # Vérifier l'ancien mot de passe
            if not verify_password(old_password, user.mot_de_passe_hash):
                return False, "Ancien mot de passe incorrect."

            # Mettre à jour
            user.mot_de_passe_hash = hash_password(new_password)
            user.doit_changer_mdp = False

            logger.info(f"Mot de passe changé pour {user.login}")
            return True, "Mot de passe changé avec succès."
