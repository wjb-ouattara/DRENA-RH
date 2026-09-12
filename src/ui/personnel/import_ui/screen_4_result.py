"""
========================================================================
DRENAET-RH — Écran 4 : Résultat de l'import
========================================================================
Lance l'exécution RÉELLE en tâche de fond (thread) et affiche :
- Une barre de progression pendant l'exécution
- Un rapport final avec compteurs
- Un bouton "Nouvel import" pour recommencer

Utilise un QThread pour ne pas bloquer l'UI pendant l'import
(les gros fichiers peuvent prendre plusieurs secondes).
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QGridLayout,
)

from src.services.auth_service import UserSession
from src.services.import_pipeline import ImportService


# ========================================================================
# WORKER THREAD (exécute l'import en arrière-plan)
# ========================================================================
class ImportWorker(QThread):
    """Thread qui exécute l'import réel."""

    # Émis à la fin, avec le rapport d'exécution
    finished_with_report = pyqtSignal(object)
    # Émis en cas d'erreur critique
    error_occurred = pyqtSignal(str)

    def __init__(self, preview_report):
        super().__init__()
        self.preview_report = preview_report

    def run(self):
        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"
            user_role = session.role if session.is_authenticated else None

            report = ImportService.execute(
                preview_report=self.preview_report,
                user_login=user_login,
                user_role=user_role,
                commentaire="Import depuis l'interface utilisateur",
            )
            self.finished_with_report.emit(report)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ========================================================================
class Screen4Result(QWidget):
    """Écran 4 : exécution + résultat."""

    restart_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ImportWorker = None
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # === Zone d'exécution (visible pendant l'import) ===
        self.exec_frame = self._build_exec_frame()
        layout.addWidget(self.exec_frame)

        # === Zone de résultat (visible à la fin) ===
        self.result_frame = self._build_result_frame()
        self.result_frame.hide()
        layout.addWidget(self.result_frame)

        layout.addStretch()

    def _build_exec_frame(self) -> QFrame:
        """Bloc affiché pendant l'exécution."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icône loading
        self.exec_icon = QLabel()
        self.exec_icon.setPixmap(
            qta.icon("fa5s.spinner", color="#4338CA").pixmap(QSize(64, 64))
        )
        self.exec_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exec_icon.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.exec_icon)

        # Titre
        self.exec_title = QLabel("Import en cours...")
        self.exec_title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        self.exec_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.exec_title)

        # Message
        self.exec_msg = QLabel(
            "Merci de patienter pendant que les données sont écrites dans la base."
        )
        self.exec_msg.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent; border: none;"
        )
        self.exec_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exec_msg.setWordWrap(True)
        layout.addWidget(self.exec_msg)

        # Barre de progression (indéterminée)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # mode indéterminé
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #4338CA;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress)

        return frame

    def _build_result_frame(self) -> QFrame:
        """Bloc affiché à la fin (rapport final)."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header : gros check ou croix
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        self.result_icon = QLabel()
        self.result_icon.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(self.result_icon)

        header_text = QVBoxLayout()
        self.result_title = QLabel("Import terminé")
        self.result_title.setStyleSheet(
            "font-size: 22px; font-weight: bold; background: transparent; border: none;"
        )
        header_text.addWidget(self.result_title)

        self.result_subtitle = QLabel("")
        self.result_subtitle.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent; border: none;"
        )
        header_text.addWidget(self.result_subtitle)

        header_layout.addLayout(header_text)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Grille de compteurs
        self.result_stats_grid = self._build_result_stats()
        layout.addWidget(self.result_stats_grid)

        # Message d'audit
        self.audit_msg = QLabel()
        self.audit_msg.setStyleSheet("""
            QLabel {
                background-color: #EEF2FF;
                color: #4338CA;
                border: 1px solid #C7D2FE;
                border-radius: 6px;
                padding: 12px 14px;
                font-size: 12px;
            }
        """)
        self.audit_msg.setWordWrap(True)
        layout.addWidget(self.audit_msg)

        # Boutons
        buttons = QHBoxLayout()
        buttons.addStretch()

        restart_btn = QPushButton("  Nouvel import  ")
        restart_btn.setIcon(qta.icon("fa5s.plus", color="#FFFFFF"))
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.setFixedHeight(44)
        restart_btn.setMinimumWidth(200)
        restart_btn.setStyleSheet("""
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
        """)
        restart_btn.clicked.connect(self.restart_requested.emit)
        buttons.addWidget(restart_btn)

        layout.addLayout(buttons)
        return frame

    def _build_result_stats(self) -> QWidget:
        """Grille de compteurs du rapport final."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        self.result_stats = {}
        stats_config = [
            ("nb_crees",    "Agents créés",     "fa5s.plus-circle", "#10B981"),
            ("nb_modifies", "Agents modifiés",  "fa5s.edit",        "#3B82F6"),
            ("nb_ignores",  "Ignorés",          "fa5s.minus-circle","#94A3B8"),
            ("nb_erreurs",  "Erreurs",          "fa5s.exclamation-triangle", "#DC2626"),
        ]

        for i, (key, label, icon, color) in enumerate(stats_config):
            card = self._build_result_card(label, icon, color)
            grid.addWidget(card, 0, i)
            self.result_stats[key] = card

        return w

    def _build_result_card(self, label: str, icon_name: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        card.setMinimumHeight(80)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)

        # Label
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        layout.addWidget(lbl)

        # Nombre
        value = QLabel("0")
        value.setStyleSheet(
            f"color: {color}; font-size: 26px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        layout.addWidget(value)

        card.value_label = value
        return card

    # ====================================================================
    def execute(self, preview_report):
        """Lance l'exécution en arrière-plan."""
        # Reset UI
        self.exec_frame.show()
        self.result_frame.hide()

        # Lancer le worker
        self.worker = ImportWorker(preview_report)
        self.worker.finished_with_report.connect(self._on_import_finished)
        self.worker.error_occurred.connect(self._on_import_error)
        self.worker.start()

    def _on_import_finished(self, report):
        """Import terminé : afficher le résultat."""
        self.exec_frame.hide()
        self.result_frame.show()

        # Choisir l'icône et couleur selon le statut
        statut = report.statut
        if statut == "SUCCESS":
            icon_name = "fa5s.check-circle"
            color = "#10B981"
            title = "Import réussi !"
            subtitle = f"Toutes les données ont été importées avec succès en {report.duree_ms} ms."
        elif statut == "PARTIAL":
            icon_name = "fa5s.exclamation-circle"
            color = "#F59E0B"
            title = "Import partiel"
            subtitle = f"L'import s'est terminé avec des avertissements ({report.duree_ms} ms)."
        else:
            icon_name = "fa5s.times-circle"
            color = "#DC2626"
            title = "Import échoué"
            subtitle = f"L'import n'a pas pu s'exécuter ({report.duree_ms} ms)."

        self.result_icon.setPixmap(qta.icon(icon_name, color=color).pixmap(QSize(56, 56)))
        self.result_title.setText(title)
        self.result_title.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        self.result_subtitle.setText(subtitle)

        # Compteurs
        self.result_stats["nb_crees"].value_label.setText(str(report.nb_crees))
        self.result_stats["nb_modifies"].value_label.setText(str(report.nb_modifies))
        self.result_stats["nb_ignores"].value_label.setText(str(report.nb_ignores))
        self.result_stats["nb_erreurs"].value_label.setText(str(report.nb_erreurs))

        # Message audit
        self.audit_msg.setText(
            f"<b>Traçabilité :</b> cet import a été enregistré dans le journal "
            f"des imports (ID #{report.import_log_id}). Vous pouvez consulter le "
            f"détail dans l'onglet <b>Historique imports</b>."
        )

    def _on_import_error(self, error_msg: str):
        """Erreur critique pendant l'import."""
        self.exec_frame.hide()
        self.result_frame.show()

        self.result_icon.setPixmap(
            qta.icon("fa5s.times-circle", color="#DC2626").pixmap(QSize(56, 56))
        )
        self.result_title.setText("Erreur critique")
        self.result_title.setStyleSheet(
            "color: #DC2626; font-size: 22px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        self.result_subtitle.setText(f"L'import n'a pas pu se lancer : {error_msg}")

        # Reset compteurs
        for card in self.result_stats.values():
            card.value_label.setText("—")

        self.audit_msg.setText(
            "<b>Erreur non récupérée.</b> Aucune donnée n'a été modifiée. "
            "Vérifiez le fichier et réessayez."
        )