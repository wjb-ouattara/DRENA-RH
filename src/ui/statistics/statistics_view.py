"""
========================================================================
DRENAET-RH — StatisticsView
========================================================================
Vue principale du module Statistiques.

Structure :
- 4 KPI cards en haut
- Graphique en barres : Personnel par structure
- Graphique en donut : Personnel par sexe
- Graphique en donut : Absences par type
- Graphique en courbe : Évolution mensuelle des absences (12 mois)
- Graphique en barres : Documents générés par type
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QMessageBox,
)

from src.services.statistics_service import StatisticsService
from src.ui.widgets.chart_widgets import (
    BarChartWidget, DonutChartWidget, LineChartWidget,
)


class StatisticsView(QWidget):
    """Vue principale du module Statistiques."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # ====================================================================
    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(20)

        # === Header ===
        layout.addWidget(self._build_header())

        # === KPI Cards ===
        self.kpi_grid = self._build_kpi_grid()
        layout.addWidget(self.kpi_grid)

        # === Ligne 1 : Personnel par structure (barres) + par sexe (donut) ===
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        self.structure_card, self.structure_chart = self._build_chart_card(
            "Personnel par structure", "fa5s.building", BarChartWidget,
        )
        row1.addWidget(self.structure_card, stretch=2)

        self.sexe_card, self.sexe_chart = self._build_chart_card(
            "Répartition par sexe", "fa5s.venus-mars", DonutChartWidget,
        )
        row1.addWidget(self.sexe_card, stretch=1)

        layout.addLayout(row1)

        # === Ligne 2 : Absences par type (donut) + Évolution mensuelle (courbe) ===
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        self.absence_type_card, self.absence_type_chart = self._build_chart_card(
            "Absences par type (année en cours)", "fa5s.calendar-times", DonutChartWidget,
        )
        row2.addWidget(self.absence_type_card, stretch=1)

        self.evolution_card, self.evolution_chart = self._build_chart_card(
            "Évolution des absences (12 derniers mois)", "fa5s.chart-line", LineChartWidget,
        )
        row2.addWidget(self.evolution_card, stretch=2)

        layout.addLayout(row2)

        # === Ligne 3 : Documents par type (barres, pleine largeur) ===
        self.documents_card, self.documents_chart = self._build_chart_card(
            "Documents générés par type", "fa5s.file-alt", BarChartWidget,
        )
        layout.addWidget(self.documents_card)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ====================================================================
    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title = QLabel("Statistiques")
        title.setStyleSheet("color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;")
        title_col.addWidget(title)

        subtitle = QLabel("Vue d'ensemble des ressources humaines de la DRENAET de Katiola")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        title_col.addWidget(subtitle)
        layout.addLayout(title_col)

        layout.addStretch()

        refresh_btn = QPushButton("  Actualiser")
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#4338CA"))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFixedHeight(38)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #4338CA;
                border: 1px solid #4338CA; border-radius: 6px;
                padding: 0 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #EEF2FF; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        return w

    # ====================================================================
    def _build_kpi_grid(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        self.kpi_cards = {}
        configs = [
            ("total_agents", "Agents actifs", "fa5s.users", "#4338CA"),
            ("ratio_femmes", "Taux de femmes", "fa5s.venus", "#EC4899"),
            ("absences_en_cours", "Absences en cours", "fa5s.calendar-times", "#F59E0B"),
            ("documents_ce_mois", "Documents ce mois", "fa5s.file-alt", "#10B981"),
        ]
        for i, (key, label, icon, color) in enumerate(configs):
            card = self._build_kpi_card(label, icon, color)
            grid.addWidget(card, 0, i)
            self.kpi_cards[key] = card

        return w

    def _build_kpi_card(self, label: str, icon_name: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: #FFFFFF; border: 1px solid #E2E8F0;
            border-left: 4px solid {color}; border-radius: 8px; }}
        """)
        card.setMinimumHeight(90)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(QSize(14, 14)))
        icon.setStyleSheet("background: transparent; border: none;")
        top.addWidget(icon)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        top.addWidget(lbl)
        top.addStretch()
        layout.addLayout(top)

        value = QLabel("—")
        value.setStyleSheet(f"color: {color}; font-size: 30px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(value)

        card.value_label = value
        return card

    # ====================================================================
    def _build_chart_card(self, title: str, icon_name: str, chart_cls) -> tuple:
        """Crée une carte contenant un graphique."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }
        """)
        frame.setMinimumHeight(300)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color="#4338CA").pixmap(QSize(16, 16)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; background: transparent; border: none;"
        )
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        chart = chart_cls()
        layout.addWidget(chart, stretch=1)

        return frame, chart

    # ====================================================================
    def refresh(self):
        """Recharge toutes les données et graphiques."""
        try:
            kpi = StatisticsService.get_kpi_summary()
            self.kpi_cards["total_agents"].value_label.setText(str(kpi["total_agents"]))
            self.kpi_cards["ratio_femmes"].value_label.setText(f"{kpi['ratio_femmes_pct']}%")
            self.kpi_cards["absences_en_cours"].value_label.setText(str(kpi["absences_en_cours"]))
            self.kpi_cards["documents_ce_mois"].value_label.setText(str(kpi["documents_ce_mois"]))

            self.structure_chart.set_data(StatisticsService.get_personnel_par_structure())
            self.sexe_chart.set_data(StatisticsService.get_personnel_par_sexe())
            self.absence_type_chart.set_data(StatisticsService.get_absences_par_type())
            self.evolution_chart.set_data(StatisticsService.get_absences_evolution_mensuelle())
            self.documents_chart.set_data(StatisticsService.get_documents_par_type())

        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Chargement des statistiques échoué :\n{e}")