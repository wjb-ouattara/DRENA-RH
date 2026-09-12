"""
========================================================================
DRENAET-RH — Formulaire : Titre de Congés
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
from src.services.document_templates.titre_conges import TitreCongesTemplate
from src.ui.widgets.icon_label import IconLabel, StepLabel


class TitreCongesForm(QWidget):
    """Formulaire pour générer un Titre de Congés."""

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
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#10B981"))
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setFixedHeight(38)
        back_btn.setFixedWidth(220)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()
        layout.addLayout(back_layout)

        # Header
        layout.addWidget(self._build_header_card())

        # Étape 1 : Agent
        layout.addWidget(StepLabel(1, "AGENT EN CONGÉS",
            "Saisir le matricule de l'agent demandeur",
            color="#10B981"))
        self.agent_card = self._build_agent_search_card()
        layout.addWidget(self.agent_card)

        # Étape 2 : Période et destination
        layout.addWidget(StepLabel(2, "PÉRIODE ET DESTINATION",
            "Définir la période de congés et le lieu de villégiature",
            color="#10B981"))
        layout.addWidget(self._build_details_card())

        # Bouton Générer
        gen_layout = QHBoxLayout()
        gen_layout.addStretch()
        self.gen_btn = QPushButton("  GÉNÉRER LE TITRE DE CONGÉS")
        self.gen_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        self.gen_btn.setIconSize(QSize(18, 18))
        self.gen_btn.setMinimumHeight(50)
        self.gen_btn.setMinimumWidth(300)
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #059669; }
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
                    stop:0 #10B981, stop:1 #34D399);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; }
        """)
        card.setMinimumHeight(80)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.umbrella-beach", color="#FFFFFF").pixmap(QSize(42, 42)))
        layout.addWidget(icon_lbl)
        layout.addSpacing(16)

        text_layout = QVBoxLayout()
        title = QLabel("Titre de Congés")
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(title)
        sub = QLabel("Autoriser un agent à prendre ses congés sur une période donnée")
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
        mat_lbl = IconLabel("fa5s.id-card", "Matricule :", icon_color="#10B981", icon_size=16)
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
            QLineEdit:focus { border-color: #10B981; }
        """)
        search_layout.addWidget(mat_input)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setMinimumHeight(36)
        search_btn.setFixedWidth(140)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: #FFFFFF; border: none;
                border-radius: 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #059669; }
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
            QLineEdit:focus, QDateEdit:focus { border-color: #10B981; }
            QLabel { color: #1E1B4B; font-size: 12px; font-weight: bold; }
        """)
        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)

        # Date début
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        self.date_debut.setDisplayFormat("dd/MM/yyyy")
        self.date_debut.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-plus", "Début des congés :",
                              icon_color="#10B981", icon_size=16), self.date_debut)

        # Date fin
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addDays(30))
        self.date_fin.setDisplayFormat("dd/MM/yyyy")
        self.date_fin.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-check", "Fin des congés (inclus) :",
                              icon_color="#10B981", icon_size=16), self.date_fin)

        # Destination
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("Ex : Abidjan / Au village natal / En France")
        self.destination.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.map-marker-alt", "Destination :",
                              icon_color="#10B981", icon_size=16), self.destination)

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
                f"<b>Fonction :</b> {agent.fonction or '—'}<br/>"
                f"<b>Structure :</b> {agent.structure.nom if agent.structure else '—'}"
            )
            card.info_label.setText(text)
            card.info_label.setStyleSheet("""
                QLabel {
                    background-color: #ECFDF5;
                    border: 1.5px solid #10B981;
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

        d_debut = self.date_debut.date().toPyDate()
        d_fin = self.date_fin.date().toPyDate()
        if d_fin < d_debut:
            QMessageBox.warning(self, "Dates invalides",
                                "La date de fin doit être postérieure à la date de début.")
            return

        if not self.destination.text().strip():
            QMessageBox.warning(self, "Champ requis", "La destination est requise.")
            return

        parameters = {
            "date_debut": d_debut,
            "date_fin": d_fin,
            "destination": self.destination.text().strip(),
        }

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Génération en cours...")

        try:
            session = UserSession.get_instance()
            generator = DocumentGenerator()
            pdf_path, numero = generator.generate(
                template=TitreCongesTemplate(),
                personnel_id=self.agent["id"],
                parameters=parameters,
                user_login=session.login or "user",
            )

            # === HOOK Sprint 5 : création automatique de l'absence liée ===
            try:
                from src.services.absence_service import AbsenceService
                from src.models import get_session
                from src.models.document import DocumentGenere

                with get_session() as db:
                    doc = (
                        db.query(DocumentGenere)
                        .filter_by(numero=numero)
                        .order_by(DocumentGenere.id.desc())
                        .first()
                    )
                    document_id = doc.id if doc else None

                absence_result = AbsenceService.create_from_document(
                    personnel_id=self.agent["id"],
                    type_absence="Congé annuel",
                    date_debut=d_debut,
                    date_fin=d_fin,
                    motif=f"Congés - Destination : {parameters['destination']}",
                    document_id=document_id,
                    user_login=session.login or "user",
                )
                if absence_result.get("error"):
                    print(f"[Absences] Création auto échouée (non bloquant) : {absence_result['error']}")
                elif absence_result.get("quota_warning"):
                    qs = absence_result["quota_status"]
                    QMessageBox.warning(
                        self, "Alerte quota de congés",
                        f"⚠ Attention : cet agent dépasse son quota de congés annuels.\n\n"
                        f"Jours pris en {qs['annee']} : {qs['jours_pris']} / {qs['quota_total']} jours.",
                    )
            except Exception as hook_error:
                print(f"[Absences] Hook création auto échoué (non bloquant) : {hook_error}")

            reply = QMessageBox.information(
                self, "Document généré",
                f"<b>Titre de Congés créé !</b><br/><br/>"
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
            self.gen_btn.setText("  GÉNÉRER LE TITRE DE CONGÉS")

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
        self.destination.clear()