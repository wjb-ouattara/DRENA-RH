"""
========================================================================
DRENAET-RH — Orchestrateur de l'application
========================================================================
Gère le cycle de vie des fenêtres :
  Login → Main → Logout → Login → ...

Comportement :
- Au démarrage : affiche LoginWindow
- Après login : ferme LoginWindow, affiche MainWindow
- Après logout : ferme MainWindow, ré-affiche LoginWindow vide
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from config import settings
from src.ui.login_window import LoginWindow
from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class DrenaetRHApp:
    """Application DRENAET-RH (orchestrateur)."""

    def __init__(self):
        # Créer l'application Qt
        self.qapp = QApplication(sys.argv)
        self.qapp.setApplicationName(settings.APP_NAME)
        self.qapp.setApplicationVersion(settings.APP_VERSION)
        self.qapp.setOrganizationName(settings.APP_ORGANIZATION)

        # Charger la feuille de style
        self._load_stylesheet()

        # Définir la police par défaut
        default_font = QFont(settings.FONTS["primary"], 10)
        self.qapp.setFont(default_font)

        # Fenêtres
        self.login_window = None
        self.main_window = None

    # ================================================================
    def _load_stylesheet(self):
        """Charge le fichier QSS principal."""
        qss_file = settings.STYLES_DIR / "main.qss"
        if qss_file.exists():
            try:
                with open(qss_file, "r", encoding="utf-8") as f:
                    qss = f.read()
                self.qapp.setStyleSheet(qss)
                logger.info(f"✓ Feuille de style chargée : {qss_file}")
            except Exception as e:
                logger.warning(f"Impossible de charger {qss_file} : {e}")
        else:
            logger.warning(f"Feuille de style introuvable : {qss_file}")

    # ================================================================
    def run(self) -> int:
        """Lance l'application : affiche le login."""
        self._show_login()
        return self.qapp.exec()

    # ================================================================
    def _show_login(self):
        """Affiche la fenêtre de login."""
        # Fermer la main window si elle existe
        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        # Créer / réinitialiser la fenêtre de login
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.login_success.connect(self._on_login_success)

        self.login_window.clear_fields()
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()

    # ================================================================
    def _on_login_success(self, user):
        """Callback : login réussi → afficher la fenêtre principale."""
        logger.info(f"Login OK → affichage de la fenêtre principale ({user.login})")

        # Fermer le login
        if self.login_window:
            self.login_window.hide()

        # Créer la main window
        self.main_window = MainWindow()
        self.main_window.logout_requested.connect(self._on_logout)
        self.main_window.show()

    # ================================================================
    def _on_logout(self):
        """Callback : déconnexion demandée → retour au login."""
        logger.info("Déconnexion → retour au login")
        self._show_login()
