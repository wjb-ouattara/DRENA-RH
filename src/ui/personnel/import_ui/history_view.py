"""
========================================================================
DRENAET-RH — Vue Historique des imports
========================================================================
Affiche la liste des imports Excel passés (import_logs) avec :
- Une table paginée : date, fichier, stratégie, utilisateur, statut, compteurs
- Un bouton "Voir détails" par ligne → affiche les ImportDetail
- Filtres : par statut, par utilisateur
- Rafraîchissement automatique quand on arrive sur l'onglet
"""

from datetime import datetime

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialog, QScrollArea, QMessageBox,
)

from src.models import get_session
from src.models.import_log import ImportLog, ImportDetail


# Couleurs par statut
STATUT_STYLES = {
    "SUCCESS":     {"color": "#10B981", "label": "Réussi",   "icon": "fa5s.check-circle"},
    "PARTIAL":     {"color": "#F59E0B", "label": "Partiel",  "icon": "fa5s.exclamation-circle"},
    "FAILED":      {"color": "#DC2626", "label": "Échoué",   "icon": "fa5s.times-circle"},
    "IN_PROGRESS": {"color": "#3B82F6", "label": "En cours", "icon": "fa5s.spinner"},
    "DRY_RUN":     {"color": "#94A3B8", "label": "Simulation","icon": "fa5s.search"},
}


class ImportHistoryView(QWidget):
    """Vue de l'historique des imports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # === Titre + bouton rafraîchir ===
        header_layout = QHBoxLayout()

        title_col = QVBoxLayout()
        title = QLabel("Historique des imports Excel")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;"
        )
        title_col.addWidget(title)

        subtitle = QLabel(
            "Journal complet des imports effectués. Cliquez sur un import pour voir le détail."
        )
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        refresh_btn = QPushButton("  Rafraîchir")
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#4338CA"))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFixedHeight(38)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4338CA;
                border: 1px solid #4338CA;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #EEF2FF; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # === Table des imports ===
        self.table = self._build_table()
        layout.addWidget(self.table, stretch=1)

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Date", "Fichier", "Feuille", "Stratégie", "Utilisateur",
            "Statut", "Résultats", "Actions",
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
            QTableWidget::item { padding: 8px; }
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
        table.setColumnWidth(0, 140)
        table.setColumnWidth(1, 200)
        table.setColumnWidth(2, 120)
        table.setColumnWidth(3, 110)
        table.setColumnWidth(4, 110)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 200)
        table.setColumnWidth(7, 100)
        return table

    # ====================================================================
    def refresh(self):
        """Recharge la liste des imports depuis la BD."""
        try:
            with get_session() as db:
                imports = (
                    db.query(ImportLog)
                    .order_by(ImportLog.date_import.desc())
                    .limit(100)
                    .all()
                )
                # Détacher : convertir en dicts pour utiliser après la session
                imports_data = [i.to_dict() for i in imports]

            self._fill_table(imports_data)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Erreur",
                f"Impossible de charger l'historique :\n\n{e}",
            )

    def _fill_table(self, imports_data: list):
        """Remplit la table avec les imports."""
        self.table.setRowCount(len(imports_data))

        if not imports_data:
            self.table.setRowCount(1)
            no_data = QTableWidgetItem("  Aucun import enregistré pour l'instant.")
            no_data.setForeground(QColor("#64748B"))
            self.table.setItem(0, 0, no_data)
            self.table.setSpan(0, 0, 1, 8)
            return

        for row_idx, imp in enumerate(imports_data):
            # Date
            date_str = self._format_date(imp.get("date_import"))
            self.table.setItem(row_idx, 0, QTableWidgetItem(date_str))

            # Fichier
            self.table.setItem(row_idx, 1, QTableWidgetItem(imp.get("nom_fichier", "?")))

            # Feuille
            self.table.setItem(row_idx, 2, QTableWidgetItem(imp.get("feuille_excel") or "—"))

            # Stratégie
            self.table.setItem(row_idx, 3, QTableWidgetItem(imp.get("strategie", "?")))

            # Utilisateur
            self.table.setItem(row_idx, 4, QTableWidgetItem(imp.get("utilisateur_login", "?")))

            # Statut (coloré)
            statut = imp.get("statut", "?")
            style = STATUT_STYLES.get(statut, {"color": "#64748B", "label": statut})
            statut_item = QTableWidgetItem(style["label"])
            statut_item.setForeground(QColor(style["color"]))
            self.table.setItem(row_idx, 5, statut_item)

            # Résultats (résumé compteurs)
            resume = (
                f"{imp.get('nb_crees', 0)} créés • "
                f"{imp.get('nb_modifies', 0)} MAJ • "
                f"{imp.get('nb_erreurs', 0)} erreurs"
            )
            self.table.setItem(row_idx, 6, QTableWidgetItem(resume))

            # Bouton "Voir"
            btn = QPushButton("  Voir")
            btn.setIcon(qta.icon("fa5s.eye", color="#4338CA"))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #4338CA;
                    border: 1px solid #4338CA;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #EEF2FF; }
            """)
            import_id = imp.get("id")
            btn.clicked.connect(lambda checked, iid=import_id: self._show_details(iid))
            self.table.setCellWidget(row_idx, 7, btn)

    def _format_date(self, iso_str: str) -> str:
        if not iso_str:
            return "?"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return iso_str

    # ====================================================================
    def _show_details(self, import_log_id: int):
        """Affiche le détail d'un import dans une popup."""
        dialog = ImportDetailDialog(import_log_id, parent=self)
        dialog.exec()


# ========================================================================
# DIALOG DE DÉTAIL
# ========================================================================
class ImportDetailDialog(QDialog):
    """Popup qui affiche le détail ligne par ligne d'un import."""

    def __init__(self, import_log_id: int, parent=None):
        super().__init__(parent)
        self.import_log_id = import_log_id
        self.setWindowTitle(f"Détail import #{import_log_id}")
        self.resize(900, 600)
        self.setStyleSheet("background-color: #F8FAFC;")
        self._build_ui()
        self._load_details()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        self.title_lbl = QLabel(f"Détails de l'import #{self.import_log_id}")
        self.title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 18px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self.title_lbl)

        # Infos globales
        self.info_lbl = QLabel()
        self.info_lbl.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                color: #1E1B4B;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 14px;
                font-size: 12px;
            }
        """)
        self.info_lbl.setWordWrap(True)
        layout.addWidget(self.info_lbl)

        # Table des détails
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Ligne", "Matricule", "Action", "Détail"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
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
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 110)
        layout.addWidget(self.table, stretch=1)

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_details(self):
        """Charge les infos et détails depuis la BD."""
        try:
            with get_session() as db:
                import_log = db.query(ImportLog).filter_by(id=self.import_log_id).first()
                if not import_log:
                    self.info_lbl.setText("Import introuvable.")
                    return

                imp_data = import_log.to_dict()
                details = [d.to_dict() for d in import_log.details]

            # Infos
            statut_style = STATUT_STYLES.get(imp_data["statut"], {"color": "#64748B"})
            info_html = (
                f"<b>Fichier :</b> {imp_data['nom_fichier']}<br/>"
                f"<b>Date :</b> {imp_data['date_import']}<br/>"
                f"<b>Feuille :</b> {imp_data.get('feuille_excel', '—')}<br/>"
                f"<b>Stratégie :</b> {imp_data['strategie']}<br/>"
                f"<b>Utilisateur :</b> {imp_data['utilisateur_login']} "
                f"({imp_data.get('utilisateur_role', '?')})<br/>"
                f"<b>Statut :</b> <span style='color:{statut_style['color']};'>"
                f"<b>{imp_data['statut']}</b></span> "
                f"({imp_data['duree_ms']} ms)<br/>"
                f"<b>Résultats :</b> "
                f"{imp_data['nb_crees']} créés • "
                f"{imp_data['nb_modifies']} modifiés • "
                f"{imp_data['nb_ignores']} ignorés • "
                f"{imp_data['nb_erreurs']} erreurs"
            )
            self.info_lbl.setText(info_html)

            # Table des détails
            self.table.setRowCount(len(details))
            for row_idx, d in enumerate(details):
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(d["numero_ligne_excel"])))
                self.table.setItem(row_idx, 1, QTableWidgetItem(d.get("matricule") or "—"))

                action = d.get("action", "?")
                colors = {
                    "CREATED": "#10B981", "UPDATED": "#3B82F6",
                    "SKIPPED": "#94A3B8", "ERROR": "#DC2626",
                }
                action_item = QTableWidgetItem(action)
                action_item.setForeground(QColor(colors.get(action, "#64748B")))
                self.table.setItem(row_idx, 2, action_item)

                # Détail (message erreur ou changements)
                if d.get("message_erreur"):
                    detail = d["message_erreur"]
                else:
                    changements = d.get("changements", {})
                    if "changements" in changements:
                        detail = ", ".join(changements["changements"].keys())
                    elif "valeurs_initiales" in changements:
                        detail = "Création"
                    elif "raison" in changements:
                        detail = changements["raison"]
                    else:
                        detail = ""
                self.table.setItem(row_idx, 3, QTableWidgetItem(detail))

        except Exception as e:
            self.info_lbl.setText(f"Erreur : {e}")