"""
========================================================================
DRENAET-RH — AuditLogView (consultation globale du journal d'audit)
========================================================================
Vue en lecture seule qui affiche TOUTES les actions tracées dans
l'application (créations, modifications, suppressions d'agents), tous
utilisateurs confondus.

Complète la vue "Historique" de la fiche d'un agent (qui ne montre que
l'historique d'UN agent) par une vue globale filtrable par :
- Type d'action (CREATE / UPDATE / DELETE)
- Source (MANUAL / IMPORT)
- Utilisateur
- Recherche texte (matricule / nom)
"""

from datetime import datetime

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)

from src.services.audit_service import AuditService


PAGE_SIZE = 50

ACTION_COLORS = {"CREATE": "#10B981", "UPDATE": "#3B82F6", "DELETE": "#DC2626"}
ACTION_ICONS = {"CREATE": "fa5s.plus-circle", "UPDATE": "fa5s.edit", "DELETE": "fa5s.trash-alt"}


class AuditLogView(QWidget):
    """Vue de consultation globale du journal d'audit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._total = 0
        self._query = ""
        self._action_filter = None
        self._source_filter = None
        self._build_ui()
        self.refresh()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_filters_bar())

        self.table = self._build_table()
        layout.addWidget(self.table, stretch=1)

        layout.addWidget(self._build_pagination_bar())

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title = QLabel("Journal d'audit")
        title.setStyleSheet("color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;")
        title_col.addWidget(title)

        self.total_lbl = QLabel("Chargement...")
        self.total_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        title_col.addWidget(self.total_lbl)
        layout.addLayout(title_col)

        layout.addStretch()

        refresh_btn = QPushButton("  Actualiser")
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#4338CA"))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFixedHeight(38)
        refresh_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #4338CA;
            border: 1px solid #4338CA; border-radius: 6px; padding: 0 16px;
            font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #EEF2FF; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        return w

    def _build_filters_bar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }")
        frame.setFixedHeight(58)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        search_icon = QLabel()
        search_icon.setPixmap(qta.icon("fa5s.search", color="#64748B").pixmap(QSize(14, 14)))
        search_icon.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par matricule ou nom d'agent...")
        self.search_input.setMinimumHeight(34)
        self.search_input.setStyleSheet(
            "QLineEdit { background: transparent; border: none; font-size: 12px; }"
        )
        self.search_input.textChanged.connect(self._on_filter_change)
        layout.addWidget(self.search_input, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #E2E8F0; border: none;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        self.action_filter = self._make_combo()
        self.action_filter.addItem("Toutes actions", userData=None)
        for a, label in [("CREATE", "Créations"), ("UPDATE", "Modifications"), ("DELETE", "Suppressions")]:
            self.action_filter.addItem(label, userData=a)
        self.action_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.action_filter)

        self.source_filter = self._make_combo()
        self.source_filter.addItem("Toutes sources", userData=None)
        self.source_filter.addItem("Manuel", userData="MANUAL")
        self.source_filter.addItem("Import Excel", userData="IMPORT")
        self.source_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.source_filter)

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
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Date", "Action", "Matricule", "Agent", "Utilisateur", "Source",
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
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 150)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 110)
        table.setColumnWidth(3, 200)
        table.setColumnWidth(4, 130)
        table.verticalHeader().setDefaultSectionSize(40)
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
        self.prev_btn.clicked.connect(self._on_prev)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Suivant  ")
        self.next_btn.setIcon(qta.icon("fa5s.chevron-right", color="#64748B"))
        self.next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setFixedHeight(34)
        self.next_btn.setStyleSheet(self._pagination_style())
        self.next_btn.clicked.connect(self._on_next)
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
            entries, total = AuditService.search(
                query=self._query,
                action=self._action_filter,
                source=self._source_filter,
                page=self._current_page,
                page_size=PAGE_SIZE,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement échoué :\n{e}")
            return

        self._total = total
        self.total_lbl.setText(f"{total} action(s) enregistrée(s)" if total != 1 else "1 action enregistrée")
        self._fill_table(entries)
        self._update_pagination()

    def _fill_table(self, entries: list):
        self.table.setRowCount(len(entries))
        if not entries:
            self.table.setRowCount(1)
            item = QTableWidgetItem("  Aucune action ne correspond à ces critères.")
            item.setForeground(QColor("#94A3B8"))
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 6)
            return

        for row, e in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(self._fmt_datetime(e.get("date_action"))))

            action = e.get("action", "?")
            action_item = QTableWidgetItem(f"  {action}")
            action_item.setForeground(QColor(ACTION_COLORS.get(action, "#64748B")))
            action_item.setIcon(qta.icon(ACTION_ICONS.get(action, "fa5s.circle"), color=ACTION_COLORS.get(action, "#64748B")))
            self.table.setItem(row, 1, action_item)

            self.table.setItem(row, 2, QTableWidgetItem(e.get("personnel_matricule") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(e.get("personnel_nom_complet") or ""))

            user_txt = e.get("utilisateur_login") or "?"
            if e.get("utilisateur_role"):
                user_txt += f" ({e['utilisateur_role']})"
            self.table.setItem(row, 4, QTableWidgetItem(user_txt))

            source = e.get("source") or "MANUAL"
            src_item = QTableWidgetItem(source)
            if source == "IMPORT":
                src_item.setForeground(QColor("#F59E0B"))
            self.table.setItem(row, 5, src_item)

    def _fmt_datetime(self, iso_str) -> str:
        if not iso_str:
            return "?"
        try:
            return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return str(iso_str)

    def _update_pagination(self):
        total_pages = max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_info.setText(f"Page {self._current_page} sur {total_pages} • {self._total} action(s)")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < total_pages)

    # ====================================================================
    def _on_filter_change(self):
        self._query = self.search_input.text().strip()
        self._action_filter = self.action_filter.currentData()
        self._source_filter = self.source_filter.currentData()
        self._current_page = 1
        self.refresh()

    def _on_prev(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.refresh()

    def _on_next(self):
        total_pages = max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._current_page < total_pages:
            self._current_page += 1
            self.refresh()