"""
========================================================================
DRENAET-RH — LoginWindow (VERSION 2 — Redesign professionnel)
========================================================================
Écran de connexion en "carte flottante" avec ombre portée, split-screen :
- Panneau gauche : identité de marque (dégradé orange, motifs
  géométriques peints, logo, tagline) — couleurs du drapeau ivoirien
- Panneau droit : formulaire de connexion épuré (login, mot de passe,
  bouton, gestion d'erreur, option "se souvenir de moi")

Architecture volontairement DÉCOUPLÉE de la logique d'authentification :
cette classe ne connaît RIEN du système d'auth existant. Elle expose :

    login_submitted = pyqtSignal(str, str)   # (login, password)
    show_error(message: str)                 # afficher une erreur
    set_loading(is_loading: bool)             # état "connexion en cours"
    clear_password()                          # vider le champ mot de passe

L'appelant (app.py / main.py) branche `login_submitted` sur sa fonction
d'authentification existante, appelle `show_error()` en cas d'échec et
ferme cette fenêtre + ouvre MainWindow en cas de succès. Voir l'exemple
d'intégration en bas de ce fichier.

Fenêtre frameless avec fond transparent : le "vrai" contenu est une
carte blanche à coins arrondis avec QGraphicsDropShadowEffect, qui
flotte visuellement sur le bureau — effet moderne, pas une fenêtre plate.
"""

import sys
from pathlib import Path

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QPixmap, QIcon, QFont, QKeyEvent,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QCheckBox, QApplication,
)


# ========================================================================
# PALETTE — identité régionale (drapeau Côte d'Ivoire : orange/blanc/vert)
# ========================================================================
ORANGE_PRIMARY = "#F97316"
ORANGE_DARK = "#C2410C"
ORANGE_DEEP = "#9A3412"
GREEN_CI = "#128A4D"
NAVY_TEXT = "#1E1B4B"
GRAY_TEXT = "#64748B"
GRAY_BORDER = "#E2E8F0"
DANGER_BG = "#FEF2F2"
DANGER_TEXT = "#DC2626"
DANGER_BORDER = "#FECACA"


# ========================================================================
# AUTHENTIFICATION — appel direct à AuthService.authenticate()
# ========================================================================
def _authenticate(login: str, password: str):
    """
    Authentifie via le vrai service existant.

    AuthService.authenticate() retourne (success: bool, message: str,
    user: Utilisateur | None). On relaie directement ce triplet.
    """
    from src.services.auth_service import AuthService
    return AuthService.authenticate(login, password)


# ========================================================================
# PANNEAU DE MARQUE (gauche) — motifs géométriques peints
# ========================================================================
class BrandPanel(QFrame):
    """Panneau gauche : dégradé orange + motifs géométriques + logo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(420)
        self.setStyleSheet("border: none;")
        self._build_content()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0.0, QColor(ORANGE_PRIMARY))
        gradient.setColorAt(1.0, QColor(ORANGE_DEEP))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRect(rect)

        painter.setBrush(QColor(255, 255, 255, 18))
        painter.drawEllipse(QPoint(rect.width() + 40, -40), 180, 180)
        painter.drawEllipse(QPoint(-60, rect.height() - 80), 140, 140)

        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawEllipse(QPoint(rect.width() - 30, rect.height() + 20), 110, 110)

        strip_w = 5
        strip_x = rect.width() - 18
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(QRectF(strip_x, rect.height() * 0.36, strip_w, rect.height() * 0.22), 2.5, 2.5)
        painter.setBrush(QColor(GREEN_CI))
        painter.drawRoundedRect(QRectF(strip_x, rect.height() * 0.61, strip_w, rect.height() * 0.22), 2.5, 2.5)

        painter.end()

    def _build_content(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 50, 44, 40)
        layout.setSpacing(0)

        logo_lbl = QLabel()
        logo_path = self._find_logo()
        if logo_path and logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled = pixmap.scaled(
                76, 76, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(scaled)
        else:
            logo_lbl.setPixmap(qta.icon("fa5s.graduation-cap", color="#FFFFFF").pixmap(QSize(60, 60)))
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(logo_lbl)

        layout.addSpacing(28)

        app_title = QLabel("DRENAET-RH")
        app_title.setStyleSheet(
            "color: #FFFFFF; font-size: 26px; font-weight: bold; background: transparent; border: none;"
        )
        layout.addWidget(app_title)

        subtitle = QLabel("DRENAET de Katiola")
        subtitle.setStyleSheet(
            "color: rgba(255,255,255,210); font-size: 13px; background: transparent; border: none;"
        )
        layout.addWidget(subtitle)

        layout.addSpacing(50)

        tagline = QLabel(
            "Système intégré de gestion des ressources humaines "
            "au service de l'administration régionale de l'éducation."
        )
        tagline.setWordWrap(True)
        tagline.setStyleSheet(
            "color: rgba(255,255,255,235); font-size: 14px; background: transparent; border: none;"
        )
        layout.addWidget(tagline)

        layout.addStretch()

        for icon_name, text in [
            ("fa5s.file-signature", "Documents officiels automatisés"),
            ("fa5s.users-cog", "Gestion centralisée du personnel"),
            ("fa5s.shield-alt", "Traçabilité complète des actions"),
        ]:
            layout.addWidget(self._build_feature_row(icon_name, text))
            layout.addSpacing(14)

        layout.addStretch()

        version = QLabel("v1.0.0  ·  © 2026")
        version.setStyleSheet(
            "color: rgba(255,255,255,150); font-size: 10px; background: transparent; border: none;"
        )
        layout.addWidget(version)

    def _build_feature_row(self, icon_name: str, text: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        icon_bg = QLabel()
        icon_bg.setFixedSize(30, 30)
        icon_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_bg.setStyleSheet(
            "background-color: rgba(255,255,255,30); border-radius: 15px; border: none;"
        )
        icon_bg.setPixmap(qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(14, 14)))
        row.addWidget(icon_bg)

        lbl = QLabel(text)
        lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; background: transparent; border: none;")
        lbl.setWordWrap(True)
        row.addWidget(lbl, stretch=1)

        return w

    def _find_logo(self):
        try:
            from config import settings as app_config
            return app_config.IMAGES_DIR / "logo_drena.png"
        except Exception:
            return None


# ========================================================================
# CHAMP DE SAISIE STYLISÉ
# ========================================================================
def _make_field(placeholder: str, icon_name: str, password: bool = False) -> QLineEdit:
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setMinimumHeight(48)
    if password:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setStyleSheet(f"""
        QLineEdit {{
            background-color: #F8FAFC;
            border: 1.5px solid {GRAY_BORDER};
            border-radius: 10px;
            padding: 4px 14px 4px 40px;
            font-size: 13px;
            color: {NAVY_TEXT};
        }}
        QLineEdit:focus {{
            border-color: {ORANGE_PRIMARY};
            background-color: #FFFFFF;
        }}
    """)
    action = field.addAction(
        qta.icon(icon_name, color=GRAY_TEXT), QLineEdit.ActionPosition.LeadingPosition
    )
    return field


# ========================================================================
# FENÊTRE DE CONNEXION
# ========================================================================
class LoginWindow(QWidget):
    """Fenêtre de connexion — carte flottante avec ombre, split-screen.

    Contrat exact attendu par app.py (DrenaetRHApp) :
    - `login_success(object)` émis avec l'objet Utilisateur authentifié
    - `clear_fields()` appelée avant chaque affichage (reset du formulaire)

    L'authentification passe par AuthService.authenticate(login, password)
    -> (success, message, user), déjà implémenté dans auth_service.py.
    """

    login_success = pyqtSignal(object)  # émet l'objet Utilisateur authentifié
    # Signal bonus (optionnel, pour du code tiers éventuel) : (login, password)
    login_submitted = pyqtSignal(str, str)

    CARD_WIDTH = 940
    CARD_HEIGHT = 560

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.CARD_WIDTH + 60, self.CARD_HEIGHT + 60)

        self._drag_pos = None
        self._build_ui()
        self._center_on_screen()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 30, 30, 30)

        self.card = QFrame()
        self.card.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 18px;
                border: 1px solid {GRAY_BORDER};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(60)
        shadow.setXOffset(0)
        shadow.setYOffset(18)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self.brand_panel = BrandPanel()
        self.brand_panel.setStyleSheet(
            self.brand_panel.styleSheet()
            + "border-top-left-radius: 18px; border-bottom-left-radius: 18px;"
        )
        card_layout.addWidget(self.brand_panel)

        card_layout.addWidget(self._build_form_panel(), stretch=1)

        outer.addWidget(self.card)

        self.close_btn = QPushButton(self)
        self.close_btn.setIcon(qta.icon("fa5s.times", color="#94A3B8"))
        self.close_btn.setIconSize(QSize(14, 14))
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
            QPushButton:hover { background-color: #FEE2E2; }
        """)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.move(self.width() - 58, 22)

    # ====================================================================
    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: transparent; border: none;")

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(64, 56, 64, 44)
        outer.setSpacing(0)
        outer.addStretch(1)

        title = QLabel("Bienvenue")
        title.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 26px; font-weight: bold; background: transparent; border: none;"
        )
        outer.addWidget(title)

        subtitle = QLabel("Connectez-vous pour accéder à votre espace de travail.")
        subtitle.setStyleSheet(
            f"color: {GRAY_TEXT}; font-size: 13px; background: transparent; border: none;"
        )
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        outer.addSpacing(32)

        self.error_banner = QLabel()
        self.error_banner.setWordWrap(True)
        self.error_banner.setStyleSheet(f"""
            QLabel {{
                background-color: {DANGER_BG};
                color: {DANGER_TEXT};
                border: 1px solid {DANGER_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        self.error_banner.hide()
        outer.addWidget(self.error_banner)
        outer.addSpacing(14)

        login_label = QLabel("IDENTIFIANT")
        login_label.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 10px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        outer.addWidget(login_label)
        outer.addSpacing(6)

        self.login_input = _make_field("Votre identifiant", "fa5s.user")
        self.login_input.returnPressed.connect(self._focus_password)
        outer.addWidget(self.login_input)

        outer.addSpacing(18)

        pwd_label = QLabel("MOT DE PASSE")
        pwd_label.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 10px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        outer.addWidget(pwd_label)
        outer.addSpacing(6)

        self.password_input = _make_field("Votre mot de passe", "fa5s.lock", password=True)
        self.password_input.returnPressed.connect(self._on_submit)
        self._toggle_action = self.password_input.addAction(
            qta.icon("fa5s.eye", color=GRAY_TEXT), QLineEdit.ActionPosition.TrailingPosition
        )
        self._toggle_action.triggered.connect(self._toggle_password_visibility)
        self._password_visible = False
        outer.addWidget(self.password_input)

        outer.addSpacing(8)

        self.capslock_warning = QLabel("⚠  Verr. Maj activé")
        self.capslock_warning.setStyleSheet(
            f"color: {ORANGE_DARK}; font-size: 10.5px; background: transparent; border: none;"
        )
        self.capslock_warning.hide()
        outer.addWidget(self.capslock_warning)

        outer.addSpacing(10)

        self.remember_check = QCheckBox("Se souvenir de mon identifiant")
        self.remember_check.setStyleSheet(
            f"color: {GRAY_TEXT}; font-size: 12px; background: transparent; border: none;"
        )
        outer.addWidget(self.remember_check)

        outer.addSpacing(26)

        self.submit_btn = QPushButton("Se connecter")
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.setFixedHeight(48)
        self.submit_btn.setIcon(qta.icon("fa5s.sign-in-alt", color="#FFFFFF"))
        self.submit_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ORANGE_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ORANGE_DARK}; }}
            QPushButton:disabled {{ background-color: #FDBA74; }}
        """)
        self.submit_btn.clicked.connect(self._on_submit)
        outer.addWidget(self.submit_btn)

        outer.addStretch(2)

        footer = QLabel("Besoin d'aide ? Contactez le Service des Ressources Humaines.")
        footer.setStyleSheet(f"color: {GRAY_TEXT}; font-size: 10.5px; background: transparent; border: none;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(footer)

        return panel

    # ====================================================================
    def _focus_password(self):
        self.password_input.setFocus()

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_action.setIcon(qta.icon("fa5s.eye-slash", color=GRAY_TEXT))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_action.setIcon(qta.icon("fa5s.eye", color=GRAY_TEXT))

    def _on_submit(self):
        login = self.login_input.text().strip()
        password = self.password_input.text()

        if not login or not password:
            self.show_error("Merci de renseigner votre identifiant et votre mot de passe.")
            return

        self.hide_error()
        self.login_submitted.emit(login, password)  # signal bonus, informatif

        self.set_loading(True)
        QApplication.processEvents()

        try:
            success, message, user = _authenticate(login, password)
        except Exception as e:
            self.set_loading(False)
            self.show_error(f"Erreur technique : {e}")
            return

        self.set_loading(False)

        if success:
            self.login_success.emit(user)
        else:
            self.show_error(message or "Identifiant ou mot de passe incorrect.")
            self.clear_password()

    # ====================================================================
    # API PUBLIQUE (appelée par le code qui gère l'authentification)
    # ====================================================================
    def show_error(self, message: str):
        self.error_banner.setText(f"  {message}")
        self.error_banner.show()

    def hide_error(self):
        self.error_banner.hide()

    def set_loading(self, is_loading: bool):
        self.submit_btn.setEnabled(not is_loading)
        self.submit_btn.setText("Connexion en cours..." if is_loading else "Se connecter")
        self.login_input.setEnabled(not is_loading)
        self.password_input.setEnabled(not is_loading)

    def clear_password(self):
        self.password_input.clear()
        self.password_input.setFocus()

    def clear_fields(self):
        """
        Réinitialise le formulaire avant affichage.
        Appelée par app.py à chaque `_show_login()` (démarrage + après logout).

        Garde l'identifiant pré-rempli si "Se souvenir de moi" était coché,
        efface toujours le mot de passe et les messages d'erreur.
        """
        if not self.remember_check.isChecked():
            self.login_input.clear()
        self.password_input.clear()
        self.hide_error()
        self.capslock_warning.hide()
        self.set_loading(False)

        if self.login_input.text():
            self.password_input.setFocus()
        else:
            self.login_input.setFocus()

    def get_remembered_login(self) -> str:
        return self.login_input.text().strip() if self.remember_check.isChecked() else ""

    def set_login_text(self, login: str):
        self.login_input.setText(login)
        self.remember_check.setChecked(bool(login))
        self.password_input.setFocus()

    # ====================================================================
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_CapsLock:
            self.capslock_warning.setVisible(not self.capslock_warning.isVisible())
        super().keyPressEvent(event)

    # ====================================================================
    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ========================================================================
# INTÉGRATION
# ========================================================================
"""
Contrat exact respecté pour app.py (DrenaetRHApp) :

    self.login_window.login_success.connect(self._on_login_success)
    ...
    self.login_window.clear_fields()

L'authentification appelle directement AuthService.authenticate(login,
password) -> (success, message, user), et login_success émet l'objet
`user` (Utilisateur) tel quel — exactement ce que `_on_login_success(user)`
attend (il lit `user.login`).

Aucune autre modification n'est nécessaire dans app.py.
"""