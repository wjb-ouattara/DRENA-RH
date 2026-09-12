"""
========================================================================
DRENAET-RH — Formulaire : Attestation de Travail
========================================================================
"""

import os
import subprocess
import sys
from pathlib import Path

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from src.models import get_session, Personnel
from src.services.auth_service import UserSession
from src.services.document_generator import DocumentGenerator
from src.services.document_templates.attestation_travail import AttestationTravailTemplate
from src.ui.widgets.icon_label import IconLabel, StepLabel


class AttestationTravailForm(QWidget):
    """Formulaire pour générer une Attestation de Travail."""

    back_requested = pyqtSignal()
    document_generated = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.agent = None
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 30)
        layout.setSpacing(20)

        # Bouton retour
        back_layout = QHBoxLayout()
        back_btn = QPushButton("  Retour aux documents")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#EC4899"))
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setFixedHeight(38)
        back_btn.setFixedWidth(220)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()
        layout.addLayout(back_layout)

        # Header
        layout.addWidget(self._build_header_card())

        # Étape 1 : Agent
        layout.addWidget(StepLabel(1, "AGENT CONCERNÉ",
            "Saisir le matricule de l'agent à attester",
            color="#EC4899"))
        self.agent_card = self._build_agent_search_card()
        layout.addWidget(self.agent_card)

        # Étape 2 : But (optionnel)
        layout.addWidget(StepLabel(2, "BUT DE L'ATTESTATION (optionnel)",
            "À quoi servira cette attestation ? (banque, visa, etc.)",
            color="#EC4899"))
        layout.addWidget(self._build_but_card())

        # Bouton Générer
        gen_layout = QHBoxLayout()
        gen_layout.addStretch()
        self.gen_btn = QPushButton("  GÉNÉRER L'ATTESTATION")
        self.gen_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        self.gen_btn.setIconSize(QSize(18, 18))
        self.gen_btn.setMinimumHeight(50)
        self.gen_btn.setMinimumWidth(280)
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #EC4899;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #DB2777; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.gen_btn.clicked.connect(self._on_generate)
        gen_layout.addWidget(self.gen_btn)
        layout.addLayout(gen_layout)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ====================================================================
    def _build_header_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EC4899, stop:1 #F472B6);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; }
        """)
        card.setMinimumHeight(80)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.file-signature", color="#FFFFFF").pixmap(QSize(42, 42)))
        layout.addWidget(icon_lbl)
        layout.addSpacing(16)

        text_layout = QVBoxLayout()
        title = QLabel("Attestation de Travail")
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(title)

        sub = QLabel("Certifier qu'un agent est en service à la DRENAET")
        sub.setStyleSheet("color: #FFFFFF; font-size: 11px;")
        text_layout.addWidget(sub)

        layout.addLayout(text_layout)
        layout.addStretch()
        return card


    # ====================================================================
    def _build_agent_search_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        mat_lbl = IconLabel("fa5s.id-card", "Matricule :", icon_color="#EC4899", icon_size=16)
        mat_lbl.setFixedWidth(130)
        search_layout.addWidget(mat_lbl)

        mat_input = QLineEdit()
        mat_input.setPlaceholderText("Ex : 233329C")
        mat_input.setMinimumHeight(36)
        mat_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QLineEdit:focus { border-color: #EC4899; }
        """)
        search_layout.addWidget(mat_input)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setMinimumHeight(36)
        search_btn.setFixedWidth(140)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #EC4899; color: #FFFFFF; border: none;
                border-radius: 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #DB2777; }
        """)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        info_label = QLabel("Saisissez un matricule puis cliquez sur Rechercher")
        info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        card.mat_input = mat_input
        card.search_btn = search_btn
        card.info_label = info_label

        search_btn.clicked.connect(lambda: self._search_agent(card))
        mat_input.returnPressed.connect(lambda: self._search_agent(card))
        return card

    # ====================================================================
    def _build_but_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QLineEdit:focus { border-color: #EC4899; }
            QLabel {
                color: #1E1B4B; font-size: 12px; font-weight: bold;
            }
        """)

        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)

        self.but = QLineEdit()
        self.but.setPlaceholderText(
            "Ex : auprès de la SGBCI - Demande de prêt"
            "  (laisser vide → 'ce que de droit')"
        )
        self.but.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.bullseye", "But :",
                              icon_color="#EC4899", icon_size=16), self.but)

        return card

    # ====================================================================
    def _search_agent(self, card):
        matricule = card.mat_input.text().strip().upper()
        if not matricule:
            card.info_label.setText("Veuillez saisir un matricule.")
            card.info_label.setStyleSheet("color: #DC2626; font-size: 11px; padding: 8px;")
            return

        with get_session() as db:
            agent = db.query(Personnel).filter_by(matricule=matricule).first()
            if not agent:
                card.info_label.setText(
                    f"Aucun agent trouvé avec le matricule <b>{matricule}</b>."
                )
                card.info_label.setStyleSheet("color: #DC2626; font-size: 11px; padding: 8px;")
                self.agent = None
                return

            text = (
                f"<b>Agent trouvé</b><br/><br/>"
                f"<b>Matricule :</b> {agent.matricule}<br/>"
                f"<b>Nom complet :</b> {agent.nom_complet}<br/>"
                f"<b>Emploi :</b> {agent.emploi}<br/>"
                f"<b>Grade :</b> {agent.grade or '—'}<br/>"
                f"<b>Fonction :</b> {agent.fonction or '—'}<br/>"
                f"<b>Structure :</b> {agent.structure.nom if agent.structure else '—'}<br/>"
                f"<b>Date prise service :</b> "
                f"{agent.date_prise_service.strftime('%d/%m/%Y') if agent.date_prise_service else '—'}"
            )
            card.info_label.setText(text)
            card.info_label.setStyleSheet("""
                QLabel {
                    background-color: #FDF2F8;
                    border: 1.5px solid #EC4899;
                    border-radius: 8px;
                    padding: 14px;
                    color: #1E1B4B;
                    font-size: 12px;
                }
            """)
            self.agent = {
                "id": agent.id,
                "matricule": agent.matricule,
                "nom_complet": agent.nom_complet,
            }

    # ====================================================================
    def _on_generate(self):
        if not self.agent:
            QMessageBox.warning(self, "Agent requis",
                                "Veuillez d'abord identifier l'agent concerné.")
            return

        parameters = {
            "but": self.but.text().strip() or None,
        }

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Génération en cours...")

        try:
            session = UserSession.get_instance()
            generator = DocumentGenerator()
            template = AttestationTravailTemplate()

            pdf_path, numero = generator.generate(
                template=template,
                personnel_id=self.agent["id"],
                parameters=parameters,
                user_login=session.login or "user",
            )

            reply = QMessageBox.information(
                self, "Document généré",
                f"<b>Attestation de Travail créée avec succès !</b><br/><br/>"
                f"<b>Numéro :</b> {numero}<br/>"
                f"<b>Fichier :</b> {Path(pdf_path).name}<br/><br/>"
                f"Souhaitez-vous ouvrir le document ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._open_pdf(pdf_path)

            self.document_generated.emit(pdf_path, numero)
            self._reset_form()

        except Exception as e:
            QMessageBox.critical(self, "Erreur de génération",
                                 f"Une erreur est survenue :\n\n{str(e)}")
        finally:
            self.gen_btn.setEnabled(True)
            self.gen_btn.setText("  GÉNÉRER L'ATTESTATION")

    # ====================================================================
    def _open_pdf(self, path: str):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Ouverture impossible",
                                f"Le PDF a été créé mais n'a pas pu être ouvert.\n\nChemin : {path}")

    # ====================================================================
    def _reset_form(self):
        self.agent = None
        self.agent_card.mat_input.clear()
        self.agent_card.info_label.setText("Saisissez un matricule puis cliquez sur Rechercher")
        self.agent_card.info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        self.but.clear()