"""
========================================================================
DRENAET-RH — PersonnelView (conteneur avec onglets) — VERSION FINALE
========================================================================
Vue principale du module Personnel.

Présente les fonctionnalités sous forme d'onglets horizontaux :
- Liste des agents (VRAIE VUE - Sprint 4 Étape 4)
- Nouvel agent (bouton dans la liste)
- Importer Excel (Sprint 4 Étape 3)
- Historique imports (Sprint 4 Étape 3)

Changement par rapport à la version précédente :
- L'onglet 0 (Liste) affiche maintenant PersonnelListView
- L'onglet 1 (Nouveau) ouvre directement PersonnelFormDialog
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame,
)

from src.ui.personnel.personnel_list_view import PersonnelListView
from src.ui.personnel.personnel_form_dialog import PersonnelFormDialog
from src.ui.personnel.import_ui.import_wizard import ImportWizard
from src.ui.personnel.import_ui.history_view import ImportHistoryView


class PersonnelView(QWidget):
    """Vue conteneur du module Personnel avec système d'onglets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tab = 0
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Barre d'onglets ===
        self.tabs_bar = self._build_tabs_bar()
        layout.addWidget(self.tabs_bar)

        # === Stack des vues ===
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #F8FAFC;")

        # Onglet 0 : Liste des agents (VRAIE VUE Étape 4)
        self.list_view = PersonnelListView()
        self.stack.addWidget(self.list_view)

        # Onglet 1 : Nouvel agent (raccourci - ouvre popup + revient à la liste)
        self.new_view = self._build_new_agent_placeholder()
        self.stack.addWidget(self.new_view)

        # Onglet 2 : Import Excel (Étape 3)
        self.import_view = ImportWizard()
        self.stack.addWidget(self.import_view)

        # Onglet 3 : Historique imports (Étape 3)
        self.history_view = ImportHistoryView()
        self.stack.addWidget(self.history_view)

        layout.addWidget(self.stack, stretch=1)

        # Activer l'onglet 0 par défaut
        self._on_tab_click(0)

    # ====================================================================
    def _build_tabs_bar(self) -> QFrame:
        """Barre horizontale des onglets."""
        bar = QFrame()
        bar.setObjectName("personnelTabsBar")
        bar.setStyleSheet("""
            QFrame#personnelTabsBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        bar.setFixedHeight(52)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(4)

        # 4 onglets
        tabs = [
            ("fa5s.users", "Liste des agents"),
            ("fa5s.user-plus", "Nouvel agent"),
            ("fa5s.file-import", "Importer Excel"),
            ("fa5s.history", "Historique imports"),
        ]

        self._tab_buttons = []
        for i, (icon_name, label) in enumerate(tabs):
            btn = self._build_tab_button(i, icon_name, label)
            layout.addWidget(btn)
            self._tab_buttons.append(btn)

        layout.addStretch()
        return bar

    def _build_tab_button(self, index: int, icon_name: str, label: str) -> QPushButton:
        """Crée un bouton d'onglet."""
        btn = QPushButton(f"   {label}")
        btn.setObjectName("personnelTab")
        btn.setIcon(qta.icon(icon_name, color="#64748B"))
        btn.setIconSize(QSize(16, 16))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setFixedHeight(52)
        btn.setMinimumWidth(180)
        btn.setStyleSheet("""
            QPushButton#personnelTab {
                background-color: transparent;
                color: #64748B;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton#personnelTab:hover {
                color: #4338CA;
                background-color: #F1F5F9;
            }
            QPushButton#personnelTab:checked {
                color: #4338CA;
                border-bottom: 3px solid #4338CA;
                font-weight: bold;
                background-color: #FFFFFF;
            }
        """)
        btn.toggled.connect(
            lambda checked, i=icon_name, b=btn: b.setIcon(
                qta.icon(i, color="#4338CA" if checked else "#64748B")
            )
        )
        btn.clicked.connect(lambda: self._on_tab_click(index))
        return btn

    def _build_new_agent_placeholder(self) -> QWidget:
        """Écran de l'onglet Nouveau (invitation à cliquer)."""
        w = QWidget()
        w.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout(w)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Grande icône
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.user-plus", color="#10B981").pixmap(QSize(96, 96)))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # Titre
        title_lbl = QLabel("Ajouter un nouvel agent")
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 22px; font-weight: bold; background: transparent;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Message
        msg_lbl = QLabel(
            "Cliquez sur le bouton ci-dessous pour ouvrir le formulaire "
            "de création d'un nouvel agent."
        )
        msg_lbl.setStyleSheet(
            "color: #64748B; font-size: 13px; background: transparent;"
        )
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        # Bouton
        btn = QPushButton("  Créer un nouvel agent  ")
        btn.setIcon(qta.icon("fa5s.plus", color="#FFFFFF"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(48)
        btn.setMinimumWidth(250)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 24px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn.clicked.connect(self._on_open_new_dialog)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return w

    # ====================================================================
    def _on_tab_click(self, index: int):
        """Change l'onglet actif."""
        self._current_tab = index
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)

        # Actions spéciales par onglet
        if index == 0:
            # Liste : rafraîchir au cas où import récent
            self.list_view.refresh()
        elif index == 3:
            # Historique : rafraîchir
            self.history_view.refresh()

    def _on_open_new_dialog(self):
        """Ouvre la popup Nouveau et revient à la liste après."""
        dialog = PersonnelFormDialog(agent_id=None, parent=self)
        if dialog.exec():
            # Bascule automatiquement vers la Liste et rafraîchit
            self._on_tab_click(0)