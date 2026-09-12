"""
========================================================================
DRENAET-RH — Formulaire : Demande d'Autorisation d'Absence
========================================================================
Formulaire pour générer une autorisation d'absence.

Fonctionnement :
1. Utilisateur tape le matricule de l'agent → auto-remplissage des infos
2. Saisit dates, destination, motif
3. Saisit matricule de l'intérimaire (optionnel) → auto-remplissage
4. Clique "Générer" → PDF créé et ouvert
"""

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QDateEdit, QTextEdit, QPushButton, QFrame,
    QScrollArea, QMessageBox, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSize

from src.models import get_session, Personnel
from src.services.auth_service import UserSession
from src.services.document_generator import DocumentGenerator
from src.services.document_templates.autorisation_absence import AutorisationAbsenceTemplate
from src.ui.widgets.icon_label import IconLabel, StepLabel


class AutorisationAbsenceForm(QWidget):
    """Formulaire pour générer une Autorisation d'Absence."""

    back_requested = pyqtSignal()  # retour à la liste des docs
    document_generated = pyqtSignal(str, str)  # (path_pdf, numero)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.agent = None       # Personnel sélectionné
        self.interim_agent = None  # Personnel intérimaire (optionnel)
        self._build_ui()

    # ====================================================================
    def _build_ui(self):
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 30)
        layout.setSpacing(20)

        # === Bouton retour ===
        back_layout = QHBoxLayout()
        back_btn = QPushButton("  Retour aux documents")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#4338CA"))
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setFixedHeight(38)
        back_btn.setFixedWidth(220)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()
        layout.addLayout(back_layout)

        # === Header ===
        header = self._build_header_card()
        layout.addWidget(header)

        # === Étape 1 : Identifier l'agent (matricule) ===
        layout.addWidget(StepLabel(1, "BÉNÉFICIAIRE DE L'AUTORISATION",
            "Saisir le matricule de l'agent demandeur",
            color="#4338CA"))

        self.agent_card = self._build_agent_search_card(is_interim=False)
        layout.addWidget(self.agent_card)

        # === Étape 2 : Détails de l'absence ===
        layout.addWidget(StepLabel(2, "DÉTAILS DE L'AUTORISATION",
            "Renseigner la période, la destination et le motif",
            color="#4338CA"))

        details_card = self._build_details_card()
        layout.addWidget(details_card)

        # === Étape 3 : Intérimaire (optionnel) ===
        layout.addWidget(StepLabel(3, "INTÉRIMAIRE (optionnel)",
            "Désigner un agent qui assurera l'intérim pendant l'absence",
            color="#4338CA"))

        self.interim_card = self._build_agent_search_card(is_interim=True)
        layout.addWidget(self.interim_card)

        # === Bouton Générer ===
        gen_layout = QHBoxLayout()
        gen_layout.addStretch()

        self.gen_btn = QPushButton("  GÉNÉRER LE DOCUMENT")
        self.gen_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        self.gen_btn.setIconSize(QSize(18, 18))
        self.gen_btn.setMinimumHeight(50)
        self.gen_btn.setMinimumWidth(280)
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #312E81; }
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
        """En-tête de la page."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338CA, stop:1 #7C3AED);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; }
        """)
        card.setMinimumHeight(80)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)

        # Icône
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.calendar-check", color="#FFFFFF").pixmap(QSize(42, 42)))
        layout.addWidget(icon_lbl)
        layout.addSpacing(16)

        # Texte
        text_layout = QVBoxLayout()
        title = QLabel("Demande d'Autorisation d'Absence")
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(title)

        sub = QLabel("Générer une autorisation d'absence pour un agent du Service")
        sub.setStyleSheet("color: #FFFFFF; font-size: 11px;")
        text_layout.addWidget(sub)

        layout.addLayout(text_layout)
        layout.addStretch()

        return card


    # ====================================================================
    def _build_agent_search_card(self, is_interim: bool = False) -> QFrame:
        """Carte de recherche/affichage d'un agent par matricule."""
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

        # Ligne de recherche
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        mat_lbl = IconLabel("fa5s.id-card", "Matricule :", icon_color="#4338CA", icon_size=16)
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
            QLineEdit:focus { border-color: #4338CA; }
        """)
        search_layout.addWidget(mat_input)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setMinimumHeight(36)
        search_btn.setFixedWidth(140)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA; color: #FFFFFF; border: none;
                border-radius: 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #312E81; }
        """)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Zone d'affichage des infos de l'agent (vide au départ)
        info_label = QLabel(
            "Saisissez un matricule puis cliquez sur Rechercher" if not is_interim
            else "Optionnel — Laissez vide si pas d'intérimaire"
        )
        info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Stocker les widgets dans la carte pour pouvoir les manipuler
        card.mat_input = mat_input
        card.search_btn = search_btn
        card.info_label = info_label
        card.is_interim = is_interim

        # Brancher la recherche
        search_btn.clicked.connect(lambda: self._search_agent(card))
        mat_input.returnPressed.connect(lambda: self._search_agent(card))

        return card

    # ====================================================================
    def _build_details_card(self) -> QFrame:
        """Carte des détails de l'absence (dates, motif, etc.)."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QLineEdit, QDateEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #4338CA;
            }
            QLabel {
                color: #1E1B4B; font-size: 12px; font-weight: bold;
            }
        """)

        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Date début
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        self.date_debut.setDisplayFormat("dd/MM/yyyy")
        self.date_debut.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-plus", "Date de début :",
                              icon_color="#4338CA", icon_size=16), self.date_debut)

        # Date fin
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addDays(2))
        self.date_fin.setDisplayFormat("dd/MM/yyyy")
        self.date_fin.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-check", "Date de fin :",
                              icon_color="#4338CA", icon_size=16), self.date_fin)

        # Date reprise
        self.date_reprise = QDateEdit()
        self.date_reprise.setCalendarPopup(True)
        self.date_reprise.setDate(QDate.currentDate().addDays(3))
        self.date_reprise.setDisplayFormat("dd/MM/yyyy")
        self.date_reprise.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-check", "🔄  Date de reprise :",
                              icon_color="#4338CA", icon_size=16), self.date_reprise)

        # Heure reprise
        self.heure_reprise = QLineEdit("07h30")
        self.heure_reprise.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.clock", "Heure de reprise :",
                              icon_color="#4338CA", icon_size=16), self.heure_reprise)

        # Destination
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("Ex : L'Ambassade de France - Abidjan")
        self.destination.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.map-marker-alt", "Destination :",
                              icon_color="#4338CA", icon_size=16), self.destination)

        # Motif
        self.motif = QTextEdit()
        self.motif.setPlaceholderText("Ex : Courses administratives")
        self.motif.setMaximumHeight(80)
        form.addRow(IconLabel("fa5s.comment-dots", "Motif :",
                              icon_color="#4338CA", icon_size=16), self.motif)

        return card

    # ====================================================================
    def _search_agent(self, card):
        """Recherche un agent par matricule et affiche ses infos."""
        matricule = card.mat_input.text().strip().upper()
        if not matricule:
            card.info_label.setText(
                "Veuillez saisir un matricule."
            )
            card.info_label.setStyleSheet(
                "color: #DC2626; font-size: 11px; padding: 8px;"
            )
            return

        with get_session() as db:
            agent = db.query(Personnel).filter_by(matricule=matricule).first()

            if not agent:
                card.info_label.setText(
                    f"Aucun agent trouvé avec le matricule <b>{matricule}</b>."
                )
                card.info_label.setStyleSheet(
                    "color: #DC2626; font-size: 11px; padding: 8px;"
                )
                if card.is_interim:
                    self.interim_agent = None
                else:
                    self.agent = None
                return

            # Construire le bel affichage de l'agent
            text = self._format_agent_display(agent)
            card.info_label.setText(text)
            card.info_label.setStyleSheet("""
                QLabel {
                    background-color: #F0FDF4;
                    border: 1.5px solid #10B981;
                    border-radius: 8px;
                    padding: 14px;
                    color: #1E1B4B;
                    font-size: 12px;
                }
            """)

            # Stocker l'agent
            if card.is_interim:
                self.interim_agent = {
                    "id": agent.id,
                    "matricule": agent.matricule,
                    "nom_complet": agent.nom_complet,
                    "emploi": agent.emploi,
                    "fonction": agent.fonction or "",
                    "structure": agent.structure.nom if agent.structure else "",
                }
            else:
                self.agent = {
                    "id": agent.id,
                    "matricule": agent.matricule,
                    "nom_complet": agent.nom_complet,
                }

    # ====================================================================
    def _format_agent_display(self, agent) -> str:
        """Formate l'affichage d'un agent trouvé."""
        return (
            f"<b>Agent trouvé</b><br/><br/>"
            f"<b>Matricule :</b> {agent.matricule}<br/>"
            f"<b>Nom complet :</b> {agent.nom_complet}<br/>"
            f"<b>Emploi :</b> {agent.emploi}<br/>"
            f"<b>Fonction :</b> {agent.fonction or '—'}<br/>"
            f"<b>Structure :</b> {agent.structure.nom if agent.structure else '—'}<br/>"
            f"<b>Téléphone :</b> {agent.telephone or '—'}"
        )

    # ====================================================================
    def _on_generate(self):
        """Génère le document PDF."""
        # Validation : agent obligatoire
        if not self.agent:
            QMessageBox.warning(
                self,
                "Agent requis",
                "Veuillez d'abord identifier l'agent bénéficiaire (étape 1)."
            )
            return

        # Validation : destination et motif
        if not self.destination.text().strip():
            QMessageBox.warning(
                self, "Champ requis", "La destination est requise."
            )
            return

        if not self.motif.toPlainText().strip():
            QMessageBox.warning(
                self, "Champ requis", "Le motif est requis."
            )
            return

        # Validation des dates
        d_debut = self.date_debut.date().toPyDate()
        d_fin = self.date_fin.date().toPyDate()
        if d_fin < d_debut:
            QMessageBox.warning(
                self, "Dates invalides",
                "La date de fin doit être postérieure à la date de début."
            )
            return

        # Préparer les paramètres
        parameters = {
            "date_debut": d_debut,
            "date_fin": d_fin,
            "date_reprise": self.date_reprise.date().toPyDate(),
            "heure_reprise": self.heure_reprise.text().strip(),
            "destination": self.destination.text().strip(),
            "motif": self.motif.toPlainText().strip(),
        }

        if self.interim_agent:
            parameters["interim_personnel_id"] = self.interim_agent["id"]
            parameters["interim"] = {
                "matricule": self.interim_agent["matricule"],
                "nom_complet": self.interim_agent["nom_complet"],
                "emploi": self.interim_agent["emploi"],
                "fonction": self.interim_agent["fonction"],
                "structure": self.interim_agent["structure"],
            }

        # Désactiver le bouton pendant la génération
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Génération en cours...")

        try:
            # Génération
            session = UserSession.get_instance()
            generator = DocumentGenerator()
            template = AutorisationAbsenceTemplate()

            pdf_path, numero = generator.generate(
                template=template,
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
                    type_absence="Autorisation d'absence",
                    date_debut=d_debut,
                    date_fin=d_fin,
                    motif=parameters["motif"],
                    document_id=document_id,
                    user_login=session.login or "user",
                )
                if absence_result.get("error"):
                    print(f"[Absences] Création auto échouée (non bloquant) : {absence_result['error']}")
            except Exception as hook_error:
                print(f"[Absences] Hook création auto échoué (non bloquant) : {hook_error}")

            # Boîte de succès avec ouverture du PDF
            reply = QMessageBox.information(
                self,
                "Document généré",
                f"<b>Document créé avec succès !</b><br/><br/>"
                f"<b>Numéro :</b> {numero}<br/>"
                f"<b>Fichier :</b> {Path(pdf_path).name}<br/><br/>"
                f"Souhaitez-vous ouvrir le document ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._open_pdf(pdf_path)

            # Émettre le signal
            self.document_generated.emit(pdf_path, numero)

            # Reset du formulaire
            self._reset_form()

        except Exception as e:
            QMessageBox.critical(
                self, "Erreur de génération",
                f"Une erreur est survenue :\n\n{str(e)}"
            )
        finally:
            self.gen_btn.setEnabled(True)
            self.gen_btn.setText("  GÉNÉRER LE DOCUMENT")

    # ====================================================================
    def _open_pdf(self, path: str):
        """Ouvre le PDF avec le lecteur par défaut."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(
                self, "Ouverture impossible",
                f"Le PDF a été créé mais n'a pas pu être ouvert automatiquement.\n\n"
                f"Chemin : {path}\n\nErreur : {e}"
            )

    # ====================================================================
    def _reset_form(self):
        """Vide tous les champs après une génération réussie."""
        self.agent = None
        self.interim_agent = None
        self.agent_card.mat_input.clear()
        self.interim_card.mat_input.clear()
        self.agent_card.info_label.setText(
            "Saisissez un matricule puis cliquez sur Rechercher"
        )
        self.agent_card.info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        self.interim_card.info_label.setText(
            "Optionnel — Laissez vide si pas d'intérimaire"
        )
        self.interim_card.info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        self.destination.clear()
        self.motif.clear()