"""
========================================================================
DRENAET-RH — Fenêtre principale (V3 — Thème clair "Light & Ember")
========================================================================
La fenêtre principale de l'application (affichée après login).

V3 :
- Sidebar en thème CLAIR (fond blanc, halo orange doux derrière le logo)
- Fix du bug d'intégration UserProfileCard (mauvais scope de variable)
- Couleurs fixées directement en Python (indépendant de main.qss)

Layout :
  ┌──────────────────────────────────────────────────────────┐
  │ CUSTOM TITLE BAR (logo + titre + boutons)                │
  ├─────────┬────────────────────────────────────────────────┤
  │         │ HEADER (titre page + utilisateur + logout)     │
  │ SIDEBAR ├────────────────────────────────────────────────┤
  │ (avec   │                                                │
  │ logo)   │  ZONE CENTRALE (QStackedWidget)                │
  │         │                                                │
  └─────────┴────────────────────────────────────────────────┘
"""

from pathlib import Path
from src.ui.personnel import PersonnelView

import qtawesome as qta
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSpacerItem, QSizePolicy,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon

from config import settings
from src.services.auth_service import AuthService, UserSession
from src.ui.widgets.sidebar_button import SidebarButton
from src.ui.widgets.custom_title_bar import CustomTitleBar
from src.ui.widgets.resizable_window_mixin import ResizableWindowMixin
from src.ui.dashboard_view import DashboardView
from src.ui.placeholder_view import PlaceholderView
from src.ui.absences import AbsencesView
from src.ui.statistics import StatisticsView
from src.ui.settings import SettingsView
from src.ui.administration import AdministrationView
from src.ui.widgets.user_profile_card import UserProfileCard


# ========================================================================
# PALETTE — "Light & Ember" (cohérente avec login / dashboard / settings)
# ========================================================================
SIDEBAR_BG = "#FFFFFF"
SIDEBAR_BORDER = "#F1F5F9"
TEXT_DARK = "#1C1917"
TEXT_MUTED = "#78716C"
FOOTER_MUTED = "#D6D3D1"
SEPARATOR_LIGHT = "#F1F5F9"
ORANGE_PRIMARY = "#F97316"


class MainWindow(ResizableWindowMixin, QMainWindow):
    """Fenêtre principale de l'application (frameless + redimensionnable)."""

    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(settings.APP_FULL_NAME)
        self.resize(
            settings.WINDOW_DEFAULT_WIDTH,
            settings.WINDOW_DEFAULT_HEIGHT,
        )
        self.setMinimumSize(
            settings.WINDOW_MIN_WIDTH,
            settings.WINDOW_MIN_HEIGHT,
        )

        icon_path = settings.IMAGES_DIR / "logo_drena.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.init_resize_tracking()

        self.menu_buttons = {}
        self.pages = {}

        self._sidebar_expanded = True
        self.SIDEBAR_WIDTH_FULL = settings.SIDEBAR_WIDTH
        self.SIDEBAR_WIDTH_COMPACT = 68

        self._build_ui()

    # ================================================================
    def _build_ui(self):
        """Construit l'interface principale."""
        central = QWidget()
        central.setObjectName("mainContainer")
        self.setCentralWidget(central)

        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # === BARRE TITRE CUSTOM (en haut) ===
        logo_path = settings.IMAGES_DIR / "logo_drena.png"
        self.title_bar = CustomTitleBar(
            title="DRENAET-RH",
            subtitle="Gestion des Ressources Humaines",
            logo_path=str(logo_path) if logo_path.exists() else None,
        )
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._on_maximize_toggle)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.toggle_sidebar_requested.connect(self._toggle_sidebar)
        outer_layout.addWidget(self.title_bar)

        # === ZONE PRINCIPALE (Sidebar | Header + Content) ===
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === SIDEBAR (gauche) — user_card intégrée DANS _build_sidebar ===
        self.sidebar = self._build_sidebar()
        main_layout.addWidget(self.sidebar)

        # === ZONE DROITE : Header + Content (vertical) ===
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header = self._build_header()
        right_layout.addWidget(self.header)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentArea")
        right_layout.addWidget(self.content_stack, stretch=1)

        self._add_pages()

        main_layout.addWidget(right_container, stretch=1)
        outer_layout.addWidget(main_widget, stretch=1)

        self._on_menu_click("dashboard")

    # ================================================================
    def _on_maximize_toggle(self):
        if self.isMaximized():
            self.showNormal()
            self.title_bar.update_maximize_icon(False)
        else:
            self.showMaximized()
            self.title_bar.update_maximize_icon(True)

    # ================================================================
    def _toggle_sidebar(self):
        """Bascule entre sidebar déployée (240px) et compacte (68px)."""
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

        self._sidebar_expanded = not self._sidebar_expanded

        target_width = (
            self.SIDEBAR_WIDTH_FULL if self._sidebar_expanded
            else self.SIDEBAR_WIDTH_COMPACT
        )

        self._anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self._anim_min.setDuration(220)
        self._anim_min.setStartValue(self.sidebar.width())
        self._anim_min.setEndValue(target_width)
        self._anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self._anim_max.setDuration(220)
        self._anim_max.setStartValue(self.sidebar.width())
        self._anim_max.setEndValue(target_width)
        self._anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)

        if self._sidebar_expanded:
            self.sidebar_header.show()
            self.sidebar_footer.show()
        else:
            self.sidebar_header.hide()
            self.sidebar_footer.hide()

        for btn in self.menu_buttons.values():
            btn.set_compact(not self._sidebar_expanded)

        self.user_card.set_compact(not self._sidebar_expanded)

        self._anim_min.start()
        self._anim_max.start()

    # ================================================================
    def _build_sidebar(self) -> QWidget:
        """Construit la sidebar gauche — thème clair, halo orange doux."""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(settings.SIDEBAR_WIDTH)
        sidebar.setMaximumWidth(settings.SIDEBAR_WIDTH)
        # Fond en dégradé vertical TRÈS subtil (orange pâle en haut → blanc)
        # + halo doux derrière le logo (voir sidebar_header plus bas).
        # Fixé directement en Python : garantit le thème clair indépendamment
        # de ce que contient ressources/styles/main.qss
        sidebar.setStyleSheet(f"""
            QWidget#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF7ED,
                    stop:0.35 #FFFFFF,
                    stop:1 #FFFFFF
                );
                border-right: 1px solid {SIDEBAR_BORDER};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === HEADER DE LA SIDEBAR (LOGO + nom) ===
        self.sidebar_header = QWidget()
        self.sidebar_header.setObjectName("sidebarHeader")
        # Halo orange doux derrière le logo (qradialgradient supporté par Qt)
        # — écho discret des cercles décoratifs de l'écran de connexion
        self.sidebar_header.setStyleSheet("""
            QWidget#sidebarHeader {
                background: qradialgradient(
                    cx:0.5, cy:0.25, radius:0.9, fx:0.5, fy:0.25,
                    stop:0 rgba(249, 115, 22, 28),
                    stop:0.6 rgba(249, 115, 22, 8),
                    stop:1 rgba(249, 115, 22, 0)
                );
            }
        """)
        header_layout = QVBoxLayout(self.sidebar_header)
        header_layout.setContentsMargins(20, 24, 20, 20)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_path = settings.IMAGES_DIR / "logo_drena.png"
        if logo_path.exists():
            self.sidebar_logo = QLabel()
            pixmap = QPixmap(str(logo_path))
            scaled = pixmap.scaled(
                QSize(120, 120),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.sidebar_logo.setPixmap(scaled)
            self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sidebar_logo.setStyleSheet("background: transparent;")
            header_layout.addWidget(self.sidebar_logo)
        else:
            # Fallback : icône Font Awesome — orange (le fond est blanc désormais)
            self.sidebar_logo = QLabel()
            self.sidebar_logo.setPixmap(
                qta.icon("fa5s.graduation-cap", color=ORANGE_PRIMARY).pixmap(QSize(64, 64))
            )
            self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sidebar_logo.setStyleSheet("background: transparent;")
            header_layout.addWidget(self.sidebar_logo)

        # Nom de l'app sous le logo — couleur fixée en Python (indépendant du QSS)
        self.sidebar_title = QLabel(settings.APP_NAME)
        self.sidebar_title.setObjectName("appLogo")
        self.sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_title.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 16px; font-weight: bold; background: transparent;"
        )
        header_layout.addWidget(self.sidebar_title)

        self.sidebar_subtitle = QLabel("DRENAET de Katiola")
        self.sidebar_subtitle.setObjectName("appSubtitle")
        self.sidebar_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_subtitle.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        header_layout.addWidget(self.sidebar_subtitle)

        layout.addWidget(self.sidebar_header)

        # === MENU PRINCIPAL ===
        layout.addSpacing(8)

        menus = [
            ("dashboard",    "fa5s.tachometer-alt",  "Dashboard",       True),
            ("personnel",    "fa5s.users",           "Personnel",       False),
            ("documents",    "fa5s.file-alt",        "Documents",       True),
            ("absences",     "fa5s.calendar-times",  "Absences",        False),
            ("statistics",   "fa5s.chart-bar",       "Statistiques",    False),
        ]

        for menu_id, icon_name, label, dispo in menus:
            btn = SidebarButton(
                icon_name=icon_name,
                label=label,
                page_id=menu_id,
            )
            btn.clicked.connect(lambda checked, mid=menu_id: self._on_menu_click(mid))
            layout.addWidget(btn)
            self.menu_buttons[menu_id] = btn

        layout.addStretch()

        # === SÉPARATEUR (clair) ===
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {SEPARATOR_LIGHT}; max-height: 1px; border: none;")
        layout.addWidget(sep)

        # === MENU SECONDAIRE (Paramètres / Admin) ===
        menus_bottom = [
            ("parametres",    "fa5s.cog",            "Paramètres",      False),
            ("administration","fa5s.user-shield",    "Administration",  False),
        ]

        layout.addSpacing(8)
        for menu_id, icon_name, label, dispo in menus_bottom:
            btn = SidebarButton(
                icon_name=icon_name,
                label=label,
                page_id=menu_id,
            )
            btn.clicked.connect(lambda checked, mid=menu_id: self._on_menu_click(mid))
            layout.addWidget(btn)
            self.menu_buttons[menu_id] = btn

        layout.addSpacing(8)

        # === CARTE PROFIL UTILISATEUR (bas de sidebar) ===
        self.user_card = UserProfileCard()
        session = UserSession.get_instance()
        if session.is_authenticated:
            self.user_card.set_user(session.nom_complet or session.login, session.role)
        self.user_card.logout_clicked.connect(self._on_logout_click)
        layout.addWidget(self.user_card)

        # === FOOTER DE LA SIDEBAR ===
        self.sidebar_footer = QLabel(f"v{settings.APP_VERSION}  •  © 2026")
        self.sidebar_footer.setObjectName("sidebarFooter")
        self.sidebar_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_footer.setStyleSheet(
            f"color: {FOOTER_MUTED}; font-size: 10px; background: transparent; padding: 8px 0;"
        )
        layout.addWidget(self.sidebar_footer)

        return sidebar

    # ================================================================
    def _build_header(self) -> QWidget:
        """Construit la barre du haut (header)."""
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(60)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        self.page_title = QLabel("Tableau de bord")
        self.page_title.setObjectName("pageTitle")
        layout.addWidget(self.page_title)

        layout.addStretch()

        session = UserSession.get_instance()
        if session.is_authenticated:
            user_icon = QLabel()
            user_icon.setPixmap(
                qta.icon("fa5s.user-circle", color="#F97316").pixmap(QSize(28, 28))
            )
            layout.addWidget(user_icon)

            user_info_box = QVBoxLayout()
            user_info_box.setSpacing(0)

            name_lbl = QLabel(session.nom_complet or session.login)
            name_lbl.setObjectName("userName")
            user_info_box.addWidget(name_lbl)

            role_lbl = QLabel(f"Rôle : {session.role}")
            role_lbl.setObjectName("userInfo")
            user_info_box.addWidget(role_lbl)

            layout.addLayout(user_info_box)

        self.logout_btn = QPushButton("  DÉCONNEXION")
        self.logout_btn.setObjectName("logoutBtn")
        self.logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color="#DC2626"))
        self.logout_btn.setIconSize(QSize(14, 14))
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.clicked.connect(self._on_logout_click)
        layout.addWidget(self.logout_btn)

        return header

    # ================================================================
    def _add_pages(self):
        """Ajoute les pages au QStackedWidget."""
        self.pages["dashboard"] = DashboardView()
        self.pages["dashboard"].navigate_requested.connect(self._on_dashboard_navigate)

        self.pages["personnel"] = PersonnelView()

        # === Module Documents ===
        from src.ui.documents.documents_view import DocumentsView
        from src.ui.documents.autorisation_form import AutorisationAbsenceForm
        from src.ui.documents.ordre_mission_form import OrdreMissionForm
        from src.ui.documents.attestation_travail_form import AttestationTravailForm
        from src.ui.documents.attestation_presence_form import AttestationPresenceForm
        from src.ui.documents.titre_conges_form import TitreCongesForm
        from src.ui.documents.certificat_prise_service_form import CertificatPriseServiceForm
        from src.ui.documents.certificat_cessation_form import CertificatCessationForm
        from src.ui.documents.fiche_mutation_form import FicheMutationForm

        docs_stack = QStackedWidget()
        docs_list = DocumentsView()
        docs_autorisation = AutorisationAbsenceForm()
        docs_ordre_mission = OrdreMissionForm()
        docs_attestation_travail = AttestationTravailForm()
        docs_attestation_presence = AttestationPresenceForm()
        docs_titre_conges = TitreCongesForm()
        docs_certificat_prise = CertificatPriseServiceForm()
        docs_certificat_cessation = CertificatCessationForm()
        docs_fiche_mutation = FicheMutationForm()

        docs_stack.addWidget(docs_list)
        docs_stack.addWidget(docs_autorisation)
        docs_stack.addWidget(docs_ordre_mission)
        docs_stack.addWidget(docs_attestation_travail)
        docs_stack.addWidget(docs_attestation_presence)
        docs_stack.addWidget(docs_titre_conges)
        docs_stack.addWidget(docs_certificat_prise)
        docs_stack.addWidget(docs_certificat_cessation)
        docs_stack.addWidget(docs_fiche_mutation)

        def open_doc_form(type_doc):
            mapping = {
                "autorisation_absence": 1,
                "ordre_mission": 2,
                "attestation_travail": 3,
                "attestation_presence": 4,
                "titre_conges": 5,
                "certificat_prise_service": 6,
                "certificat_cessation": 7,
                "fiche_mutation": 8,
            }
            if type_doc in mapping:
                docs_stack.setCurrentIndex(mapping[type_doc])

        docs_list.document_selected.connect(open_doc_form)
        docs_autorisation.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_ordre_mission.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_attestation_travail.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_attestation_presence.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_titre_conges.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_certificat_prise.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_certificat_cessation.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))
        docs_fiche_mutation.back_requested.connect(lambda: docs_stack.setCurrentIndex(0))

        self.pages["documents"] = docs_stack

        self.pages["absences"] = AbsencesView()
        self.pages["statistics"] = StatisticsView()
        self.pages["parametres"] = SettingsView()
        self.pages["administration"] = AdministrationView()

        for page_id, view in self.pages.items():
            self.content_stack.addWidget(view)

    def _on_dashboard_navigate(self, page_key: str):
        if page_key in self.menu_buttons:
            self.menu_buttons[page_key].click()

    # ================================================================
    def _on_menu_click(self, menu_id: str):
        for mid, btn in self.menu_buttons.items():
            btn.setChecked(mid == menu_id)

        if menu_id in self.pages:
            view = self.pages[menu_id]
            self.content_stack.setCurrentWidget(view)

            titles = {
                "dashboard":      "Tableau de bord",
                "personnel":      "Gestion du Personnel",
                "documents":      "Génération de Documents",
                "absences":       "Suivi des Absences",
                "statistics":     "Statistiques",
                "parametres":     "Paramètres",
                "administration": "Administration",
            }
            self.page_title.setText(titles.get(menu_id, ""))

    # ================================================================
    def _on_logout_click(self):
        reply = QMessageBox.question(
            self,
            "Confirmer la déconnexion",
            f"<b>Voulez-vous vraiment vous déconnecter ?</b>"
            f"<br><br>Vous reviendrez à l'écran de connexion.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            AuthService.logout()
            self.logout_requested.emit()

    # ================================================================
    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.update_maximize_icon(self.isMaximized())
        super().changeEvent(event)