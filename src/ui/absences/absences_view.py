"""
========================================================================
DRENAET-RH — AbsencesView (vue principale du module)
========================================================================
Vue avec 2 onglets :
- Liste des absences (table paginée + filtres + actions)
- Quotas de congés (vue d'ensemble par agent, jauges visuelles)
"""

from datetime import datetime
from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QMessageBox, QStackedWidget,
    QScrollArea, QProgressBar, QGridLayout,
)

from src.services.absence_service import AbsenceService, AbsenceIntrouvableError
from src.services.structure_service import StructureService
from src.models.absence import TYPES_ABSENCE
from src.ui.absences.absence_form_dialog import AbsenceFormDialog


PAGE_SIZE = 50

STATUT_COLORS = {
    "Planifiée": "#3B82F6",
    "En cours":  "#F59E0B",
    "Terminée":  "#10B981",
    "Annulée":   "#94A3B8",
}

TYPE_COLORS = {
    "Congé annuel": "#10B981",
    "Congé maladie": "#DC2626",
    "Congé maternité": "#EC4899",
    "Autorisation d'absence": "#4338CA",
    "Mission": "#7C3AED",
    "Autre": "#64748B",
}


class AbsencesView(QWidget):
    """Vue principale du module Absences."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._total = 0
        self._filters = {}
        self._build_ui()
        self.refresh()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_tabs_bar())

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #F8FAFC;")

        self.list_page = self._build_list_page()
        self.stack.addWidget(self.list_page)

        self.quota_page = self._build_quota_page()
        self.stack.addWidget(self.quota_page)

        layout.addWidget(self.stack, stretch=1)

    def _build_tabs_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0; }
        """)
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(4)

        self._tab_buttons = []
        tabs = [("fa5s.calendar-alt", "Liste des absences"), ("fa5s.chart-pie", "Quotas de congés")]
        for i, (icon, label) in enumerate(tabs):
            btn = QPushButton(f"   {label}")
            btn.setIcon(qta.icon(icon, color="#64748B"))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(52)
            btn.setMinimumWidth(180)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #64748B; border: none;
                    border-bottom: 3px solid transparent; padding: 0 20px;
                    font-size: 13px; font-weight: 500; text-align: left;
                }
                QPushButton:hover { color: #4338CA; background-color: #F1F5F9; }
                QPushButton:checked {
                    color: #4338CA; border-bottom: 3px solid #4338CA;
                    font-weight: bold; background-color: #FFFFFF;
                }
            """)
            btn.toggled.connect(
                lambda checked, ic=icon, b=btn: b.setIcon(
                    qta.icon(ic, color="#4338CA" if checked else "#64748B")
                )
            )
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_click(idx))
            layout.addWidget(btn)
            self._tab_buttons.append(btn)

        layout.addStretch()
        self._tab_buttons[0].setChecked(True)
        return bar

    def _on_tab_click(self, index: int):
        for i, b in enumerate(self._tab_buttons):
            b.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.refresh()
        else:
            self._refresh_quota()

    # ====================================================================
    # PAGE 1 : LISTE
    # ====================================================================
    def _build_list_page(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Liste des absences")
        title.setStyleSheet("color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;")
        title_col.addWidget(title)
        self.total_lbl = QLabel("Chargement...")
        self.total_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        title_col.addWidget(self.total_lbl)
        header.addLayout(title_col)
        header.addStretch()

        new_btn = QPushButton("  Nouvelle absence")
        new_btn.setIcon(qta.icon("fa5s.plus", color="#FFFFFF"))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setFixedHeight(40)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 0 18px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #D97706; }
        """)
        new_btn.clicked.connect(self._on_new_absence)
        header.addWidget(new_btn)
        layout.addLayout(header)

        # Filtres
        layout.addWidget(self._build_filters_bar())

        # Table
        self.table = self._build_table()
        layout.addWidget(self.table, stretch=1)

        # Pagination
        layout.addWidget(self._build_pagination_bar())

        return w

    def _build_filters_bar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }")
        frame.setFixedHeight(56)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        lbl = QLabel("Filtrer :")
        lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold; background: transparent;")
        layout.addWidget(lbl)

        self.type_filter = self._make_combo()
        self.type_filter.addItem("Tous types", userData=None)
        for t in TYPES_ABSENCE:
            self.type_filter.addItem(t, userData=t)
        self.type_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.type_filter)

        self.statut_filter = self._make_combo()
        self.statut_filter.addItem("Tous statuts", userData=None)
        for s in ["Planifiée", "En cours", "Terminée", "Annulée"]:
            self.statut_filter.addItem(s, userData=s)
        self.statut_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.statut_filter)

        layout.addStretch()
        return frame

    def _make_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(34)
        combo.setMinimumWidth(150)
        combo.setStyleSheet("""
            QComboBox { background-color: #F1F5F9; border: 1px solid #E2E8F0;
            border-radius: 6px; padding: 4px 10px; font-size: 11px; }
        """)
        return combo

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Matricule", "Agent", "Type", "Période", "Jours ouvrés", "Statut", "Actions",
        ])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 8px; gridline-color: #F1F5F9; font-size: 12px; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section { background-color: #F1F5F9; color: #1E1B4B;
            padding: 10px; border: none; border-right: 1px solid #E2E8F0;
            font-weight: bold; font-size: 11px; }
        """)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 200)
        table.setColumnWidth(2, 160)
        table.setColumnWidth(3, 190)
        table.setColumnWidth(4, 100)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 100)
        table.verticalHeader().setDefaultSectionSize(42)
        return table

    def _build_pagination_bar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.page_info = QLabel("Page 1 sur 1")
        self.page_info.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(self.page_info)
        layout.addStretch()

        self.prev_btn = QPushButton("  Précédent")
        self.prev_btn.setIcon(qta.icon("fa5s.chevron-left", color="#64748B"))
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setStyleSheet(self._pagination_style())
        self.prev_btn.clicked.connect(self._on_prev_page)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Suivant  ")
        self.next_btn.setIcon(qta.icon("fa5s.chevron-right", color="#64748B"))
        self.next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setFixedHeight(34)
        self.next_btn.setStyleSheet(self._pagination_style())
        self.next_btn.clicked.connect(self._on_next_page)
        layout.addWidget(self.next_btn)
        return w

    def _pagination_style(self) -> str:
        return """
            QPushButton { background-color: #FFFFFF; color: #64748B;
            border: 1px solid #E2E8F0; border-radius: 6px; padding: 0 14px;
            font-size: 11px; font-weight: bold; }
            QPushButton:hover:enabled { background-color: #F1F5F9; }
            QPushButton:disabled { color: #CBD5E1; }
        """

    # ====================================================================
    def refresh(self):
        try:
            absences, total = AbsenceService.search(
                filters=self._filters, page=self._current_page, page_size=PAGE_SIZE,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement échoué :\n{e}")
            return

        self._total = total
        self.total_lbl.setText(f"{total} absence(s) au total" if total != 1 else "1 absence au total")
        self._fill_table(absences)
        self._update_pagination()

    def _fill_table(self, absences: list):
        self.table.setRowCount(len(absences))
        if not absences:
            self.table.setRowCount(1)
            item = QTableWidgetItem("  Aucune absence ne correspond à ces critères.")
            item.setForeground(QColor("#94A3B8"))
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 7)
            return

        for row, a in enumerate(absences):
            self.table.setItem(row, 0, QTableWidgetItem(a.get("matricule") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(a.get("nom_complet") or ""))

            type_item = QTableWidgetItem(a.get("type_absence") or "")
            type_item.setForeground(QColor(TYPE_COLORS.get(a.get("type_absence"), "#64748B")))
            self.table.setItem(row, 2, type_item)

            periode = f"{self._fmt(a['date_debut'])} → {self._fmt(a['date_fin'])}"
            self.table.setItem(row, 3, QTableWidgetItem(periode))

            jours_item = QTableWidgetItem(str(a.get("nb_jours_ouvres", "")))
            jours_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, jours_item)

            statut_item = QTableWidgetItem(a.get("statut") or "")
            statut_item.setForeground(QColor(STATUT_COLORS.get(a.get("statut"), "#64748B")))
            statut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, statut_item)

            self.table.setCellWidget(row, 6, self._build_actions_cell(a["id"]))

    def _fmt(self, iso_str) -> str:
        if not iso_str:
            return "?"
        try:
            return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(iso_str)

    def _build_actions_cell(self, absence_id: int) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#3B82F6"))
        edit_btn.setToolTip("Modifier")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #DBEAFE; }")
        edit_btn.clicked.connect(lambda: self._on_edit(absence_id))
        layout.addWidget(edit_btn)

        del_btn = QPushButton()
        del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#DC2626"))
        del_btn.setToolTip("Supprimer")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #FEE2E2; }")
        del_btn.clicked.connect(lambda: self._on_delete(absence_id))
        layout.addWidget(del_btn)

        return w

    def _update_pagination(self):
        total_pages = max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_info.setText(f"Page {self._current_page} sur {total_pages} • {self._total} absence(s)")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < total_pages)

    # ====================================================================
    def _on_filter_change(self):
        self._filters = {}
        t = self.type_filter.currentData()
        if t:
            self._filters["type_absence"] = t
        s = self.statut_filter.currentData()
        if s:
            self._filters["statut"] = s
        self._current_page = 1
        self.refresh()

    def _on_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.refresh()

    def _on_next_page(self):
        total_pages = max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._current_page < total_pages:
            self._current_page += 1
            self.refresh()

    def _on_new_absence(self):
        dialog = AbsenceFormDialog(parent=self)
        if dialog.exec():
            self.refresh()

    def _on_edit(self, absence_id: int):
        dialog = AbsenceFormDialog(absence_id=absence_id, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_delete(self, absence_id: int):
        absence = AbsenceService.get_by_id(absence_id)
        if not absence:
            self.refresh()
            return

        reply = QMessageBox.warning(
            self, "Confirmer la suppression",
            f"<b>Supprimer cette absence ?</b><br/><br/>"
            f"<b>Agent :</b> {absence['nom_complet']}<br/>"
            f"<b>Type :</b> {absence['type_absence']}<br/>"
            f"<b>Période :</b> {self._fmt(absence['date_debut'])} → {self._fmt(absence['date_fin'])}<br/><br/>"
            f"Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            AbsenceService.delete(absence_id)
            self.refresh()
        except AbsenceIntrouvableError as e:
            QMessageBox.warning(self, "Introuvable", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ====================================================================
    # PAGE 2 : QUOTAS
    # ====================================================================
    def _build_quota_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("Quotas de congés annuels")
        title.setStyleSheet("color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Quota légal : 30 jours ouvrés par an. "
            "Seuls les agents ayant pris des congés annuels apparaissent ci-dessous."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(subtitle)

        self.quota_container = QVBoxLayout()
        self.quota_container.setSpacing(10)
        layout.addLayout(self.quota_container)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _refresh_quota(self):
        while self.quota_container.count():
            item = self.quota_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            statuses = AbsenceService.get_quota_status_all_agents()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return

        if not statuses:
            empty = QLabel("Aucun congé annuel enregistré pour le moment.")
            empty.setStyleSheet("color: #94A3B8; font-size: 13px; font-style: italic; background: transparent;")
            self.quota_container.addWidget(empty)
            return

        for status in statuses:
            self.quota_container.addWidget(self._build_quota_card(status))

    def _build_quota_card(self, status: dict) -> QFrame:
        frame = QFrame()
        color = "#DC2626" if status["depassement"] else ("#F59E0B" if status["pourcentage"] > 80 else "#10B981")
        frame.setStyleSheet(f"""
            QFrame {{ background-color: #FFFFFF; border: 1px solid #E2E8F0;
            border-left: 4px solid {color}; border-radius: 8px; }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name = QLabel(status["nom_complet"])
        name.setStyleSheet("color: #1E1B4B; font-size: 13px; font-weight: bold; background: transparent;")
        name_col.addWidget(name)
        mat = QLabel(status["matricule"])
        mat.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        name_col.addWidget(mat)
        layout.addLayout(name_col)
        layout.addStretch()

        progress = QProgressBar()
        progress.setRange(0, status["quota_total"])
        progress.setValue(min(status["jours_pris"], status["quota_total"]))
        progress.setFixedWidth(200)
        progress.setFixedHeight(20)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{ background-color: #E2E8F0; border: none; border-radius: 10px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 10px; }}
        """)
        layout.addWidget(progress)

        stat_lbl = QLabel(f"{status['jours_pris']} / {status['quota_total']} jours ({status['pourcentage']}%)")
        stat_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent;")
        stat_lbl.setFixedWidth(160)
        layout.addWidget(stat_lbl)

        if status["depassement"]:
            warn_icon = QLabel()
            warn_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color="#DC2626").pixmap(QSize(18, 18)))
            warn_icon.setStyleSheet("background: transparent;")
            warn_icon.setToolTip("Quota dépassé")
            layout.addWidget(warn_icon)

        return frame