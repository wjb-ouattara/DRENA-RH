"""
========================================================================
DRENAET-RH — UserProfileCard
========================================================================
Carte profil utilisateur pour le bas de la sidebar — pattern moderne
repris des dashboards premium (Notion, Linear, Vercel) : avatar avec
initiales, nom, rôle, bouton de déconnexion intégré.

Usage dans main_window.py (_build_sidebar) :

    from src.ui.widgets.user_profile_card import UserProfileCard

    self.user_card = UserProfileCard()
    self.user_card.set_user("Administrateur", "admin")  # nom, rôle
    self.user_card.logout_clicked.connect(self.logout_requested.emit)
    sidebar_layout.addWidget(self.user_card)

Supporte le mode compact (sidebar réduite) via `.set_compact(bool)`,
même API que SidebarButton pour cohérence.
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame


ORANGE_SOFT_BG = "#FFEDD5"
ORANGE_TEXT = "#C2410C"
TEXT_DARK = "#1C1917"
TEXT_MUTED = "#78716C"
BORDER_LIGHT = "#F1F5F9"
HOVER_BG = "#F5F5F4"


class UserProfileCard(QWidget):
    """Carte profil utilisateur — bas de sidebar."""

    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._compact = False
        self._nom = "Utilisateur"
        self._role = "operateur"
        self.setStyleSheet("background: transparent;")
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_LIGHT}; border: none;")
        outer.addWidget(sep)

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.row = QHBoxLayout(self.content)
        self.row.setContentsMargins(16, 14, 12, 14)
        self.row.setSpacing(10)

        # Avatar (initiales sur fond orange doux)
        self.avatar = QLabel("?")
        self.avatar.setFixedSize(38, 38)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {ORANGE_SOFT_BG};
                color: {ORANGE_TEXT};
                border-radius: 19px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        self.row.addWidget(self.avatar)

        # Nom + rôle
        self.text_col = QVBoxLayout()
        self.text_col.setSpacing(1)

        self.name_lbl = QLabel(self._nom)
        self.name_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 12.5px; font-weight: bold; background: transparent;"
        )
        self.text_col.addWidget(self.name_lbl)

        self.role_lbl = QLabel("Opérateur")
        self.role_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10.5px; background: transparent;"
        )
        self.text_col.addWidget(self.role_lbl)

        self.row.addLayout(self.text_col, stretch=1)

        # Bouton déconnexion
        self.logout_btn = QPushButton()
        self.logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color=TEXT_MUTED))
        self.logout_btn.setIconSize(QSize(14, 14))
        self.logout_btn.setFixedSize(30, 30)
        self.logout_btn.setToolTip("Se déconnecter")
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #FEE2E2;
            }}
        """)
        self.logout_btn.clicked.connect(self.logout_clicked.emit)
        self.row.addWidget(self.logout_btn)

        outer.addWidget(self.content)

    # ====================================================================
    def set_user(self, nom_complet: str, role: str = "operateur"):
        """Met à jour les infos affichées (nom + rôle)."""
        self._nom = nom_complet or "Utilisateur"
        self._role = role or "operateur"

        initials = "".join(w[0].upper() for w in self._nom.split()[:2] if w)
        self.avatar.setText(initials or "?")

        self.name_lbl.setText(self._nom)
        role_labels = {"admin": "Administrateur", "operateur": "Opérateur"}
        self.role_lbl.setText(role_labels.get(self._role, self._role.title()))

    # ====================================================================
    def set_compact(self, compact: bool):
        """Mode compact : avatar centré seul, nom/rôle cachés, logout en dessous."""
        if self._compact == compact:
            return
        self._compact = compact

        if compact:
            self.row.setContentsMargins(0, 14, 0, 14)
            self.text_col.itemAt(0).widget().hide()
            self.text_col.itemAt(1).widget().hide()
            self.logout_btn.hide()
            self.row.setAlignment(self.avatar, Qt.AlignmentFlag.AlignCenter)
            self.avatar.setToolTip(f"{self._nom} — clic droit pour se déconnecter")
        else:
            self.row.setContentsMargins(16, 14, 12, 14)
            self.text_col.itemAt(0).widget().show()
            self.text_col.itemAt(1).widget().show()
            self.logout_btn.show()
            self.avatar.setToolTip("")