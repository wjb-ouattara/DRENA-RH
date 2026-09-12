"""
========================================================================
DRENAET-RH — Écran 2 : Configuration de l'import
========================================================================
Permet à l'utilisateur de :
- Choisir la feuille du fichier Excel
- Choisir la stratégie de merge (UPSERT / INSERT_ONLY / UPDATE_ONLY / REPLACE)
- Voir un aperçu du mapping automatique des colonnes
- Lancer l'analyse (dry-run)
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QScrollArea, QMessageBox, QApplication,
)

from src.services.import_pipeline import (
    ExcelReader, ColumnMapper, MergeStrategy, ImportService,
)


class Screen2Configure(QWidget):
    """Écran 2 : configuration de l'import."""

    back_requested = pyqtSignal()
    analyze_requested = pyqtSignal(str, str, object)  # sheet, strategy, preview_report

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: str = None
        self.file_info: dict = None
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # === Titre ===
        title = QLabel("Étape 2 : Configuration de l'import")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Sélectionnez la feuille à traiter et la stratégie d'import à appliquer."
        )
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        layout.addWidget(subtitle)

        # === Bloc 1 : Feuille ===
        layout.addWidget(self._build_sheet_selector())

        # === Bloc 2 : Stratégie ===
        layout.addWidget(self._build_strategy_selector())

        # === Bloc 3 : Aperçu mapping colonnes ===
        self.mapping_frame = self._build_mapping_preview()
        layout.addWidget(self.mapping_frame)

        # === Boutons ===
        buttons_layout = QHBoxLayout()

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
        buttons_layout.addWidget(back_btn)

        buttons_layout.addStretch()

        self.analyze_btn = QPushButton("  Analyser (simulation)  ")
        self.analyze_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.setFixedHeight(44)
        self.analyze_btn.setMinimumWidth(220)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover { background-color: #3730A3; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze)
        buttons_layout.addWidget(self.analyze_btn)

        layout.addLayout(buttons_layout)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ====================================================================
    def _build_sheet_selector(self) -> QFrame:
        """Section : choix de la feuille."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Titre section
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.table", color="#4338CA").pixmap(QSize(18, 18)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title = QLabel("Feuille à importer")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Combo box
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumHeight(38)
        self.sheet_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QComboBox:focus { border-color: #4338CA; }
        """)
        layout.addWidget(self.sheet_combo)

        return frame

    def _build_strategy_selector(self) -> QFrame:
        """Section : choix de la stratégie."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Titre section
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.random", color="#4338CA").pixmap(QSize(18, 18)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title = QLabel("Stratégie d'import")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Combo box avec les 4 stratégies
        self.strategy_combo = QComboBox()
        self.strategy_combo.setMinimumHeight(38)
        self.strategy_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QComboBox:focus { border-color: #4338CA; }
        """)

        strategies = MergeStrategy.get_available_strategies()
        for s in strategies:
            self.strategy_combo.addItem(s["label"], userData=s)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_change)

        layout.addWidget(self.strategy_combo)

        # Description de la stratégie sélectionnée
        self.strategy_desc = QLabel()
        self.strategy_desc.setStyleSheet("""
            QLabel {
                background-color: #EEF2FF;
                color: #1E1B4B;
                border: 1px solid #C7D2FE;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 11px;
            }
        """)
        self.strategy_desc.setWordWrap(True)
        layout.addWidget(self.strategy_desc)

        self._on_strategy_change(0)  # afficher la desc de la 1ère
        return frame

    def _build_mapping_preview(self) -> QFrame:
        """Section : aperçu du mapping automatique."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Titre section
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.columns", color="#4338CA").pixmap(QSize(18, 18)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title = QLabel("Aperçu du mapping des colonnes")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Contenu (rempli dynamiquement)
        self.mapping_content = QLabel(
            "Sélectionnez une feuille pour voir le mapping des colonnes."
        )
        self.mapping_content.setStyleSheet(
            "color: #64748B; font-size: 12px; font-style: italic; "
            "background: transparent; border: none;"
        )
        self.mapping_content.setWordWrap(True)
        layout.addWidget(self.mapping_content)

        return frame

    # ====================================================================
    def load_file(self, file_path: str, file_info: dict):
        """Charge un fichier (appelé par le wizard)."""
        self.file_path = file_path
        self.file_info = file_info

        # Remplir le combo des feuilles
        self.sheet_combo.clear()
        for sheet in file_info["feuilles"]:
            self.sheet_combo.addItem(sheet)

        # Rafraîchir le mapping preview
        self.sheet_combo.currentTextChanged.connect(self._refresh_mapping_preview)
        self._refresh_mapping_preview()

    def _refresh_mapping_preview(self):
        """Recalcule le mapping automatique et l'affiche."""
        sheet = self.sheet_combo.currentText()
        if not sheet or not self.file_path:
            return

        try:
            with ExcelReader(self.file_path) as reader:
                headers, _ = reader.read_sheet(sheet)

            mapper = ColumnMapper()
            result = mapper.auto_map(headers)

            # Construire le HTML de l'aperçu
            html = self._build_mapping_html(result, headers)
            self.mapping_content.setText(html)

        except Exception as e:
            self.mapping_content.setText(
                f"<span style='color:#DC2626;'>Erreur lors du mapping : {e}</span>"
            )

    def _build_mapping_html(self, result: dict, headers: list) -> str:
        """Construit un HTML récap du mapping."""
        mapping = result["mapping"]
        missing = result["missing_required_fields"]
        unmapped = result["unmapped_excel_columns"]

        lines = []

        # Champs mappés (obligatoires en priorité)
        obligatoires = ["matricule", "nom", "prenoms", "sexe", "emploi", "structure"]
        mapped_lines = []
        for champ in obligatoires:
            if champ in mapping:
                col = mapping[champ]
                if isinstance(col, str) and col.startswith("__SUBSTITUT__"):
                    col = f"(via {col.replace('__SUBSTITUT__', '')})"
                mapped_lines.append(
                    f"<span style='color:#10B981;'>&#10004;</span> "
                    f"<b>{champ}</b> &larr; <i>{col}</i>"
                )

        for champ, col in mapping.items():
            if champ in obligatoires:
                continue
            if isinstance(col, str) and col.startswith("__SUBSTITUT__"):
                continue
            mapped_lines.append(
                f"<span style='color:#10B981;'>&#10004;</span> "
                f"<b>{champ}</b> &larr; <i>{col}</i>"
            )

        if mapped_lines:
            lines.append(
                f"<b style='color:#10B981;'>Colonnes reconnues ({len(mapped_lines)}) :</b><br/>"
                + "<br/>".join(mapped_lines)
            )

        # Champs obligatoires manquants
        if missing:
            lines.append(
                "<br/><br/>"
                f"<b style='color:#DC2626;'>Champs obligatoires MANQUANTS ({len(missing)}) :</b><br/>"
                + " • ".join(f"<b>{c}</b>" for c in missing)
                + "<br/><i style='color:#64748B;'>L'analyse ne pourra pas continuer sans ces champs.</i>"
            )

        # Colonnes non reconnues
        if unmapped:
            lines.append(
                "<br/><br/>"
                f"<b style='color:#F59E0B;'>Colonnes non reconnues ({len(unmapped)}) :</b><br/>"
                + ", ".join(f"<i>{c}</i>" for c in unmapped)
                + "<br/><i style='color:#64748B;'>Ces colonnes seront ignorées.</i>"
            )

        return "".join(lines) or "<i>Aucun mapping détecté.</i>"

    # ====================================================================
    def _on_strategy_change(self, index: int):
        """Met à jour la description de la stratégie."""
        data = self.strategy_combo.itemData(index)
        if not data:
            return
        desc = data["description"]
        level = data["warning_level"]
        color = "#DC2626" if level == "danger" else "#4338CA"

        self.strategy_desc.setText(
            f"<span style='color:{color};'><b>{data['label']}</b></span><br/>{desc}"
        )

    # ====================================================================
    def _on_analyze(self):
        """Lance le dry-run et passe à l'écran 3."""
        if not self.file_path:
            return

        sheet = self.sheet_combo.currentText()
        strategy_data = self.strategy_combo.currentData()
        strategy = strategy_data["value"] if strategy_data else "UPSERT"

        # Feedback visuel : bouton désactivé + curseur d'attente
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("  Analyse en cours...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            report = ImportService.dry_run(
                file_path=self.file_path,
                sheet_name=sheet,
                strategy=strategy,
            )
            self.analyze_requested.emit(sheet, strategy, report)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur d'analyse",
                f"L'analyse a échoué :\n\n{e}",
            )
        finally:
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("  Analyser (simulation)  ")
            QApplication.restoreOverrideCursor()