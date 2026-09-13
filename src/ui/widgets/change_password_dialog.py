"""
========================================================================
DRENAET-RH — ChangePasswordDialog
========================================================================
Popup permettant à l'utilisateur connecté (administrateur OU opérateur) de
changer SON PROPRE mot de passe, sans passer par le module Administration.

À ne pas confondre avec la réinitialisation par l'administrateur
(src/ui/administration/users_view.py) qui agit sur le compte d'un AUTRE
utilisateur et ne demande pas l'ancien mot de passe.

La vérification de l'ancien mot de passe, la longueur minimale et
l'interdiction de réutiliser l'ancien sont assurées par
AuthService.change_password() — aucune logique métier ici.

Usage :
    from src.ui.widgets.change_password_dialog import ChangePasswordDialog

    dialog = ChangePasswordDialog(self)
    dialog.exec()
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame,
)

from src.services.auth_service import AuthService, UserSession


# Palette "Light & Ember"
ORANGE_PRIMARY = "#F97316"
ORANGE_DARK = "#C2410C"
ORANGE_SOFT_BG = "#FFEDD5"
TEXT_DARK = "#1C1917"
TEXT_MUTED = "#78716C"
BORDER_LIGHT = "#E7E5E4"
DANGER = "#DC2626"
SUCCESS = "#128A4D"

# Longueur minimale, alignée sur AuthService.change_password()
LONGUEUR_MIN = 6


class ChangePasswordDialog(QDialog):
    """Popup de changement du mot de passe personnel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Changer mon mot de passe")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; }")
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(0)

        # === En-tête : icône + titre + utilisateur concerné ===
        entete = QHBoxLayout()
        entete.setSpacing(12)

        icone = QLabel()
        icone.setFixedSize(40, 40)
        icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icone.setPixmap(qta.icon("fa5s.key", color=ORANGE_DARK).pixmap(QSize(18, 18)))
        icone.setStyleSheet(
            f"background-color: {ORANGE_SOFT_BG}; border-radius: 20px;"
        )
        entete.addWidget(icone)

        colonne_titre = QVBoxLayout()
        colonne_titre.setSpacing(2)

        titre = QLabel("Changer mon mot de passe")
        titre.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 15px; font-weight: bold;"
        )
        colonne_titre.addWidget(titre)

        session = UserSession.get_instance()
        sous_titre = QLabel(
            f"Compte : {session.login or 'inconnu'}"
        )
        sous_titre.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11.5px;")
        colonne_titre.addWidget(sous_titre)

        entete.addLayout(colonne_titre, stretch=1)
        layout.addLayout(entete)

        layout.addSpacing(20)

        # === Champs (style souligné, sans encadrés) ===
        self.champ_actuel = self._ajouter_champ(
            layout, "Mot de passe actuel", "Saisissez votre mot de passe actuel"
        )
        layout.addSpacing(14)

        self.champ_nouveau = self._ajouter_champ(
            layout, "Nouveau mot de passe",
            f"Au moins {LONGUEUR_MIN} caractères",
        )
        layout.addSpacing(14)

        self.champ_confirmation = self._ajouter_champ(
            layout, "Confirmer le nouveau mot de passe",
            "Saisissez à nouveau le nouveau mot de passe",
        )

        layout.addSpacing(6)

        # === Zone de message (erreur / succès) ===
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setStyleSheet(f"color: {DANGER}; font-size: 11.5px;")
        self.message.setVisible(False)
        layout.addWidget(self.message)

        layout.addSpacing(16)

        # Filet fin de séparation avant les boutons
        filet = QFrame()
        filet.setFixedHeight(1)
        filet.setStyleSheet(f"background-color: {BORDER_LIGHT}; border: none;")
        layout.addWidget(filet)

        layout.addSpacing(16)

        # === Boutons ===
        boutons = QHBoxLayout()
        boutons.setSpacing(10)
        boutons.addStretch()

        self.bouton_annuler = QPushButton("Annuler")
        self.bouton_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_annuler.setFixedHeight(36)
        self.bouton_annuler.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_MUTED};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 8px;
                padding: 0 18px;
                font-size: 12.5px;
            }}
            QPushButton:hover {{ background-color: #F5F5F4; color: {TEXT_DARK}; }}
        """)
        self.bouton_annuler.clicked.connect(self.reject)
        boutons.addWidget(self.bouton_annuler)

        self.bouton_valider = QPushButton("Changer le mot de passe")
        self.bouton_valider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_valider.setFixedHeight(36)
        self.bouton_valider.setDefault(True)
        self.bouton_valider.setStyleSheet(f"""
            QPushButton {{
                background-color: {ORANGE_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 12.5px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ORANGE_DARK}; }}
            QPushButton:disabled {{ background-color: #E7E5E4; color: #A8A29E; }}
        """)
        self.bouton_valider.clicked.connect(self._on_valider)
        boutons.addWidget(self.bouton_valider)

        layout.addLayout(boutons)

        self.champ_actuel.setFocus()

    # ====================================================================
    def _ajouter_champ(self, layout: QVBoxLayout, libelle: str,
                       indication: str) -> QLineEdit:
        """Ajoute un couple libellé + champ mot de passe en style souligné."""
        etiquette = QLabel(libelle)
        etiquette.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(etiquette)

        champ = QLineEdit()
        champ.setEchoMode(QLineEdit.EchoMode.Password)
        champ.setPlaceholderText(indication)
        champ.setFixedHeight(34)
        champ.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {TEXT_DARK};
                border: none;
                border-bottom: 1px solid {BORDER_LIGHT};
                font-size: 13px;
                padding: 2px 0;
            }}
            QLineEdit:focus {{ border-bottom: 2px solid {ORANGE_PRIMARY}; }}
        """)
        champ.returnPressed.connect(self._on_valider)
        layout.addWidget(champ)
        return champ

    # ====================================================================
    def _afficher_erreur(self, texte: str):
        self.message.setStyleSheet(f"color: {DANGER}; font-size: 11.5px;")
        self.message.setText(texte)
        self.message.setVisible(True)

    # ====================================================================
    def _on_valider(self):
        """Valide la saisie puis délègue à AuthService.change_password()."""
        actuel = self.champ_actuel.text()
        nouveau = self.champ_nouveau.text()
        confirmation = self.champ_confirmation.text()

        # --- Contrôles de saisie (côté interface uniquement) ---
        if not actuel or not nouveau or not confirmation:
            self._afficher_erreur("Veuillez remplir les trois champs.")
            return

        if nouveau != confirmation:
            self._afficher_erreur(
                "Le nouveau mot de passe et sa confirmation ne correspondent pas."
            )
            self.champ_confirmation.clear()
            self.champ_confirmation.setFocus()
            return

        session = UserSession.get_instance()
        if not session.is_authenticated:
            self._afficher_erreur("Session expirée. Reconnectez-vous.")
            return

        # --- Délégation au service (vérification de l'ancien mot de passe,
        #     longueur minimale, interdiction de réutiliser l'ancien) ---
        self.bouton_valider.setEnabled(False)
        try:
            succes, message = AuthService.change_password(
                session.user_id, actuel, nouveau
            )
        except Exception as e:  # pragma: no cover — filet de sécurité
            self.bouton_valider.setEnabled(True)
            self._afficher_erreur(f"Erreur inattendue : {e}")
            return
        self.bouton_valider.setEnabled(True)

        if not succes:
            self._afficher_erreur(message)
            self.champ_actuel.selectAll()
            self.champ_actuel.setFocus()
            return

        QMessageBox.information(
            self,
            "Mot de passe modifié",
            "<b>Votre mot de passe a été changé avec succès.</b>"
            "<br><br>Il vous sera demandé à votre prochaine connexion.",
        )
        self.accept()
