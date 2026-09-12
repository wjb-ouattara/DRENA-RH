"""
========================================================================
DRENAET-RH — Widget IconLabel
========================================================================
Widget composite qui affiche une icône Font Awesome à côté d'un texte.
Utilisé partout à la place des émojis dans les formulaires.

Utilisation :
    from src.ui.widgets.icon_label import IconLabel

    # Remplace : QLabel("🔍 Matricule :")
    # Par :
    label = IconLabel("fa5s.search", "Matricule :", icon_color="#4338CA")

Fonctionne aussi comme label dans un QFormLayout :
    form.addRow(IconLabel("fa5s.calendar-alt", "Date :"), self.date_input)
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel


class IconLabel(QWidget):
    """Widget composite : icône Font Awesome + texte à droite."""

    def __init__(
        self,
        icon_name: str,
        text: str,
        icon_color: str = "#4338CA",
        icon_size: int = 14,
        text_style: str = None,
        parent=None,
    ):
        """
        Args:
            icon_name: nom de l'icône Font Awesome (ex: "fa5s.search")
            text: le texte à afficher à droite de l'icône
            icon_color: couleur hex de l'icône (défaut : indigo)
            icon_size: taille de l'icône en pixels
            text_style: CSS custom pour le QLabel du texte (sinon défaut)
            parent: widget parent
        """
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Icône (via qtawesome)
        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon(icon_name, color=icon_color).pixmap(QSize(icon_size, icon_size))
        )
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setFixedWidth(icon_size + 2)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Texte
        text_label = QLabel(text)
        default_style = (
            "color: #1E1B4B; font-size: 12px; font-weight: bold; background: transparent;"
        )
        text_label.setStyleSheet(text_style if text_style else default_style)
        layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()


class StepLabel(QWidget):
    """Widget étape numérotée : cercle avec chiffre + titre + sous-titre.

    Remplace les émojis "1️⃣ 2️⃣ 3️⃣" par un vrai cercle numéroté
    à la façon des formulaires modernes.
    """

    def __init__(
        self,
        num: int,
        title: str,
        subtitle: str = None,
        color: str = "#4338CA",
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Cercle numéroté
        num_label = QLabel(str(num))
        num_label.setFixedSize(32, 32)
        num_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border-radius: 16px;
            }}
        """)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(num_label, alignment=Qt.AlignmentFlag.AlignTop)

        # Titre + sous-titre
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QHBoxLayout(text_widget) if not subtitle else None
        if subtitle:
            from PyQt6.QtWidgets import QVBoxLayout
            text_layout = QVBoxLayout(text_widget)
            text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 14px; font-weight: bold; background: transparent;"
        )
        text_layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(
                "color: #64748B; font-size: 11px; background: transparent;"
            )
            sub_lbl.setWordWrap(True)
            text_layout.addWidget(sub_lbl)

        layout.addWidget(text_widget, stretch=1)