"""
========================================================================
DRENAET-RH — PersonnelDetailDialog (fiche agent + audit trail)
========================================================================
Popup en lecture seule qui affiche :
- La fiche complète de l'agent (3 sections : Identité / Contact / Carrière)
- L'historique de toutes les modifications (audit trail)

Boutons :
- Modifier   → ouvre PersonnelFormDialog en mode EDIT
- Fermer     → ferme la popup

L'audit trail affiche pour chaque entrée :
- Date de l'action
- Type d'action (CREATE / UPDATE / DELETE)
- Utilisateur qui a fait l'action
- Source (MANUAL / IMPORT)
- Détail des changements (champ par champ pour UPDATE)
"""

from datetime import datetime
from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QMessageBox, QWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)

from src.services.personnel_service import PersonnelService
from src.services.audit_service import AuditService


ACTION_COLORS = {
    "CREATE": "#10B981",
    "UPDATE": "#3B82F6",
    "DELETE": "#DC2626",
}


class PersonnelDetailDialog(QDialog):
    """Popup fiche agent + audit trail."""

    # Signal émis si l'utilisateur clique sur "Modifier"
    edit_requested = pyqtSignal(int)  # agent_id

    def __init__(self, agent_id: int, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.agent_data: Optional[dict] = None

        self.setWindowTitle("Fiche agent")
        self.resize(820, 700)
        self.setStyleSheet("background-color: #F8FAFC;")
        self.setModal(True)

        self._build_ui()
        self._load_data()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # === Header ===
        self.header_frame = self._build_header()
        outer.addWidget(self.header_frame)

        # === Onglets : Fiche / Historique ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #F8FAFC;
                border: none;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #64748B;
                padding: 12px 24px;
                font-size: 12px;
                font-weight: bold;
                border-bottom: 3px solid transparent;
            }
            QTabBar::tab:hover {
                color: #4338CA;
                background-color: #F1F5F9;
            }
            QTabBar::tab:selected {
                color: #4338CA;
                border-bottom: 3px solid #4338CA;
                background-color: #FFFFFF;
            }
        """)

        # Onglet 1 : Fiche
        self.fiche_widget = self._build_fiche_tab()
        self.tabs.addTab(self.fiche_widget, qta.icon("fa5s.id-card", color="#64748B"), "  Fiche complète  ")

        # Onglet 2 : Historique
        self.history_widget = self._build_history_tab()
        self.tabs.addTab(self.history_widget, qta.icon("fa5s.history", color="#64748B"), "  Historique  ")

        outer.addWidget(self.tabs, stretch=1)

        # === Boutons ===
        outer.addWidget(self._build_buttons_bar())

    # ====================================================================
    def _build_header(self) -> QFrame:
        """En-tête coloré avec nom de l'agent."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338CA, stop:1 #7C3AED);
                border: none;
            }
        """)
        frame.setFixedHeight(96)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(20)

        # Avatar rond
        avatar = QLabel()
        avatar.setPixmap(qta.icon("fa5s.user-tie", color="#FFFFFF").pixmap(QSize(48, 48)))
        avatar.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(avatar)

        # Nom + infos
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.header_name = QLabel("Chargement...")
        self.header_name.setStyleSheet(
            "color: #FFFFFF; font-size: 20px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        text_layout.addWidget(self.header_name)

        self.header_subtitle = QLabel("")
        self.header_subtitle.setStyleSheet(
            "color: #E0E7FF; font-size: 12px; background: transparent; border: none;"
        )
        text_layout.addWidget(self.header_subtitle)

        layout.addLayout(text_layout, stretch=1)

        # Badge matricule
        self.matricule_badge = QLabel("")
        self.matricule_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 40);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.matricule_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        return frame

    # ====================================================================
    def _build_fiche_tab(self) -> QWidget:
        """Onglet 1 : fiche détaillée."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Sections
        self.identite_frame, self.identite_grid = self._build_info_section(
            "Identité", "fa5s.id-card"
        )
        layout.addWidget(self.identite_frame)

        self.contact_frame, self.contact_grid = self._build_info_section(
            "Contact", "fa5s.address-book"
        )
        layout.addWidget(self.contact_frame)

        self.carriere_frame, self.carriere_grid = self._build_info_section(
            "Carrière & Affectation", "fa5s.briefcase"
        )
        layout.addWidget(self.carriere_frame)

        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_info_section(self, title: str, icon_name: str) -> tuple:
        """Section d'infos (lecture seule)."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # Titre
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color="#4338CA").pixmap(QSize(16, 16)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Grille
        grid = QGridLayout()
        grid.setSpacing(10)
        layout.addLayout(grid)

        return frame, grid

    def _add_info_row(
        self,
        grid: QGridLayout,
        row: int,
        col: int,
        label: str,
        value: str,
        colspan: int = 1,
    ):
        """Ajoute une ligne (label / valeur) dans une grille."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            "color: #64748B; font-size: 10px; font-weight: bold; "
            "text-transform: uppercase; background: transparent; border: none;"
        )
        layout.addWidget(lbl)

        val = QLabel(value or "—")
        val.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; background: transparent; border: none;"
        )
        val.setWordWrap(True)
        layout.addWidget(val)

        grid.addWidget(w, row, col, 1, colspan)

    # ====================================================================
    def _build_history_tab(self) -> QWidget:
        """Onglet 2 : historique / audit trail."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header + compteur
        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title = QLabel("Historique des modifications")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 14px; font-weight: bold; background: transparent;"
        )
        title_col.addWidget(title)

        subtitle = QLabel(
            "Chaque action effectuée sur cet agent est tracée ici (audit trail)."
        )
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 11px; background: transparent;"
        )
        title_col.addWidget(subtitle)
        header.addLayout(title_col)

        header.addStretch()

        self.history_count = QLabel("")
        self.history_count.setStyleSheet("""
            QLabel {
                background-color: #EEF2FF;
                color: #4338CA;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        header.addWidget(self.history_count, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(header)

        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Action", "Utilisateur", "Source", "Détail",
        ])
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #F1F5F9;
                font-size: 11px;
            }
            QTableWidget::item { padding: 6px; }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #1E1B4B;
                padding: 8px;
                border: none;
                border-right: 1px solid #E2E8F0;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setColumnWidth(0, 130)
        self.history_table.setColumnWidth(1, 90)
        self.history_table.setColumnWidth(2, 120)
        self.history_table.setColumnWidth(3, 90)
        layout.addWidget(self.history_table, stretch=1)

        return w

    # ====================================================================
    def _build_buttons_bar(self) -> QFrame:
        """Barre de boutons en bas."""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E2E8F0;
            }
        """)
        bar.setFixedHeight(64)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)

        close_btn = QPushButton("  Fermer")
        close_btn.setIcon(qta.icon("fa5s.times", color="#64748B"))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(40)
        close_btn.setMinimumWidth(140)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        layout.addStretch()

        edit_btn = QPushButton("  Modifier cet agent")
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#FFFFFF"))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedHeight(40)
        edit_btn.setMinimumWidth(200)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        edit_btn.clicked.connect(self._on_edit)
        layout.addWidget(edit_btn)

        return bar

    # ====================================================================
    def _load_data(self):
        """Charge les données de l'agent."""
        try:
            agent = PersonnelService.get_by_id(self.agent_id)
            if not agent:
                QMessageBox.critical(self, "Erreur", "Agent introuvable.")
                self.reject()
                return
            self.agent_data = agent
            self._fill_header(agent)
            self._fill_fiche(agent)
            self._fill_history(agent.get("matricule"))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement échoué :\n{e}")

    def _fill_header(self, agent: dict):
        """Remplit l'en-tête."""
        self.header_name.setText(agent.get("nom_complet") or "?")
        self.matricule_badge.setText(agent.get("matricule") or "—")

        # Sous-titre : fonction @ structure
        subtitle_parts = []
        if agent.get("fonction"):
            subtitle_parts.append(agent["fonction"])
        if agent.get("structure_nom"):
            subtitle_parts.append(agent["structure_nom"])
        elif agent.get("emploi"):
            subtitle_parts.append(agent["emploi"])
        self.header_subtitle.setText(" • ".join(subtitle_parts))

    def _fill_fiche(self, agent: dict):
        """Remplit les 3 sections de la fiche."""
        # Vider les grilles avant de remplir
        for grid in [self.identite_grid, self.contact_grid, self.carriere_grid]:
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Section IDENTITÉ
        self._add_info_row(self.identite_grid, 0, 0, "Matricule", agent.get("matricule"))
        self._add_info_row(self.identite_grid, 0, 1, "Sexe", agent.get("civilite") or agent.get("sexe"))
        self._add_info_row(self.identite_grid, 1, 0, "Nom", agent.get("nom"))
        self._add_info_row(self.identite_grid, 1, 1, "Prénoms", agent.get("prenoms"))
        self._add_info_row(self.identite_grid, 2, 0, "Date de naissance", self._format_date(agent.get("date_naissance")))
        self._add_info_row(self.identite_grid, 2, 1, "Lieu de naissance", agent.get("lieu_naissance"))
        self._add_info_row(self.identite_grid, 3, 0, "Situation matrimoniale", agent.get("situation_matrimoniale"), colspan=2)

        # Section CONTACT
        self._add_info_row(self.contact_grid, 0, 0, "Téléphone", agent.get("telephone"))
        self._add_info_row(self.contact_grid, 0, 1, "Email", agent.get("email"))
        self._add_info_row(self.contact_grid, 1, 0, "Résidence", agent.get("residence"), colspan=2)

        # Section CARRIÈRE
        self._add_info_row(self.carriere_grid, 0, 0, "Emploi", agent.get("emploi"))
        self._add_info_row(self.carriere_grid, 0, 1, "Grade", agent.get("grade"))
        self._add_info_row(self.carriere_grid, 1, 0, "Fonction", agent.get("fonction"), colspan=2)
        struct_txt = agent.get("structure_nom")
        if struct_txt and agent.get("structure_type"):
            struct_txt = f"{struct_txt} ({agent['structure_type']})"
        self._add_info_row(self.carriere_grid, 2, 0, "Structure", struct_txt, colspan=2)
        self._add_info_row(self.carriere_grid, 3, 0, "Date prise de service", self._format_date(agent.get("date_prise_service")))
        self._add_info_row(self.carriere_grid, 3, 1, "Date affectation", self._format_date(agent.get("date_affectation")))
        self._add_info_row(self.carriere_grid, 4, 0, "Statut", agent.get("statut"), colspan=2)

    def _format_date(self, iso_str: Optional[str]) -> str:
        if not iso_str:
            return None
        try:
            d = datetime.fromisoformat(iso_str)
            return d.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return iso_str

    def _fill_history(self, matricule: str):
        """Remplit la table d'historique."""
        try:
            history = AuditService.get_history_for_agent(matricule, limit=200)
        except Exception as e:
            QMessageBox.warning(self, "Historique", f"Erreur chargement historique : {e}")
            return

        self.history_count.setText(f"{len(history)} action(s)")
        self.history_table.setRowCount(len(history))

        if not history:
            self.history_table.setRowCount(1)
            item = QTableWidgetItem("  Aucun historique disponible.")
            item.setForeground(QColor("#94A3B8"))
            self.history_table.setItem(0, 0, item)
            self.history_table.setSpan(0, 0, 1, 5)
            return

        for row_idx, entry in enumerate(history):
            # Date
            self.history_table.setItem(
                row_idx, 0, QTableWidgetItem(self._format_datetime(entry.get("date_action")))
            )

            # Action (coloré)
            action = entry.get("action", "?")
            action_item = QTableWidgetItem(action)
            action_item.setForeground(QColor(ACTION_COLORS.get(action, "#64748B")))
            self.history_table.setItem(row_idx, 1, action_item)

            # Utilisateur
            user_txt = entry.get("utilisateur_login") or "?"
            if entry.get("utilisateur_role"):
                user_txt += f" ({entry['utilisateur_role']})"
            self.history_table.setItem(row_idx, 2, QTableWidgetItem(user_txt))

            # Source
            source = entry.get("source") or "MANUAL"
            src_item = QTableWidgetItem(source)
            if source == "IMPORT":
                src_item.setForeground(QColor("#F59E0B"))
            self.history_table.setItem(row_idx, 3, src_item)

            # Détail
            detail = self._extract_detail(entry)
            self.history_table.setItem(row_idx, 4, QTableWidgetItem(detail))

    def _format_datetime(self, iso_str: Optional[str]) -> str:
        if not iso_str:
            return "?"
        try:
            d = datetime.fromisoformat(iso_str)
            return d.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return iso_str

    def _extract_detail(self, entry: dict) -> str:
        """Extrait un résumé texte du changement."""
        changements = entry.get("changements") or {}
        action = entry.get("action")

        if action == "CREATE":
            return "Création de l'agent"

        if action == "DELETE":
            return "Suppression de l'agent"

        if action == "UPDATE" and "changements" in changements:
            fields = list(changements["changements"].keys())
            if len(fields) <= 3:
                return f"Champs modifiés : {', '.join(fields)}"
            return f"{len(fields)} champs modifiés : {', '.join(fields[:3])}..."

        return entry.get("commentaire") or ""

    # ====================================================================
    def _on_edit(self):
        """Émet le signal pour ouvrir la popup d'édition."""
        self.edit_requested.emit(self.agent_id)
        self.accept()