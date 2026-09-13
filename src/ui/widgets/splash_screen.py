"""
========================================================================
DRENAET-RH — Écran de démarrage
========================================================================
Affiche une fenêtre d'attente pendant les préparatifs du lancement :
vérification du schéma de la base, chargement des paramètres et de la
feuille de style.

Sans cet écran, l'utilisateur ne voyait rien pendant plusieurs secondes
après le double-clic, ce qui donnait l'impression d'un blocage.
"""

import logging

from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRect

from config import settings

logger = logging.getLogger(__name__)

# Palette « Light & Ember », cohérente avec le reste de l'application
BLANC = "#FFFFFF"
ORANGE = "#F97316"
ORANGE_PALE = "#FFEDD5"
TEXTE = "#1C1917"
TEXTE_DOUX = "#78716C"

LARGEUR = 440
HAUTEUR = 300


class SplashDemarrage(QSplashScreen):
    """Fenêtre d'attente affichée pendant l'initialisation."""

    def __init__(self):
        super().__init__(self._construire_image())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    # ====================================================================
    def _construire_image(self) -> QPixmap:
        """Dessine le visuel : armoirie, nom de l'application, filet orange."""
        image = QPixmap(LARGEUR, HAUTEUR)
        image.fill(QColor(BLANC))

        p = QPainter(image)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            # Cadre discret : l'écran est sans bordure de fenêtre, un filet
            # évite qu'il se fonde dans un arrière-plan clair.
            p.setPen(QPen(QColor(ORANGE_PALE), 2))
            p.drawRect(1, 1, LARGEUR - 2, HAUTEUR - 2)

            # Bande orange en haut, rappel de l'identité visuelle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ORANGE))
            p.drawRect(0, 0, LARGEUR, 4)

            # Armoirie de Côte d'Ivoire, si elle est disponible
            armoirie = settings.IMAGES_DIR / "armoirie_ci.png"
            if armoirie.exists():
                logo = QPixmap(str(armoirie)).scaled(
                    96, 96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                p.drawPixmap((LARGEUR - logo.width()) // 2, 40, logo)
            else:
                logger.warning("Armoirie introuvable pour le splash : %s", armoirie)

            # Nom de l'application
            p.setPen(QColor(TEXTE))
            titre = QFont(settings.FONTS["primary"], 20)
            titre.setBold(True)
            p.setFont(titre)
            p.drawText(
                QRect(0, 150, LARGEUR, 34),
                Qt.AlignmentFlag.AlignCenter,
                settings.APP_NAME,
            )

            # Sous-titre
            p.setPen(QColor(TEXTE_DOUX))
            p.setFont(QFont(settings.FONTS["primary"], 9))
            p.drawText(
                QRect(0, 184, LARGEUR, 20),
                Qt.AlignmentFlag.AlignCenter,
                "Gestion des Ressources Humaines",
            )
            p.drawText(
                QRect(0, 204, LARGEUR, 20),
                Qt.AlignmentFlag.AlignCenter,
                settings.APP_ORGANIZATION,
            )
        finally:
            # Un QPainter non refermé laisse l'image inutilisable.
            p.end()

        return image

    # ====================================================================
    def etape(self, texte: str):
        """
        Affiche l'étape en cours et rend la main à Qt pour la redessiner.

        processEvents() est indispensable : l'initialisation est synchrone et
        monopolise la boucle d'événements, le message ne s'afficherait donc
        jamais.
        """
        self.showMessage(
            texte,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            QColor(TEXTE_DOUX),
        )
        QApplication.processEvents()
