"""
========================================================================
DRENAET-RH — Formulaire : Fiche d'inscription Mutation
========================================================================
Document complexe avec :
- Recherche agent par matricule
- Dates complémentaires (optionnelles, sinon reprises de l'agent)
- 3 vœux de mutation (DRENAET + IEPP par vœu, au moins 1 obligatoire)
"""

import os
import subprocess
import sys
from pathlib import Path

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QDateEdit, QPushButton, QFrame, QScrollArea, QMessageBox,
    QGridLayout
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSize

from src.models import get_session, Personnel
from src.services.auth_service import UserSession
from src.services.document_generator import DocumentGenerator
from src.services.document_templates.fiche_mutation import FicheMutationTemplate
from src.ui.widgets.icon_label import IconLabel, StepLabel


class FicheMutationForm(QWidget):
    """Formulaire pour générer une Fiche d'inscription Mutation."""

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

        # Retour
        back_layout = QHBoxLayout()
        back_btn = QPushButton("  Retour aux documents")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color="#3B82F6"))
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setFixedHeight(38)
        back_btn.setFixedWidth(220)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()
        layout.addLayout(back_layout)

        layout.addWidget(self._build_header_card())

        # Étape 1 : Agent
        layout.addWidget(StepLabel(
            1, "AGENT DEMANDEUR DE MUTATION",
            "Saisir le matricule du Chef de Circonscription demandeur",
            color="#3B82F6"))
        self.agent_card = self._build_agent_search_card()
        layout.addWidget(self.agent_card)

        # Étape 2 : Dates complémentaires
        layout.addWidget(StepLabel(
            2, "INFORMATIONS PROFESSIONNELLES COMPLÉMENTAIRES",
            "Dates clés de la carrière (laisser vide → calcul auto depuis l'agent)",
            color="#3B82F6"))
        layout.addWidget(self._build_dates_card())

        # Étape 3 : Vœux
        layout.addWidget(StepLabel(
            3, "LISTE DES VŒUX DE MUTATION",
            "Au moins 1 vœu obligatoire (DRENAET souhaitée + IEPP souhaitée)",
            color="#3B82F6"))
        layout.addWidget(self._build_voeux_card())

        # Bouton générer
        gen_layout = QHBoxLayout()
        gen_layout.addStretch()
        self.gen_btn = QPushButton("  GÉNÉRER LA FICHE DE MUTATION")
        self.gen_btn.setIcon(qta.icon("fa5s.file-pdf", color="#FFFFFF"))
        self.gen_btn.setIconSize(QSize(18, 18))
        self.gen_btn.setMinimumHeight(50)
        self.gen_btn.setMinimumWidth(320)
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #2563EB; }
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
                    stop:0 #3B82F6, stop:1 #60A5FA);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; }
        """)
        card.setMinimumHeight(80)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.exchange-alt", color="#FFFFFF").pixmap(QSize(42, 42)))
        layout.addWidget(icon_lbl)
        layout.addSpacing(16)

        text_layout = QVBoxLayout()
        title = QLabel("Fiche d'inscription Mutation")
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(title)
        sub = QLabel("Demande de mutation - Chef de Circonscription d'Enseignement Préscolaire et Primaire")
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
        mat_lbl = IconLabel("fa5s.id-card", "Matricule :", icon_color="#3B82F6", icon_size=16)
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
            QLineEdit:focus { border-color: #3B82F6; }
        """)
        search_layout.addWidget(mat_input)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setMinimumHeight(36)
        search_btn.setFixedWidth(140)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: #FFFFFF; border: none;
                border-radius: 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #2563EB; }
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

    # ====================================================================
    def _build_dates_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
            }
            QDateEdit {
                background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
                border-radius: 6px; padding: 6px 10px;
                font-size: 12px; color: #1E1B4B;
            }
            QDateEdit:focus { border-color: #3B82F6; }
            QLabel { color: #1E1B4B; font-size: 12px; font-weight: bold; }
        """)
        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)

        # Date entrée Fonction Publique
        self.date_entree_fp = QDateEdit()
        self.date_entree_fp.setCalendarPopup(True)
        self.date_entree_fp.setDate(QDate(2000, 1, 1))
        self.date_entree_fp.setDisplayFormat("dd/MM/yyyy")
        self.date_entree_fp.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-alt", "Date d'entrée à la Fonction Publique :",
                              icon_color="#3B82F6", icon_size=16), self.date_entree_fp)

        # Date entrée DRENAET
        self.date_entree_drenaet = QDateEdit()
        self.date_entree_drenaet.setCalendarPopup(True)
        self.date_entree_drenaet.setDate(QDate(2010, 1, 1))
        self.date_entree_drenaet.setDisplayFormat("dd/MM/yyyy")
        self.date_entree_drenaet.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-alt", "Date d'entrée à la DRENAET Katiola :",
                              icon_color="#3B82F6", icon_size=16), self.date_entree_drenaet)

        # Date fonction actuelle
        self.date_fonction_actuelle = QDateEdit()
        self.date_fonction_actuelle.setCalendarPopup(True)
        self.date_fonction_actuelle.setDate(QDate(2018, 9, 1))
        self.date_fonction_actuelle.setDisplayFormat("dd/MM/yyyy")
        self.date_fonction_actuelle.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-alt", "Date de prise de fonction actuelle :",
                              icon_color="#3B82F6", icon_size=16), self.date_fonction_actuelle)

        # Date retraite
        self.date_retraite = QDateEdit()
        self.date_retraite.setCalendarPopup(True)
        self.date_retraite.setDate(QDate(2035, 12, 31))
        self.date_retraite.setDisplayFormat("dd/MM/yyyy")
        self.date_retraite.setMinimumHeight(34)
        form.addRow(IconLabel("fa5s.calendar-plus", "Date de départ à la retraite :",
                              icon_color="#3B82F6", icon_size=16), self.date_retraite)

        return card

    # ====================================================================
    def _build_voeux_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
            }
            QLineEdit {
                background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
                border-radius: 6px; padding: 6px 10px;
                font-size: 12px; color: #1E1B4B;
            }
            QLineEdit:focus { border-color: #3B82F6; }
            QLabel { color: #1E1B4B; font-size: 12px; font-weight: bold; }
        """)

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Stockage des 3 vœux
        self.voeux_inputs = []

        for i in range(1, 4):  # 3 vœux
            voeu_widget = self._build_voeu_row(i)
            main_layout.addWidget(voeu_widget)

        # Note d'obligation
        note = QLabel("Au moins le 1er vœu est obligatoire (DRENAET + IEPP).")
        note.setStyleSheet("color: #DC2626; font-size: 11px; font-style: italic; padding-top: 4px;")
        main_layout.addWidget(note)

        return card

    def _build_voeu_row(self, num: int) -> QWidget:
        """Construit une ligne pour un vœu : N° | DRENAET | IEPP."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QGridLayout(widget)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Numéro du vœu
        num_label = QLabel(f"Vœu {num}")
        num_label.setStyleSheet("""
            QLabel {
                background-color: #3B82F6;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 10px;
            }
        """)
        num_label.setFixedWidth(70)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(num_label, 0, 0, 2, 1)

        # Label DRENAET
        drenaet_lbl = QLabel("DRENAET souhaitée")
        drenaet_lbl.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold;")
        layout.addWidget(drenaet_lbl, 0, 1)

        # Label IEPP
        iepp_lbl = QLabel("IEPP souhaitée")
        iepp_lbl.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold;")
        layout.addWidget(iepp_lbl, 0, 2)

        # Input DRENAET
        drenaet_input = QLineEdit()
        drenaet_input.setPlaceholderText("Ex : DRENAET DE BOUAKE 1" if num == 1 else "Optionnel")
        drenaet_input.setMinimumHeight(32)
        layout.addWidget(drenaet_input, 1, 1)

        # Input IEPP
        iepp_input = QLineEdit()
        iepp_input.setPlaceholderText("Ex : IEPP BOUAKE NORD" if num == 1 else "Optionnel")
        iepp_input.setMinimumHeight(32)
        layout.addWidget(iepp_input, 1, 2)

        # Stocker les inputs
        self.voeux_inputs.append({
            "num": num,
            "drenaet": drenaet_input,
            "iepp": iepp_input,
        })

        return widget

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
                f"<b>Structure actuelle :</b> {agent.structure.nom if agent.structure else '—'}<br/>"
                f"<b>Téléphone :</b> {agent.telephone or '—'}"
            )
            card.info_label.setText(text)
            card.info_label.setStyleSheet("""
                QLabel {
                    background-color: #EFF6FF;
                    border: 1.5px solid #3B82F6;
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

            # Pré-remplir les dates avec les valeurs de l'agent si dispo
            if agent.date_prise_service:
                self.date_entree_drenaet.setDate(QDate(
                    agent.date_prise_service.year,
                    agent.date_prise_service.month,
                    agent.date_prise_service.day,
                ))
            if agent.date_affectation:
                self.date_fonction_actuelle.setDate(QDate(
                    agent.date_affectation.year,
                    agent.date_affectation.month,
                    agent.date_affectation.day,
                ))

    # ====================================================================
    def _on_generate(self):
        if not self.agent:
            QMessageBox.warning(self, "Agent requis",
                                "Veuillez d'abord identifier l'agent demandeur.")
            return

        # Récupérer les vœux saisis
        voeux = []
        for v in self.voeux_inputs:
            drenaet = v["drenaet"].text().strip()
            iepp = v["iepp"].text().strip()
            if drenaet or iepp:
                voeux.append({
                    "drenaet": drenaet or "—",
                    "iepp": iepp or "—",
                })

        # Vérifier qu'au moins 1 vœu est complet
        if not voeux:
            QMessageBox.warning(self, "Vœu requis",
                                "Veuillez saisir au moins un vœu de mutation "
                                "(DRENAET souhaitée et/ou IEPP souhaitée).")
            return

        # Vérifier que le 1er vœu est complet (DRENAET ET IEPP)
        v1 = self.voeux_inputs[0]
        if not v1["drenaet"].text().strip() or not v1["iepp"].text().strip():
            QMessageBox.warning(self, "Premier vœu incomplet",
                                "Le premier vœu doit avoir à la fois "
                                "une DRENAET souhaitée ET une IEPP souhaitée.")
            return

        parameters = {
            "date_entree_fp": self.date_entree_fp.date().toPyDate(),
            "date_entree_drenaet": self.date_entree_drenaet.date().toPyDate(),
            "date_fonction_actuelle": self.date_fonction_actuelle.date().toPyDate(),
            "date_retraite": self.date_retraite.date().toPyDate(),
            "voeux": voeux,
        }

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Génération en cours...")

        try:
            session = UserSession.get_instance()
            generator = DocumentGenerator()
            pdf_path, numero = generator.generate(
                template=FicheMutationTemplate(),
                personnel_id=self.agent["id"],
                parameters=parameters,
                user_login=session.login or "user",
            )

            reply = QMessageBox.information(
                self, "Document généré",
                f"<b>Fiche de Mutation créée !</b><br/><br/>"
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
            self.gen_btn.setText("  GÉNÉRER LA FICHE DE MUTATION")

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
                                f"Le PDF a été créé.\n\nChemin : {path}")

    def _reset_form(self):
        self.agent = None
        self.agent_card.mat_input.clear()
        self.agent_card.info_label.setText("Saisissez un matricule puis cliquez sur Rechercher")
        self.agent_card.info_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-style: italic; padding: 8px;"
        )
        for v in self.voeux_inputs:
            v["drenaet"].clear()
            v["iepp"].clear()