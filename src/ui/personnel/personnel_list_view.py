"""
========================================================================
DRENAET-RH — PersonnelListView (liste + recherche + filtres + actions)
========================================================================
Vue principale de gestion des agents.

Composants :
- Barre de recherche full-text (matricule, nom, prénoms)
- Filtres : structure, sexe, statut
- Bouton "+ Nouvel agent" (ouvre PersonnelFormDialog en mode CREATE)
- Table paginée (50 agents par page par défaut)
- Actions par ligne : Voir / Modifier / Supprimer
- Pagination bas de page

Rafraîchissement automatique après chaque action.
"""

from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)

from src.services.personnel_service import (
    PersonnelService, AgentIntrouvableError,
)
from src.services.structure_service import StructureService
from src.services.auth_service import UserSession

from src.ui.personnel.personnel_form_dialog import PersonnelFormDialog
from src.ui.personnel.personnel_detail_dialog import PersonnelDetailDialog


PAGE_SIZE = 50

STATUT_COLORS = {
    "Actif":     "#10B981",
    "Inactif":   "#94A3B8",
    "En congé":  "#F59E0B",
    "Muté":      "#3B82F6",
    "Retraité":  "#8B5CF6",
}


class PersonnelListView(QWidget):
    """Vue liste paginée des agents."""

    # Signal émis quand on doit rafraîchir depuis l'extérieur
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._total_agents = 0
        self._search_query = ""
        self._filters = {}
        self._build_ui()
        self._load_structures_filter()
        self.refresh()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        # === Titre + bouton Nouveau ===
        layout.addWidget(self._build_header_bar())

        # === Barre de recherche + filtres ===
        layout.addWidget(self._build_filters_bar())

        # === Table ===
        self.table = self._build_table()
        layout.addWidget(self.table, stretch=1)

        # === Pagination ===
        layout.addWidget(self._build_pagination_bar())

    # ====================================================================
    def _build_header_bar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title = QLabel("Liste des agents")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;"
        )
        title_col.addWidget(title)

        self.total_lbl = QLabel("Chargement...")
        self.total_lbl.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        title_col.addWidget(self.total_lbl)
        layout.addLayout(title_col)

        layout.addStretch()

        # Bouton refresh
        refresh_btn = QPushButton()
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#4338CA"))
        refresh_btn.setToolTip("Rafraîchir")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #EEF2FF; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        # Bouton "Nouvel agent"
        new_btn = QPushButton("  Nouvel agent")
        new_btn.setIcon(qta.icon("fa5s.user-plus", color="#FFFFFF"))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setFixedHeight(40)
        new_btn.setMinimumWidth(180)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        new_btn.clicked.connect(self._on_new_agent)
        layout.addWidget(new_btn)

        return w

    # ====================================================================
    def _build_filters_bar(self) -> QFrame:
        """Barre de recherche + filtres."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        frame.setFixedHeight(60)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        # Icône recherche
        search_icon = QLabel()
        search_icon.setPixmap(qta.icon("fa5s.search", color="#64748B").pixmap(QSize(16, 16)))
        search_icon.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(search_icon)

        # Champ recherche
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par matricule, nom ou prénoms...")
        self.search_input.setMinimumHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                font-size: 12px;
                color: #1E1B4B;
                padding: 4px;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_change)
        layout.addWidget(self.search_input, stretch=1)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #E2E8F0; border: none;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # Filtre Structure
        self.structure_filter = self._make_filter_combo()
        self.structure_filter.setMinimumWidth(160)
        self.structure_filter.addItem("Toutes structures", userData=None)
        self.structure_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.structure_filter)

        # Filtre Sexe
        self.sexe_filter = self._make_filter_combo()
        self.sexe_filter.setMinimumWidth(120)
        self.sexe_filter.addItem("Tous sexes", userData=None)
        self.sexe_filter.addItem("Homme (M)", userData="M")
        self.sexe_filter.addItem("Femme (F)", userData="F")
        self.sexe_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.sexe_filter)

        # Filtre Statut
        self.statut_filter = self._make_filter_combo()
        self.statut_filter.setMinimumWidth(140)
        self.statut_filter.addItem("Tous statuts", userData=None)
        for s in ["Actif", "Inactif", "En congé", "Muté", "Retraité"]:
            self.statut_filter.addItem(s, userData=s)
        self.statut_filter.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self.statut_filter)

        return frame

    def _make_filter_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(36)
        combo.setStyleSheet("""
            QComboBox {
                background-color: #F1F5F9;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                color: #1E1B4B;
            }
            QComboBox:focus { border-color: #4338CA; }
        """)
        return combo

    def _load_structures_filter(self):
        """Charge les structures dans le combo de filtre."""
        try:
            structures = StructureService.list_all()
            for s in structures:
                self.structure_filter.addItem(s["nom"], userData=s["id"])
        except Exception:
            pass

    # ====================================================================
    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Matricule", "Nom complet", "Sexe", "Emploi",
            "Structure", "Statut", "Actions",
        ])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #F1F5F9;
                font-size: 12px;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected {
                background-color: #EEF2FF;
                color: #1E1B4B;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #1E1B4B;
                padding: 10px;
                border: none;
                border-right: 1px solid #E2E8F0;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(False)
        table.setColumnWidth(0, 110)
        table.setColumnWidth(1, 220)
        table.setColumnWidth(2, 60)
        table.setColumnWidth(3, 180)
        table.setColumnWidth(4, 200)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 130)
        table.verticalHeader().setDefaultSectionSize(44)
        return table

    # ====================================================================
    def _build_pagination_bar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Info page
        self.page_info = QLabel("Page 1 sur 1")
        self.page_info.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self.page_info)

        layout.addStretch()

        # Bouton précédent
        self.prev_btn = QPushButton("  Précédent")
        self.prev_btn.setIcon(qta.icon("fa5s.chevron-left", color="#64748B"))
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setFixedHeight(36)
        self.prev_btn.setStyleSheet(self._pagination_btn_style())
        self.prev_btn.clicked.connect(self._on_prev_page)
        layout.addWidget(self.prev_btn)

        # Bouton suivant
        self.next_btn = QPushButton("Suivant  ")
        self.next_btn.setIcon(qta.icon("fa5s.chevron-right", color="#64748B"))
        self.next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setFixedHeight(36)
        self.next_btn.setStyleSheet(self._pagination_btn_style())
        self.next_btn.clicked.connect(self._on_next_page)
        layout.addWidget(self.next_btn)

        return w

    def _pagination_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #FFFFFF;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover:enabled { background-color: #F1F5F9; }
            QPushButton:disabled { color: #CBD5E1; }
        """

    # ====================================================================
    # DATA & REFRESH
    # ====================================================================
    def refresh(self):
        """Recharge la liste depuis la BD."""
        try:
            agents, total = PersonnelService.search(
                query=self._search_query,
                filters=self._filters,
                page=self._current_page,
                page_size=PAGE_SIZE,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement échoué :\n{e}")
            return

        self._total_agents = total

        # Message de total
        if total == 0:
            self.total_lbl.setText("Aucun agent trouvé")
        elif total == 1:
            self.total_lbl.setText("1 agent au total")
        else:
            self.total_lbl.setText(f"{total} agents au total")

        # Remplir la table
        self._fill_table(agents)

        # Mettre à jour la pagination
        self._update_pagination()

    def _fill_table(self, agents: list):
        self.table.setRowCount(len(agents))

        if not agents:
            self.table.setRowCount(1)
            item = QTableWidgetItem("  Aucun agent ne correspond à ces critères.")
            item.setForeground(QColor("#94A3B8"))
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 7)
            return

        for row_idx, agent in enumerate(agents):
            # Matricule (gras)
            mat_item = QTableWidgetItem(agent.get("matricule") or "")
            font = mat_item.font()
            font.setBold(True)
            mat_item.setFont(font)
            self.table.setItem(row_idx, 0, mat_item)

            # Nom complet
            self.table.setItem(row_idx, 1, QTableWidgetItem(agent.get("nom_complet") or ""))

            # Sexe
            sexe_item = QTableWidgetItem(agent.get("sexe") or "?")
            sexe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if agent.get("sexe") == "M":
                sexe_item.setForeground(QColor("#3B82F6"))
            elif agent.get("sexe") == "F":
                sexe_item.setForeground(QColor("#EC4899"))
            self.table.setItem(row_idx, 2, sexe_item)

            # Emploi
            self.table.setItem(row_idx, 3, QTableWidgetItem(agent.get("emploi") or ""))

            # Structure
            self.table.setItem(row_idx, 4, QTableWidgetItem(agent.get("structure_nom") or ""))

            # Statut (badge coloré)
            statut = agent.get("statut") or "?"
            statut_item = QTableWidgetItem(statut)
            statut_item.setForeground(QColor(STATUT_COLORS.get(statut, "#64748B")))
            statut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 5, statut_item)

            # Actions
            actions_widget = self._build_actions_cell(agent["id"])
            self.table.setCellWidget(row_idx, 6, actions_widget)

    def _build_actions_cell(self, agent_id: int) -> QWidget:
        """3 boutons : Voir / Modifier / Supprimer."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Voir
        view_btn = QPushButton()
        view_btn.setIcon(qta.icon("fa5s.eye", color="#4338CA"))
        view_btn.setToolTip("Voir la fiche")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setFixedSize(30, 30)
        view_btn.setStyleSheet(self._icon_btn_style("#EEF2FF"))
        view_btn.clicked.connect(lambda: self._on_view_agent(agent_id))
        layout.addWidget(view_btn)

        # Modifier
        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#3B82F6"))
        edit_btn.setToolTip("Modifier")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet(self._icon_btn_style("#DBEAFE"))
        edit_btn.clicked.connect(lambda: self._on_edit_agent(agent_id))
        layout.addWidget(edit_btn)

        # Supprimer
        del_btn = QPushButton()
        del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#DC2626"))
        del_btn.setToolTip("Supprimer")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet(self._icon_btn_style("#FEE2E2"))
        del_btn.clicked.connect(lambda: self._on_delete_agent(agent_id))
        layout.addWidget(del_btn)

        return w

    def _icon_btn_style(self, hover_bg: str) -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """

    def _update_pagination(self):
        """Met à jour l'état des boutons pagination + info page."""
        total_pages = max(1, (self._total_agents + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_info.setText(
            f"Page {self._current_page} sur {total_pages} • "
            f"{self._total_agents} agent(s) au total"
        )
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < total_pages)

    # ====================================================================
    # HANDLERS
    # ====================================================================
    def _on_search_change(self, text: str):
        """Rafraîchit la recherche."""
        self._search_query = text.strip()
        self._current_page = 1
        self.refresh()

    def _on_filter_change(self):
        """Rafraîchit les filtres."""
        self._filters = {}
        struct_id = self.structure_filter.currentData()
        if struct_id is not None:
            self._filters["structure_id"] = struct_id
        sexe = self.sexe_filter.currentData()
        if sexe is not None:
            self._filters["sexe"] = sexe
        statut = self.statut_filter.currentData()
        if statut is not None:
            self._filters["statut"] = statut

        self._current_page = 1
        self.refresh()

    def _on_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.refresh()

    def _on_next_page(self):
        total_pages = max(1, (self._total_agents + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._current_page < total_pages:
            self._current_page += 1
            self.refresh()

    def _on_new_agent(self):
        """Ouvre la popup de création."""
        dialog = PersonnelFormDialog(agent_id=None, parent=self)
        if dialog.exec():
            self.refresh()
            self.data_changed.emit()

    def _on_view_agent(self, agent_id: int):
        """Ouvre la popup de fiche."""
        dialog = PersonnelDetailDialog(agent_id=agent_id, parent=self)
        dialog.edit_requested.connect(self._on_edit_agent)
        dialog.exec()

    def _on_edit_agent(self, agent_id: int):
        """Ouvre la popup de modification."""
        dialog = PersonnelFormDialog(agent_id=agent_id, parent=self)
        if dialog.exec():
            self.refresh()
            self.data_changed.emit()

    def _on_delete_agent(self, agent_id: int):
        """Confirme puis supprime un agent."""
        # Récupérer les infos pour affichage
        try:
            agent = PersonnelService.get_by_id(agent_id)
            if not agent:
                QMessageBox.warning(self, "Introuvable", "Cet agent n'existe plus.")
                self.refresh()
                return
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return

        reply = QMessageBox.warning(
            self,
            "Confirmer la suppression",
            f"<b>Voulez-vous vraiment supprimer cet agent ?</b><br/><br/>"
            f"<b>Matricule :</b> {agent['matricule']}<br/>"
            f"<b>Nom :</b> {agent['nom_complet']}<br/><br/>"
            f"<span style='color:#DC2626;'>⚠️ Cette action est IRRÉVERSIBLE.</span><br/>"
            f"L'agent sera définitivement supprimé de la base de données. "
            f"Toutefois, l'historique de ses modifications sera conservé.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Exécuter la suppression
        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"
            user_role = session.role if session.is_authenticated else None

            PersonnelService.delete(
                agent_id=agent_id,
                user_login=user_login,
                user_role=user_role,
                commentaire="Suppression via UI",
            )
            QMessageBox.information(
                self, "Suppression",
                f"L'agent {agent['matricule']} a été supprimé.",
            )
            self.refresh()
            self.data_changed.emit()

        except AgentIntrouvableError as e:
            QMessageBox.warning(self, "Introuvable", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Suppression échouée :\n{e}")