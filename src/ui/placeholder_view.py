"""
========================================================================
DRENAET-RH — Page Placeholder (module à venir)
========================================================================
Page affichée pour les modules pas encore implémentés.
Au fur et à mesure des sprints, on remplace ces placeholders par les
vraies vues.
"""

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize


class PlaceholderView(QWidget):
    """Page placeholder pour les modules futurs."""

    def __init__(
        self,
        title: str = "Module à venir",
        subtitle: str = "Ce module sera disponible dans un prochain sprint.",
        icon_name: str = "fa5s.cog",
        sprint: str = "",
        parent=None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Carte centrale
        card = QFrame()
        card.setStyleSheet(
            "QFrame { "
            "  background-color: #FFFFFF; "
            "  border: 1px solid #E2E8F0; "
            "  border-radius: 12px; "
            "  padding: 50px; "
            "}"
        )
        card.setMaximumWidth(600)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(16)

        # Icône
        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon(icon_name, color="#7C3AED").pixmap(QSize(72, 72))
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        # Titre
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 22px; font-weight: bold; padding-top: 10px;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        # Sous-titre
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setStyleSheet(
            "color: #64748B; font-size: 12px;"
        )
        subtitle_lbl.setWordWrap(True)
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle_lbl)

        # Badge sprint
        if sprint:
            badge = QLabel(f"📅  {sprint}")
            badge.setStyleSheet(
                "background-color: #E0E7FF; color: #4338CA; "
                "font-size: 11px; font-weight: bold; padding: 6px 14px; "
                "border-radius: 6px;"
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_wrap = QVBoxLayout()
            badge_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_wrap.addWidget(badge)
            card_layout.addLayout(badge_wrap)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
