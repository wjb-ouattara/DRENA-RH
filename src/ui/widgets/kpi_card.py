"""
========================================================================
DRENAET-RH — Widget : KPICard (Carte d'indicateur)
========================================================================
Affiche un KPI sous forme de carte moderne :
- Bandeau coloré en haut avec icône + label
- Grand nombre au centre
- Sous-titre descriptif en bas
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class KPICard(QFrame):
    """
    Carte d'indicateur (KPI Card) au style moderne.

    Usage :
        card = KPICard(
            icon="🏫",
            label="ÉTABLISSEMENTS",
            value="19",
            subtitle="Structures suivies",
            color="#4338CA",   # couleur du bandeau
        )
    """

    def __init__(
        self,
        icon: str = "📊",
        label: str = "INDICATEUR",
        value: str = "0",
        subtitle: str = "",
        color: str = "#4338CA",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self._color = color

        # Layout vertical : label / value / subtitle
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== Bandeau coloré (icon + label) =====
        self.label_widget = QLabel(f"  {icon}  {label}")
        self.label_widget.setObjectName("kpiLabel")
        self.label_widget.setStyleSheet(
            f"background-color: {color}; color: #FFFFFF; "
            f"font-size: 10px; font-weight: bold; "
            f"padding: 8px 14px; border-top-left-radius: 12px; "
            f"border-top-right-radius: 12px;"
        )
        layout.addWidget(self.label_widget)

        # ===== Grand nombre =====
        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("kpiValue")
        self.value_widget.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {color}; padding: 14px;"
        )
        self.value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_widget)

        # ===== Sous-titre =====
        self.subtitle_widget = QLabel(subtitle)
        self.subtitle_widget.setObjectName("kpiSubtitle")
        self.subtitle_widget.setStyleSheet(
            "color: #64748B; font-size: 10px; "
            "font-style: italic; padding: 4px 14px 14px 14px;"
        )
        self.subtitle_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_widget)

        # Style du frame englobant
        self.setStyleSheet(
            "QFrame#kpiCard { "
            "  background-color: #FFFFFF; "
            "  border: 1px solid #E2E8F0; "
            "  border-radius: 12px; "
            "}"
        )

        # Dimensions
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)

    # ================================================================
    def set_value(self, value: str):
        """Met à jour la valeur affichée."""
        self.value_widget.setText(str(value))

    def set_subtitle(self, subtitle: str):
        """Met à jour le sous-titre."""
        self.subtitle_widget.setText(subtitle)
