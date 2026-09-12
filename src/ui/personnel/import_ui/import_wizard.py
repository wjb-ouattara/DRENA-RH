"""
========================================================================
DRENAET-RH — ImportWizard
========================================================================
Wizard qui orchestre les 4 écrans du processus d'import Excel.

État partagé entre les écrans :
- file_path : chemin du fichier sélectionné (écran 1)
- file_info : métadonnées du fichier
- sheet_name : feuille sélectionnée (écran 2)
- strategy : stratégie choisie (écran 2)
- preview_report : rapport du dry-run (écran 3)
- execution_report : rapport final (écran 4)
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QFrame, QPushButton,
)

from src.ui.personnel.import_ui.screen_1_select_file import Screen1SelectFile
from src.ui.personnel.import_ui.screen_2_configure import Screen2Configure
from src.ui.personnel.import_ui.screen_3_preview import Screen3Preview
from src.ui.personnel.import_ui.screen_4_result import Screen4Result


class ImportWizard(QWidget):
    """Wizard d'import Excel en 4 écrans."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # État partagé entre les écrans
        self.state = {
            "file_path": None,
            "file_info": None,
            "sheet_name": None,
            "strategy": "UPSERT",
            "preview_report": None,
            "execution_report": None,
        }

        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Progress steps (bandeau en haut) ===
        self.steps_bar = self._build_steps_bar()
        layout.addWidget(self.steps_bar)

        # === Stack des 4 écrans ===
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #F8FAFC;")

        # Écran 1 : Sélection fichier
        self.screen1 = Screen1SelectFile()
        self.screen1.next_requested.connect(self._go_to_screen_2)
        self.stack.addWidget(self.screen1)

        # Écran 2 : Configuration
        self.screen2 = Screen2Configure()
        self.screen2.back_requested.connect(self._go_to_screen_1)
        self.screen2.analyze_requested.connect(self._go_to_screen_3)
        self.stack.addWidget(self.screen2)

        # Écran 3 : Preview
        self.screen3 = Screen3Preview()
        self.screen3.back_requested.connect(self._go_to_screen_2)
        self.screen3.confirm_requested.connect(self._go_to_screen_4)
        self.stack.addWidget(self.screen3)

        # Écran 4 : Résultat
        self.screen4 = Screen4Result()
        self.screen4.restart_requested.connect(self._go_to_screen_1)
        self.stack.addWidget(self.screen4)

        layout.addWidget(self.stack, stretch=1)

    # ====================================================================
    def _build_steps_bar(self) -> QFrame:
        """Bandeau des étapes en haut (visualise la progression)."""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        bar.setFixedHeight(70)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(30, 12, 30, 12)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._step_widgets = []
        steps = [
            ("fa5s.file-upload", "Sélection"),
            ("fa5s.cogs", "Configuration"),
            ("fa5s.search", "Aperçu"),
            ("fa5s.check-circle", "Résultat"),
        ]

        for i, (icon, label) in enumerate(steps):
            # Widget d'étape (cercle + label)
            step_widget = self._build_step_widget(i + 1, icon, label)
            self._step_widgets.append(step_widget)
            layout.addWidget(step_widget)

            # Séparateur entre étapes
            if i < len(steps) - 1:
                sep = QLabel("——")
                sep.setStyleSheet(
                    "color: #CBD5E1; font-size: 14px; font-weight: bold; "
                    "padding: 0 10px; background: transparent;"
                )
                layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)

        return bar

    def _build_step_widget(self, num: int, icon_name: str, label: str) -> QWidget:
        """Widget d'une étape (cercle numéroté + label)."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.step_num = num  # pour référence ensuite

        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Cercle
        circle = QLabel(str(num))
        circle.setFixedSize(32, 32)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setObjectName(f"stepCircle{num}")
        circle.setStyleSheet("""
            QLabel {
                background-color: #E2E8F0;
                color: #64748B;
                font-size: 13px;
                font-weight: bold;
                border-radius: 16px;
            }
        """)
        layout.addWidget(circle)
        w.circle = circle

        # Label
        text = QLabel(label)
        text.setStyleSheet(
            "color: #64748B; font-size: 12px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(text)
        w.text = text

        return w

    def _update_steps_state(self, active_step: int):
        """Colore les étapes selon la progression."""
        for w in self._step_widgets:
            if w.step_num < active_step:
                # Étapes passées : vert avec check
                w.circle.setText("✓")
                w.circle.setStyleSheet("""
                    QLabel {
                        background-color: #10B981;
                        color: #FFFFFF;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 16px;
                    }
                """)
                w.text.setStyleSheet(
                    "color: #10B981; font-size: 12px; font-weight: bold; background: transparent;"
                )
            elif w.step_num == active_step:
                # Étape courante : indigo
                w.circle.setText(str(w.step_num))
                w.circle.setStyleSheet("""
                    QLabel {
                        background-color: #4338CA;
                        color: #FFFFFF;
                        font-size: 13px;
                        font-weight: bold;
                        border-radius: 16px;
                    }
                """)
                w.text.setStyleSheet(
                    "color: #4338CA; font-size: 12px; font-weight: bold; background: transparent;"
                )
            else:
                # Étapes futures : gris
                w.circle.setText(str(w.step_num))
                w.circle.setStyleSheet("""
                    QLabel {
                        background-color: #E2E8F0;
                        color: #64748B;
                        font-size: 13px;
                        font-weight: bold;
                        border-radius: 16px;
                    }
                """)
                w.text.setStyleSheet(
                    "color: #64748B; font-size: 12px; font-weight: 500; background: transparent;"
                )

    # ====================================================================
    # NAVIGATION ENTRE ÉCRANS
    # ====================================================================
    def _go_to_screen_1(self):
        """Retour à l'écran de sélection."""
        # Reset partiel de l'état (garder le fichier si l'utilisateur revient)
        self.stack.setCurrentIndex(0)
        self._update_steps_state(1)

    def _go_to_screen_2(self, file_path: str, file_info: dict):
        """Passage à l'écran de configuration."""
        self.state["file_path"] = file_path
        self.state["file_info"] = file_info
        self.screen2.load_file(file_path, file_info)
        self.stack.setCurrentIndex(1)
        self._update_steps_state(2)

    def _go_to_screen_3(self, sheet_name: str, strategy: str, preview_report):
        """Passage à l'écran de prévisualisation."""
        self.state["sheet_name"] = sheet_name
        self.state["strategy"] = strategy
        self.state["preview_report"] = preview_report
        self.screen3.load_report(preview_report)
        self.stack.setCurrentIndex(2)
        self._update_steps_state(3)

    def _go_to_screen_4(self):
        """Passage à l'écran de résultat (lance l'exécution)."""
        self.stack.setCurrentIndex(3)
        self._update_steps_state(4)
        # Lancer l'exécution réelle
        self.screen4.execute(self.state["preview_report"])