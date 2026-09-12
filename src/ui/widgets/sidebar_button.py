"""
========================================================================
DRENAET-RH — SidebarButton (VERSION 3 — "Light & Ember")
========================================================================
Sidebar claire et aérée : fond blanc, item actif traité comme une pill
orange DOUCE (fond teinté clair, texte orange foncé lisible) — pas de
panneau sombre. Inspiré des dashboards clairs premium (Stripe, Notion,
Linear en mode clair).

API PUBLIQUE INCHANGÉE (drop-in replacement) :
    SidebarButton(icon_name, label, page_id=None, badge_count=0)
    .set_compact(bool)
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QPushButton, QLabel


# ========================================================================
# PALETTE — "Light & Ember"
# ========================================================================
HOVER_BG = "#F5F5F4"          # stone-100
TEXT_MUTED = "#78716C"        # stone-500 (icônes/texte inactifs)
TEXT_HOVER = "#292524"        # stone-800
ORANGE_PRIMARY = "#F97316"
ORANGE_SOFT_BG = "#FFEDD5"    # orange-100 (fond pill actif)
ORANGE_TEXT_ACTIVE = "#C2410C"  # orange-700 (texte pill actif, lisible)


class SidebarButton(QPushButton):
    """Bouton de menu de la sidebar — style pill orange douce sur fond clair."""

    def __init__(
        self,
        icon_name: str,
        label: str,
        page_id: str = None,
        badge_count: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.icon_name = icon_name
        self.label = label
        self.page_id = page_id or ""
        self._compact = False
        self._badge_count = badge_count

        self.setObjectName("sidebarBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._icon_normal = qta.icon(icon_name, color=TEXT_MUTED)
        self._icon_active = qta.icon(icon_name, color=ORANGE_TEXT_ACTIVE)

        self._apply_mode()
        self._apply_style()
        self.toggled.connect(self._on_toggled)

        self._badge_label = None
        if self._badge_count > 0:
            self._build_badge()

    # ====================================================================
    def set_compact(self, compact: bool):
        if self._compact == compact:
            return
        self._compact = compact
        self._apply_mode()
        if self._badge_label:
            self._position_badge()

    def _apply_mode(self):
        self.setIcon(self._icon_normal if not self.isChecked() else self._icon_active)
        self.setIconSize(QSize(18, 18))

        if self._compact:
            self.setText("")
            self.setToolTip(self.label)
            self.setFixedHeight(44)
        else:
            self.setText(f"   {self.label}")
            self.setToolTip("")
            self.setFixedHeight(44)

    def _on_toggled(self, checked: bool):
        self.setIcon(self._icon_active if checked else self._icon_normal)

    # ====================================================================
    def _apply_style(self):
        """Pill flottante avec marge, fond orange doux à l'état actif."""
        self.setStyleSheet(f"""
            QPushButton#sidebarBtn {{
                background-color: transparent;
                color: {TEXT_MUTED};
                border: none;
                border-radius: 10px;
                text-align: left;
                padding: 0 14px;
                margin: 2px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#sidebarBtn:hover {{
                background-color: {HOVER_BG};
                color: {TEXT_HOVER};
            }}
            QPushButton#sidebarBtn:checked {{
                background-color: {ORANGE_SOFT_BG};
                color: {ORANGE_TEXT_ACTIVE};
                font-weight: bold;
            }}
        """)

    # ====================================================================
    # BADGE (bonus optionnel)
    # ====================================================================
    def _build_badge(self):
        self._badge_label = QLabel(str(self._badge_count), self)
        self._badge_label.setFixedSize(18, 18)
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge_label.setStyleSheet(f"""
            QLabel {{
                background-color: {ORANGE_PRIMARY};
                color: #FFFFFF;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
                border: 2px solid #FFFFFF;
            }}
        """)
        self._position_badge()
        self._badge_label.show()

    def _position_badge(self):
        if not self._badge_label:
            return
        if self._compact:
            self._badge_label.move(self.width() - 16, 2)
        else:
            self._badge_label.move(self.width() - 30, 6)

    def set_badge_count(self, count: int):
        self._badge_count = count
        if count <= 0:
            if self._badge_label:
                self._badge_label.hide()
            return
        if not self._badge_label:
            self._build_badge()
        else:
            self._badge_label.setText(str(count))
            self._badge_label.show()
            self._position_badge()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._badge_label:
            self._position_badge()