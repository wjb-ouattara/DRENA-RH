"""
========================================================================
DRENAET-RH — Formulaire : Certificat de Prise de Service
========================================================================
"""

import os
import subprocess
import sys
from pathlib import Path

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QDateEdit, QPushButton, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSize

from src.models import get_session, Personnel
from src.services.auth_service import UserSession
from src.services.document_generator import DocumentGenerator
from src.services.document_templates.certificat_prise_service import CertificatPriseServiceTemplate
from src.ui.widgets.icon_label import IconLabel, StepLabel


class CertificatPriseServiceForm(QWidget):
    """Formulaire pour générer un Certificat de Prise de Service."""

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
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#F59E0B"))
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
            "Saisir le matricule de l'agent qui prend service",
            color="#F59E0B"))
        self.agent_card = self._build_agent_search_card()
        layout.addWidget(self.agent_card)

        # Étape 2 : Détails de la prise de service
        layout.addWidget(StepLabel(2, "DÉTAILS DE LA PRISE DE SERVICE",
            "Référence de l'Arrêté de nomination + lieu et date de prise de service",
            color="#F59E0B"))
        layout.addWidget(self._build_details_card())

        # Bouton Générer
        gen_layout = QHBoxLayout()
        gen_layout.addStretch()
        self.gen_btn = QPushButton("  GÉNÉRER LE CERTIFICAT")
        self.gen_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        self.gen_btn.setIconSize(QSize(18, 18))
        self.gen_btn.setMinimumHeight(50)
        self.gen_btn.setMinimumWidth(300)
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #D97706; }
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

    def _build_header_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #F59E0B, stop:1 #FBBF24);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; }
        """)
        card.setMinimumHeight(80)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.handshake", color="#FFFFFF").pixmap(QSize(42, 42)))
        layout.addWidget(icon_lbl)
        layout.addSpacing(16)

        text_layout = QVBoxLayout()
        title = QLabel("Certificat de Prise de Service")
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(title)
        sub = QLabel("Certifier la prise de fonctions effective d'un agent nommé")
        sub.setStyleSheet("color: #FFFFFF; font-size: 11px;")
        text_layout.addWidget(sub)
        layout.addLayout(text_layout)
        layout.addStretch()
        return card

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
        mat_lbl = IconLabel("fa5s.id-card", "Matricule :", icon_color="#F59E0B", icon_size=16)
        mat_lbl.setFixedWidth(130)
        search_layout.addWidget(mat_lbl)

        mat_input = QLineEdit()
        mat_input.setPlaceholderText("Ex : 233329C")
        mat_input.setMinimumHeight(36)
        mat_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
                border-radius: 6px; padding: 6px 12px;
                font-size: 12px; color: #1E1B4B;
            }
            QLineEdit:focus { border-color: #F59E0B; }
        """)
        search_layout.addWidget(mat_input)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setMinimumHeight(36)
        search_btn.setFixedWidth(140)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B; color: #FFFFFF; border: none;
                border-radius: 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #D97706; }
        """)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        info_label = QLabel("Saisissez un matricule puis cliquez sur Rechercher")
        info_label.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic; padding: 8px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        card.mat_input = mat_input
        card.info_label = info_label
        search_btn.clicked.connect(lambda: self._search_agent(card))
        mat_input.returnPressed.connect(lambda: self._search_agent(card))
        return card

    def _build_details_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
            }
            QLineEdit, QDateEdit {
                background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
                border-radius: 6px; padding: 6px 10px;
                font-size: 12px; color: #1E1B4B;
            }
            QLineEdit:focus, QDateEdit:focus { border-color: #F59E0B; }
            QLabel { color: #1E1B4B; font-size: 12px; font-weight: bold; }
        """)
        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)

        # N° Arrêté
        self.num_arrete = QLineEdit()
        self.num_arrete.setPlaceholderText("Ex : 2024-152/MENAET/CAB")
        self.num_arrete.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.file-signature", "N° Arrêté de nomination :",
                              icon_color="#F59E0B", icon_size=16), self.num_arrete)

        # Date Arrêté
        self.date_arrete = QDateEdit()
        self.date_arrete.setCalendarPopup(True)
        self.date_arrete.setDate(QDate.currentDate())
        self.date_arrete.setDisplayFormat("dd/MM/yyyy")
        self.date_arrete.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.file-signature", "Date de l'Arrêté :",
                              icon_color="#F59E0B", icon_size=16), self.date_arrete)

        # Lieu de prise de service
        self.lieu = QLineEdit()
        self.lieu.setPlaceholderText("Laisser vide → reprend la Structure de l'agent")
        self.lieu.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.map-marker-alt", "Lieu de prise de service :",
                              icon_color="#F59E0B", icon_size=16), self.lieu)

        # Qualité (= nouvelle fonction)
        self.qualite = QLineEdit()
        self.qualite.setPlaceholderText("Ex : Directeur du CAFOP / laisser vide → reprend Fonction agent")
        self.qualite.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.briefcase", "Qualité (poste) :",
                              icon_color="#F59E0B", icon_size=16), self.qualite)

        # Date prise de service
        self.date_prise = QDateEdit()
        self.date_prise.setCalendarPopup(True)
        self.date_prise.setDate(QDate.currentDate())
        self.date_prise.setDisplayFormat("dd/MM/yyyy")
        self.date_prise.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-alt", "Date de prise de service :",
                              icon_color="#F59E0B", icon_size=16), self.date_prise)

        return card

    def _search_agent(self, card):
        matricule = card.mat_input.text().strip().upper()
        if not matricule:
            card.info_label.setText("Veuillez saisir un matricule.")
            card.info_label.setStyleSheet("color: #DC2626; font-size: 11px; padding: 8px;")
            return

        with get_session() as db:
            agent = db.query(Personnel).filter_by(matricule=matricule).first()
            if not agent:
                card.info_label.setText(f"Aucun agent trouvé avec le matricule <b>{matricule}</b>.")
                card.info_label.setStyleSheet("color: #DC2626; font-size: 11px; padding: 8px;")
                self.agent = None
                return

            text = (
                f"<b>Agent trouvé</b><br/><br/>"
                f"<b>Matricule :</b> {agent.matricule}<br/>"
                f"<b>Nom complet :</b> {agent.nom_complet}<br/>"
                f"<b>Emploi :</b> {agent.emploi}<br/>"
                f"<b>Fonction actuelle :</b> {agent.fonction or '—'}<br/>"
                f"<b>Structure :</b> {agent.structure.nom if agent.structure else '—'}"
            )
            card.info_label.setText(text)
            card.info_label.setStyleSheet("""
                QLabel {
                    background-color: #FFFBEB;
                    border: 1.5px solid #F59E0B;
                    border-radius: 8px;
                    padding: 14px;
                    color: #1E1B4B;
                    font-size: 12px;
                }
            """)
            self.agent = {
                "id": agent.id, "matricule": agent.matricule,
                "nom_complet": agent.nom_complet,
            }

    def _on_generate(self):
        if not self.agent:
            QMessageBox.warning(self, "Agent requis",
                                "Veuillez d'abord identifier l'agent.")
            return

        if not self.num_arrete.text().strip():
            QMessageBox.warning(self, "Champ requis",
                                "Le numéro d'Arrêté de nomination est requis.")
            return

        parameters = {
            "num_arrete": self.num_arrete.text().strip(),
            "date_arrete": self.date_arrete.date().toPyDate(),
            "lieu_prise_service": self.lieu.text().strip() or None,
            "qualite": self.qualite.text().strip() or None,
            "date_prise_service": self.date_prise.date().toPyDate(),
        }

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Génération en cours...")

        try:
            session = UserSession.get_instance()
            generator = DocumentGenerator()
            pdf_path, numero = generator.generate(
                template=CertificatPriseServiceTemplate(),
                personnel_id=self.agent["id"],
                parameters=parameters,
                user_login=session.login or "user",
            )

            reply = QMessageBox.information(
                self, "Document généré",
                f"<b>Certificat de Prise de Service créé !</b><br/><br/>"
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
            QMessageBox.critical(self, "Erreur",
                                 f"Une erreur est survenue :\n\n{str(e)}")
        finally:
            self.gen_btn.setEnabled(True)
            self.gen_btn.setText("  GÉNÉRER LE CERTIFICAT")

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
                                f"Le PDF a été créé.\n\nChemin : {path}")

    def _reset_form(self):
        self.agent = None
        self.agent_card.mat_input.clear()
        self.agent_card.info_label.setText("Saisissez un matricule puis cliquez sur Rechercher")
        self.agent_card.info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        self.num_arrete.clear()
        self.lieu.clear()
        self.qualite.clear()