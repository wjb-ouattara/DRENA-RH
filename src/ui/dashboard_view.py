"""
========================================================================
DRENAET-RH — Dashboard (VERSION 2 — Redesign professionnel)
========================================================================
Refonte complète du Dashboard :
- Palette ORANGE dominante (couleurs du drapeau ivoirien : orange/blanc/vert)
- Suppression de l'ancienne checklist "Sprint à venir" (obsolète — tous
  les sprints sont terminés) remplacée par 2 blocs réellement utiles :
    - Actions rapides (raccourcis vers les tâches fréquentes)
    - Activité récente (dernières actions de l'audit trail, données réelles)
- KPI cards uniformes avec icône en pastille colorée (plus de bandeau
  coloré arbitraire en haut des cartes)

Le Dashboard émet un signal `navigate_requested(str)` quand l'utilisateur
clique une action rapide, pour permettre à MainWindow de changer de page.
Si le signal n'est connecté à rien, les boutons restent inertes sans
provoquer d'erreur (comportement Qt standard).
"""

from datetime import date, datetime

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QSizePolicy,
)

from src.services.auth_service import UserSession


# ========================================================================
# PALETTE — identité régionale (drapeau Côte d'Ivoire : orange/blanc/vert)
# ========================================================================
ORANGE_PRIMARY = "#F97316"
ORANGE_DARK = "#C2410C"
ORANGE_LIGHT = "#FFEDD5"
GREEN_CI = "#128A4D"
GREEN_LIGHT = "#DCFCE7"
NAVY_TEXT = "#1E1B4B"
GRAY_TEXT = "#64748B"
GRAY_BORDER = "#E2E8F0"


# ========================================================================
# UTILITAIRES
# ========================================================================
def _format_date_fr(d: date) -> str:
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convertit '#RRGGBB' + alpha (0-1) en 'rgba(r, g, b, a)' pour Qt Stylesheets.
    Qt attend #AARRGGBB (alpha en premier) pour le format hex avec transparence,
    ce qui prête à confusion — rgba() explicite est plus fiable partout."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _get_agent_count() -> int:
    try:
        from src.models import get_session, Personnel
        with get_session() as db:
            return db.query(Personnel).count()
    except Exception:
        return 0


def _get_structure_count() -> int:
    try:
        from src.models import get_session, Structure
        with get_session() as db:
            return db.query(Structure).count()
    except Exception:
        return 0


def _get_document_count() -> int:
    try:
        from src.models import get_session
        from src.models.document import DocumentGenere
        with get_session() as db:
            today = date.today()
            annee = f"{today.year - 1}-{today.year}" if today.month < 9 else f"{today.year}-{today.year + 1}"
            return db.query(DocumentGenere).filter_by(annee_scolaire=annee).count()
    except Exception:
        return 0


def _get_absences_en_cours_count() -> int:
    try:
        from src.models import get_session
        from src.models.absence import Absence
        with get_session() as db:
            return db.query(Absence).filter_by(statut="En cours").count()
    except Exception:
        return 0


def _get_recent_activity(limit: int = 6):
    try:
        from src.services.audit_service import AuditService
        return AuditService.get_recent_activity(limit=limit)
    except Exception:
        return []


ACTION_ICONS = {"CREATE": "fa5s.plus-circle", "UPDATE": "fa5s.edit", "DELETE": "fa5s.trash-alt"}
ACTION_COLORS = {"CREATE": GREEN_CI, "UPDATE": "#3B82F6", "DELETE": "#DC2626"}
ACTION_LABELS = {"CREATE": "Création", "UPDATE": "Modification", "DELETE": "Suppression"}


# ========================================================================
# WIDGET KPI CARD (v2 — pastille colorée, sans bandeau)
# ========================================================================
class KpiCard(QFrame):
    """Carte KPI épurée : icône en pastille + valeur + libellé."""

    def __init__(self, title: str, value: str, icon_name: str, color: str, bg_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setMinimumHeight(110)
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: #FFFFFF;
                border: 1px solid {GRAY_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Pastille icône (pixmap dessiné DANS le label directement, pas d'enfant en positionnement absolu)
        badge = QLabel()
        badge.setFixedSize(52, 52)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border-radius: 26px;
                border: none;
            }}
        """)
        badge.setPixmap(qta.icon(icon_name, color=color).pixmap(QSize(22, 22)))
        layout.addWidget(badge)

        # Texte
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 28px; font-weight: bold; background: transparent; border: none;"
        )
        text_col.addWidget(value_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {GRAY_TEXT}; font-size: 12px; font-weight: 500; background: transparent; border: none;"
        )
        text_col.addWidget(title_lbl)

        layout.addLayout(text_col, stretch=1)


# ========================================================================
# WIDGET ACTION RAPIDE
# ========================================================================
class QuickActionButton(QPushButton):
    """Bouton d'action rapide, style carte cliquable."""

    def __init__(self, icon_name: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(52)
        self.setIcon(qta.icon(icon_name, color=color))
        self.setIconSize(QSize(18, 18))
        self.setText(f"   {label}")
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {NAVY_TEXT};
                border: 1px solid {GRAY_BORDER};
                border-radius: 8px;
                text-align: left;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {ORANGE_LIGHT};
                border-color: {color};
            }}
        """)


# ========================================================================
# DASHBOARD VIEW
# ========================================================================
class DashboardView(QWidget):
    """Page d'accueil du logiciel — version 2, orientée action."""

    # Émis quand l'utilisateur clique une action rapide.
    # value ∈ {"personnel", "documents", "absences", "statistiques"}
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_kpi_grid())
        layout.addWidget(self._build_bottom_row(), stretch=1)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ====================================================================
    def _build_header(self) -> QFrame:
        """En-tête épuré avec liseré tricolore CI en accent."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {GRAY_BORDER};
                border-radius: 12px;
            }}
        """)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Liseré tricolore (orange / blanc / vert) — clin d'œil au drapeau CI
        flag_strip = QWidget()
        flag_strip.setFixedHeight(5)
        flag_layout = QHBoxLayout(flag_strip)
        flag_layout.setContentsMargins(0, 0, 0, 0)
        flag_layout.setSpacing(0)
        for color in [ORANGE_PRIMARY, "#FFFFFF", GREEN_CI]:
            band = QWidget()
            band.setStyleSheet(f"background-color: {color}; border-top-left-radius: 0px;")
            flag_layout.addWidget(band)
        outer.addWidget(flag_strip)

        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(28, 20, 28, 20)
        content_layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        title = QLabel("Tableau de bord")
        title.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 22px; font-weight: bold; background: transparent; border: none;"
        )
        text_col.addWidget(title)

        session = UserSession.get_instance()
        user_name = session.nom_complet if session.is_authenticated else "Utilisateur"

        sub_row = QHBoxLayout()
        sub_row.setSpacing(8)

        cal_icon = QLabel()
        cal_icon.setPixmap(qta.icon("fa5s.calendar-alt", color=GRAY_TEXT).pixmap(QSize(13, 13)))
        cal_icon.setStyleSheet("background: transparent; border: none;")
        sub_row.addWidget(cal_icon)

        sub_lbl = QLabel(f"Bonjour, {user_name} · {_format_date_fr(date.today())}")
        sub_lbl.setStyleSheet(f"color: {GRAY_TEXT}; font-size: 12px; background: transparent; border: none;")
        sub_row.addWidget(sub_lbl)
        sub_row.addStretch()

        text_col.addLayout(sub_row)
        content_layout.addLayout(text_col, stretch=1)

        # Badge rôle
        role_label = "Administrateur" if session.is_authenticated and session.role == "admin" else "Opérateur"
        badge = QLabel(role_label)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {ORANGE_LIGHT};
                color: {ORANGE_DARK};
                border-radius: 14px;
                padding: 7px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        content_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        outer.addWidget(content)
        return card

    # ====================================================================
    def _build_kpi_grid(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        kpis = [
            ("Agents enregistrés", str(_get_agent_count()), "fa5s.users", ORANGE_DARK, ORANGE_LIGHT),
            ("Établissements suivis", str(_get_structure_count()), "fa5s.building", GREEN_CI, GREEN_LIGHT),
            ("Documents cette année", str(_get_document_count()), "fa5s.file-alt", "#2563EB", "#DBEAFE"),
            ("Absences en cours", str(_get_absences_en_cours_count()), "fa5s.calendar-times", "#B45309", "#FEF3C7"),
        ]

        for i, (title, value, icon, color, bg) in enumerate(kpis):
            grid.addWidget(KpiCard(title, value, icon, color, bg), 0, i)

        return w

    # ====================================================================
    def _build_bottom_row(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._build_quick_actions(), stretch=2)
        layout.addWidget(self._build_recent_activity(), stretch=3)

        return w

    def _build_section_frame(self, title: str, icon_name: str) -> tuple:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: #FFFFFF; border: 1px solid {GRAY_BORDER}; border-radius: 12px; }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=ORANGE_PRIMARY).pixmap(QSize(16, 16)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_row.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {NAVY_TEXT}; font-size: 14px; font-weight: bold; background: transparent; border: none;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        layout.addLayout(title_row)

        return frame, layout

    # ====================================================================
    def _build_quick_actions(self) -> QFrame:
        frame, layout = self._build_section_frame("Actions rapides", "fa5s.bolt")

        actions = [
            ("fa5s.user-plus", "Ajouter un agent", ORANGE_PRIMARY, "personnel"),
            ("fa5s.file-medical", "Générer un document", "#2563EB", "documents"),
            ("fa5s.file-import", "Importer un fichier Excel", GREEN_CI, "personnel"),
            ("fa5s.chart-bar", "Voir les statistiques", "#B45309", "statistiques"),
        ]

        for icon, label, color, target in actions:
            btn = QuickActionButton(icon, label, color)
            btn.clicked.connect(lambda checked, t=target: self.navigate_requested.emit(t))
            layout.addWidget(btn)

        layout.addStretch()
        return frame

    # ====================================================================
    def _build_recent_activity(self) -> QFrame:
        frame, layout = self._build_section_frame("Activité récente", "fa5s.history")

        entries = _get_recent_activity(limit=6)

        if not entries:
            empty = QLabel("Aucune activité enregistrée pour le moment.")
            empty.setStyleSheet(f"color: {GRAY_TEXT}; font-size: 12px; font-style: italic; background: transparent; border: none;")
            layout.addWidget(empty)
            layout.addStretch()
            return frame

        for entry in entries:
            layout.addWidget(self._build_activity_row(entry))

        layout.addStretch()
        return frame

    def _build_activity_row(self, entry: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        action = entry.get("action", "?")
        color = ACTION_COLORS.get(action, GRAY_TEXT)

        # Pastille icône (pixmap direct, sans enfant en positionnement absolu)
        badge = QLabel()
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background-color: {_hex_to_rgba(color, 0.14)}; border-radius: 16px; border: none;")
        badge.setPixmap(qta.icon(ACTION_ICONS.get(action, "fa5s.circle"), color=color).pixmap(QSize(14, 14)))
        layout.addWidget(badge)

        # Texte
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        main_txt = QLabel(
            f"<b>{ACTION_LABELS.get(action, action)}</b> — "
            f"{entry.get('personnel_nom_complet') or entry.get('personnel_matricule') or 'Agent'}"
        )
        main_txt.setStyleSheet(f"color: {NAVY_TEXT}; font-size: 12px; background: transparent; border: none;")
        text_col.addWidget(main_txt)

        sub_txt = QLabel(
            f"{self._format_relative(entry.get('date_action'))} · {entry.get('utilisateur_login', '?')}"
        )
        sub_txt.setStyleSheet(f"color: {GRAY_TEXT}; font-size: 10px; background: transparent; border: none;")
        text_col.addWidget(sub_txt)

        layout.addLayout(text_col, stretch=1)
        return row

    def _format_relative(self, iso_str) -> str:
        if not iso_str:
            return "?"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%d/%m/%Y à %H:%M")
        except (ValueError, TypeError):
            return str(iso_str)