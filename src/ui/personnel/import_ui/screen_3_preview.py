"""
========================================================================
DRENAET-RH — Écran 3 : Rapport de simulation (dry-run)
========================================================================
Affiche le résultat de la simulation :
- 4 gros compteurs (à créer / à modifier / à ignorer / erreurs)
- Tableau détaillé ligne par ligne
- Filtres par type d'action
- Boutons "Retour" / "CONFIRMER L'IMPORT"

C'est l'écran CRITIQUE : l'utilisateur voit exactement ce qui va se passer
avant de valider.
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QScrollArea,
    QMessageBox, QHeaderView, QGridLayout, QAbstractItemView,
)


# Configuration des couleurs par action
ACTION_STYLES = {
    "CREATE":         {"color": "#10B981", "label": "À CRÉER",       "icon": "fa5s.plus-circle"},
    "UPDATE":         {"color": "#3B82F6", "label": "À MODIFIER",    "icon": "fa5s.edit"},
    "SKIP_EXISTS":    {"color": "#94A3B8", "label": "IGNORÉ",        "icon": "fa5s.minus-circle"},
    "SKIP_NOT_FOUND": {"color": "#94A3B8", "label": "NON TROUVÉ",    "icon": "fa5s.question-circle"},
    "SKIP_NO_CHANGE": {"color": "#94A3B8", "label": "AUCUN CHGMT",   "icon": "fa5s.equals"},
    "ERROR":          {"color": "#DC2626", "label": "ERREUR",        "icon": "fa5s.exclamation-triangle"},
}


class Screen3Preview(QWidget):
    """Écran 3 : rapport de simulation."""

    back_requested = pyqtSignal()
    confirm_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_report = None
        self._current_filter = "ALL"
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # === Titre ===
        title = QLabel("Étape 3 : Rapport de simulation")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Voici ce qui se passera lors de l'import réel. "
            "Aucune donnée n'a encore été écrite dans la base."
        )
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        layout.addWidget(subtitle)

        # === Bandeau d'infos globales ===
        self.info_frame = self._build_info_frame()
        layout.addWidget(self.info_frame)

        # === 4 grosses cartes compteurs ===
        self.stats_grid = self._build_stats_grid()
        layout.addWidget(self.stats_grid)

        # === Filtres + tableau des détails ===
        layout.addWidget(self._build_filters_bar())
        layout.addWidget(self._build_details_table(), stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # === Barre de boutons FIXE en bas ===
        outer.addWidget(self._build_buttons_bar())

    # ====================================================================
    def _build_info_frame(self) -> QFrame:
        """Bandeau récap (fichier, feuille, stratégie, durée)."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(30)

        self.info_labels = {}
        info_items = [
            ("fa5s.file-excel", "Fichier"),
            ("fa5s.table", "Feuille"),
            ("fa5s.random", "Stratégie"),
            ("fa5s.clock", "Durée analyse"),
        ]

        for icon_name, label in info_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(6)
            icon = QLabel()
            icon.setPixmap(qta.icon(icon_name, color="#64748B").pixmap(QSize(14, 14)))
            icon.setStyleSheet("background: transparent; border: none;")
            item_layout.addWidget(icon)
            lbl = QLabel(f"<b>{label} :</b> ...")
            lbl.setStyleSheet(
                "color: #1E1B4B; font-size: 11px; background: transparent; border: none;"
            )
            item_layout.addWidget(lbl)
            self.info_labels[label] = lbl
            layout.addLayout(item_layout)

        layout.addStretch()
        return frame

    def _build_stats_grid(self) -> QWidget:
        """4 cartes de compteurs (à créer / modifier / ignorer / erreurs)."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        self.stat_cards = {}
        cards_config = [
            ("CREATE",       "À CRÉER",     "fa5s.plus-circle",         "#10B981"),
            ("UPDATE",       "À MODIFIER",  "fa5s.edit",                "#3B82F6"),
            ("SKIP",         "À IGNORER",   "fa5s.minus-circle",        "#94A3B8"),
            ("ERROR",        "ERREURS",     "fa5s.exclamation-triangle","#DC2626"),
        ]

        for i, (key, label, icon, color) in enumerate(cards_config):
            card = self._build_stat_card(label, icon, color)
            grid.addWidget(card, 0, i)
            self.stat_cards[key] = card

        return w

    def _build_stat_card(self, label: str, icon_name: str, color: str) -> QFrame:
        """Une carte de compteur."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        # Ligne icône + label
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(QSize(14, 14)))
        icon.setStyleSheet("background: transparent; border: none;")
        top_layout.addWidget(icon)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        top_layout.addWidget(lbl)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Grand nombre
        value = QLabel("0")
        value.setStyleSheet(
            f"color: {color}; font-size: 36px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value)

        card.value_label = value
        return card

    def _build_filters_bar(self) -> QWidget:
        """Barre de filtres au-dessus du tableau."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Détails ligne par ligne :")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)
        layout.addSpacing(20)

        # Boutons filtres
        self._filter_buttons = {}
        filters = [
            ("ALL",    "Tout",       "#4338CA"),
            ("CREATE", "À créer",    "#10B981"),
            ("UPDATE", "À modifier", "#3B82F6"),
            ("SKIP",   "Ignorés",    "#94A3B8"),
            ("ERROR",  "Erreurs",    "#DC2626"),
        ]
        for value, label, color in filters:
            btn = self._build_filter_button(value, label, color)
            self._filter_buttons[value] = btn
            layout.addWidget(btn)

        layout.addStretch()
        return w

    def _build_filter_button(self, value: str, label: str, color: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: 1px solid {color};
                border-radius: 15px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {color}22; }}
            QPushButton:checked {{ background-color: {color}; color: #FFFFFF; }}
        """)
        btn.clicked.connect(lambda: self._apply_filter(value))
        if value == "ALL":
            btn.setChecked(True)
        return btn

    def _build_details_table(self) -> QTableWidget:
        """Tableau des décisions ligne par ligne."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Ligne", "Matricule", "Action", "Détail", "Changements",
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
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 70)
        table.setColumnWidth(1, 130)
        table.setColumnWidth(2, 130)
        table.setColumnWidth(3, 260)
        table.setMinimumHeight(280)

        self.details_table = table
        return table

    def _build_buttons_bar(self) -> QFrame:
        """Barre fixe en bas avec les boutons Retour / Confirmer."""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E2E8F0;
            }
        """)
        bar.setFixedHeight(72)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 14, 40, 14)

        back_btn = QPushButton("  Retour")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#64748B"))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedHeight(44)
        back_btn.setMinimumWidth(140)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn)

        layout.addStretch()

        self.confirm_btn = QPushButton("  CONFIRMER L'IMPORT  ")
        self.confirm_btn.setIcon(qta.icon("fa5s.check", color="#FFFFFF"))
        self.confirm_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setFixedHeight(44)
        self.confirm_btn.setMinimumWidth(260)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(self.confirm_btn)

        return bar

    # ====================================================================
    def load_report(self, preview_report):
        """Charge un rapport et rafraîchit toute la vue."""
        self.preview_report = preview_report

        # Infos globales
        info = preview_report.file_info or {}
        self.info_labels["Fichier"].setText(f"<b>Fichier :</b> {info.get('nom_fichier', '?')}")
        self.info_labels["Feuille"].setText(f"<b>Feuille :</b> {preview_report.sheet_name}")
        self.info_labels["Stratégie"].setText(f"<b>Stratégie :</b> {preview_report.strategy}")
        self.info_labels["Durée analyse"].setText(f"<b>Durée :</b> {preview_report.duree_ms} ms")

        # Compteurs
        self.stat_cards["CREATE"].value_label.setText(str(preview_report.nb_a_creer))
        self.stat_cards["UPDATE"].value_label.setText(str(preview_report.nb_a_modifier))
        self.stat_cards["SKIP"].value_label.setText(str(preview_report.nb_a_ignorer))
        self.stat_cards["ERROR"].value_label.setText(str(preview_report.nb_erreurs))

        # Décider si le bouton Confirmer est actif
        if preview_report.missing_required_fields:
            self.confirm_btn.setEnabled(False)
            self.confirm_btn.setText("  Champs obligatoires manquants  ")
        elif preview_report.nb_a_creer + preview_report.nb_a_modifier == 0:
            self.confirm_btn.setEnabled(False)
            self.confirm_btn.setText("  Rien à importer  ")
        else:
            self.confirm_btn.setEnabled(True)
            self.confirm_btn.setText("  CONFIRMER L'IMPORT  ")

        # Remplir le tableau
        self._refresh_table()

    def _refresh_table(self):
        """Remplit le tableau avec les décisions filtrées."""
        if not self.preview_report:
            return

        decisions = self.preview_report.decisions or []
        errors = self.preview_report.errors or []

        # Filtrer selon _current_filter
        rows_to_show = []
        for d in decisions:
            action = d.get("action", "")
            if self._current_filter == "ALL":
                rows_to_show.append(("decision", d))
            elif self._current_filter == "SKIP" and action.startswith("SKIP"):
                rows_to_show.append(("decision", d))
            elif action == self._current_filter:
                rows_to_show.append(("decision", d))

        if self._current_filter in ("ALL", "ERROR"):
            for e in errors:
                rows_to_show.append(("error", e))

        # Remplir la table
        self.details_table.setRowCount(len(rows_to_show))

        for row_idx, (kind, item) in enumerate(rows_to_show):
            if kind == "decision":
                self._fill_decision_row(row_idx, item)
            else:
                self._fill_error_row(row_idx, item)

    def _fill_decision_row(self, row_idx: int, d: dict):
        action = d.get("action", "?")
        style = ACTION_STYLES.get(action, {"color": "#64748B", "label": action})

        # Ligne
        self.details_table.setItem(
            row_idx, 0, QTableWidgetItem(str(d.get("row_number", "")))
        )
        # Matricule
        self.details_table.setItem(
            row_idx, 1, QTableWidgetItem(d.get("matricule", "") or "—")
        )
        # Action (avec couleur)
        action_item = QTableWidgetItem(style["label"])
        from PyQt6.QtGui import QColor
        action_item.setForeground(QColor(style["color"]))
        self.details_table.setItem(row_idx, 2, action_item)
        # Détail
        self.details_table.setItem(
            row_idx, 3, QTableWidgetItem(d.get("reason", "") or "")
        )
        # Changements (résumé)
        changes = d.get("changes", {})
        if changes:
            summary = ", ".join(changes.keys())
        else:
            summary = ""
        self.details_table.setItem(row_idx, 4, QTableWidgetItem(summary))

    def _fill_error_row(self, row_idx: int, e: dict):
        style = ACTION_STYLES["ERROR"]

        self.details_table.setItem(
            row_idx, 0, QTableWidgetItem(str(e.get("row_number", "")))
        )
        self.details_table.setItem(
            row_idx, 1, QTableWidgetItem(e.get("matricule", "") or "—")
        )
        action_item = QTableWidgetItem(style["label"])
        from PyQt6.QtGui import QColor
        action_item.setForeground(QColor(style["color"]))
        self.details_table.setItem(row_idx, 2, action_item)
        raisons = e.get("raisons", [])
        detail = "; ".join(raisons) if isinstance(raisons, list) else str(raisons)
        self.details_table.setItem(row_idx, 3, QTableWidgetItem(detail))
        self.details_table.setItem(row_idx, 4, QTableWidgetItem(""))

    def _apply_filter(self, value: str):
        """Applique un filtre et rafraîchit."""
        self._current_filter = value
        # Décocher les autres boutons
        for v, btn in self._filter_buttons.items():
            btn.setChecked(v == value)
        self._refresh_table()

    def _on_confirm(self):
        """Demande confirmation avant d'exécuter."""
        if not self.preview_report:
            return

        report = self.preview_report
        strategy = report.strategy

        # Message spécial pour REPLACE (destructif)
        if strategy == "REPLACE":
            reply = QMessageBox.warning(
                self,
                "⚠️ Attention - Stratégie destructive",
                f"<b>Vous avez choisi la stratégie REPLACE.</b><br/><br/>"
                f"Cette opération va SUPPRIMER les agents existants et les "
                f"recréer à partir du fichier Excel. "
                f"Toutes les modifications manuelles seront PERDUES.<br/><br/>"
                f"Voulez-vous vraiment continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        else:
            reply = QMessageBox.question(
                self,
                "Confirmer l'import",
                f"<b>Confirmez-vous l'import ?</b><br/><br/>"
                f"• <b>{report.nb_a_creer}</b> agent(s) seront créés<br/>"
                f"• <b>{report.nb_a_modifier}</b> agent(s) seront modifiés<br/>"
                f"• <b>{report.nb_a_ignorer}</b> ligne(s) seront ignorées<br/><br/>"
                f"Cette action sera enregistrée dans l'historique.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

        if reply == QMessageBox.StandardButton.Yes:
            self.confirm_requested.emit()