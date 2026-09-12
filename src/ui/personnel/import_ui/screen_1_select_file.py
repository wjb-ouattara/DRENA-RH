"""
========================================================================
DRENAET-RH — Écran 1 : Sélection du fichier Excel
========================================================================
Permet à l'utilisateur de :
- Faire glisser un fichier Excel (drag & drop)
- OU cliquer sur "Parcourir" pour ouvrir un dialog
- Voir les infos du fichier sélectionné (nom, taille, feuilles)
- Cliquer sur "Suivant" pour passer à la configuration
"""

from pathlib import Path

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QMessageBox,
)

from src.services.import_pipeline import ExcelReader


class Screen1SelectFile(QWidget):
    """Écran 1 : sélection du fichier Excel."""

    # Signal émis quand un fichier est validé : (path, file_info)
    next_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file: str = None
        self.file_info: dict = None
        self.setAcceptDrops(True)
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # === Titre ===
        title = QLabel("Étape 1 : Sélectionnez votre fichier Excel")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Formats acceptés : .xlsx • Vous pouvez glisser-déposer un fichier "
            "ou cliquer sur 'Parcourir'."
        )
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        layout.addWidget(subtitle)

        # === Zone de drop ===
        self.drop_zone = self._build_drop_zone()
        layout.addWidget(self.drop_zone, stretch=1)

        # === Zone d'infos du fichier (cachée par défaut) ===
        self.info_frame = self._build_info_frame()
        self.info_frame.hide()
        layout.addWidget(self.info_frame)

        # === Boutons ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.next_btn = QPushButton("  Suivant  ")
        self.next_btn.setIcon(qta.icon("fa5s.arrow-right", color="#FFFFFF"))
        self.next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setFixedHeight(44)
        self.next_btn.setMinimumWidth(160)
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover:enabled { background-color: #3730A3; }
            QPushButton:disabled { background-color: #CBD5E1; }
        """)
        self.next_btn.clicked.connect(self._on_next)
        buttons_layout.addWidget(self.next_btn)

        layout.addLayout(buttons_layout)

    def _build_drop_zone(self) -> QFrame:
        """Zone de drop drag & drop."""
        frame = QFrame()
        frame.setObjectName("dropZone")
        frame.setStyleSheet("""
            QFrame#dropZone {
                background-color: #FFFFFF;
                border: 2px dashed #C7D2FE;
                border-radius: 12px;
            }
            QFrame#dropZone:hover {
                border-color: #4338CA;
                background-color: #EEF2FF;
            }
        """)
        frame.setMinimumHeight(280)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Grosse icône
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            qta.icon("fa5s.file-excel", color="#4338CA").pixmap(QSize(72, 72))
        )
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        # Texte principal
        main_text = QLabel("Glissez votre fichier Excel ici")
        main_text.setStyleSheet(
            "color: #1E1B4B; font-size: 16px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main_text)

        # Texte secondaire
        sec_text = QLabel("ou")
        sec_text.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent; border: none;"
        )
        sec_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sec_text)

        # Bouton Parcourir
        browse_btn = QPushButton("  Parcourir mes fichiers")
        browse_btn.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(220)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        browse_btn.clicked.connect(self._on_browse)

        browse_layout = QHBoxLayout()
        browse_layout.addStretch()
        browse_layout.addWidget(browse_btn)
        browse_layout.addStretch()
        layout.addLayout(browse_layout)

        return frame

    def _build_info_frame(self) -> QFrame:
        """Zone qui affiche les infos du fichier sélectionné."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #ECFDF5;
                border: 1.5px solid #10B981;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Icône check
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            qta.icon("fa5s.check-circle", color="#10B981").pixmap(QSize(32, 32))
        )
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Infos texte
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.file_name_lbl = QLabel("nom du fichier")
        self.file_name_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 14px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        text_layout.addWidget(self.file_name_lbl)

        self.file_details_lbl = QLabel("détails")
        self.file_details_lbl.setStyleSheet(
            "color: #64748B; font-size: 11px; background: transparent; border: none;"
        )
        text_layout.addWidget(self.file_details_lbl)

        layout.addLayout(text_layout, stretch=1)

        # Bouton "Changer de fichier"
        change_btn = QPushButton("  Changer")
        change_btn.setIcon(qta.icon("fa5s.exchange-alt", color="#4338CA"))
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.setFixedHeight(32)
        change_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4338CA;
                border: 1px solid #4338CA;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #EEF2FF; }
        """)
        change_btn.clicked.connect(self._on_browse)
        layout.addWidget(change_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        return frame

    # ====================================================================
    # DRAG & DROP
    # ====================================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".xlsx") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".xlsx"):
                self._load_file(path)
                event.acceptProposedAction()
                return

    # ====================================================================
    def _on_browse(self):
        """Ouvre le dialog de sélection de fichier."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier Excel",
            str(Path.home()),
            "Fichiers Excel (*.xlsx)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        """Charge un fichier et affiche ses infos."""
        try:
            with ExcelReader(path) as reader:
                info = reader.get_file_info()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur lecture fichier",
                f"Impossible de lire ce fichier :\n\n{e}",
            )
            return

        self.selected_file = path
        self.file_info = info

        # Afficher les infos
        self.file_name_lbl.setText(info["nom_fichier"])
        taille_ko = info["taille_octets"] / 1024
        details = (
            f"{taille_ko:.1f} Ko  •  "
            f"{info['nb_feuilles']} feuille(s) : {', '.join(info['feuilles'])}"
        )
        self.file_details_lbl.setText(details)
        self.info_frame.show()

        # Activer le bouton Suivant
        self.next_btn.setEnabled(True)

    def _on_next(self):
        """Passe à l'écran suivant."""
        if self.selected_file and self.file_info:
            self.next_requested.emit(self.selected_file, self.file_info)