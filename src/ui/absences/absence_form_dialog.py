"""
========================================================================
DRENAET-RH — AbsenceFormDialog (popup ajout/modification absence)
========================================================================
Popup pour saisir manuellement une absence (hors génération de document).

Modes :
- CREATE : absence_id=None
- EDIT   : absence_id=int (pré-remplissage)

Affiche en temps réel :
- Le nombre de jours ouvrés calculé
- Une alerte si le quota de congé annuel est dépassé
"""

from datetime import date, datetime
from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QDateEdit, QTextEdit, QPushButton, QFrame,
    QMessageBox, QWidget, QLineEdit, QCompleter,
)

from src.services.absence_service import (
    AbsenceService, AbsenceException, DatesInvalidesError, AbsenceIntrouvableError,
)
from src.models.absence import TYPES_ABSENCE, TYPES_AVEC_QUOTA
from src.services.personnel_service import PersonnelService
from src.services.auth_service import UserSession


class AbsenceFormDialog(QDialog):
    """Popup ajout / modification d'une absence."""

    def __init__(self, absence_id: Optional[int] = None, personnel_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.absence_id = absence_id
        self.is_edit_mode = absence_id is not None
        self.preselected_personnel_id = personnel_id
        self.selected_agent: Optional[dict] = None

        title = "Modifier une absence" if self.is_edit_mode else "Nouvelle absence"
        self.setWindowTitle(title)
        self.resize(560, 620)
        self.setStyleSheet("background-color: #F8FAFC;")
        self.setModal(True)

        self._build_ui()

        if self.is_edit_mode:
            self._load_absence()
        elif self.preselected_personnel_id:
            self._preselect_agent(self.preselected_personnel_id)

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(self._build_agent_section())
        layout.addWidget(self._build_details_section())

        # Zone d'alerte quota (cachée par défaut)
        self.quota_alert = QLabel()
        self.quota_alert.setWordWrap(True)
        self.quota_alert.hide()
        layout.addWidget(self.quota_alert)

        layout.addStretch()
        outer.addWidget(content, stretch=1)
        outer.addWidget(self._build_buttons_bar())

    def _build_header(self) -> QFrame:
        frame = QFrame()
        color = "#3B82F6" if self.is_edit_mode else "#F59E0B"
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 #4338CA);
            }}
        """)
        frame.setFixedHeight(64)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            qta.icon("fa5s.calendar-times", color="#FFFFFF").pixmap(QSize(28, 28))
        )
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        title = QLabel("Modifier une absence" if self.is_edit_mode else "Nouvelle absence")
        title.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        layout.addWidget(title)
        layout.addStretch()
        return frame

    # ====================================================================
    def _build_agent_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Agent concerné")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 12px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        self.matricule_input = QLineEdit()
        self.matricule_input.setPlaceholderText("Matricule de l'agent (Ex: 233329C)")
        self.matricule_input.setMinimumHeight(36)
        self.matricule_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #4338CA; }
        """)
        search_layout.addWidget(self.matricule_input, stretch=1)

        search_btn = QPushButton("  Rechercher")
        search_btn.setIcon(qta.icon("fa5s.search", color="#FFFFFF"))
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedHeight(36)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        search_btn.clicked.connect(self._on_search_agent)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.agent_info_label = QLabel("Aucun agent sélectionné.")
        self.agent_info_label.setStyleSheet(
            "color: #94A3B8; font-size: 11px; font-style: italic; background: transparent;"
        )
        self.agent_info_label.setWordWrap(True)
        layout.addWidget(self.agent_info_label)

        return frame

    def _build_details_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Détails de l'absence")
        title.setStyleSheet(
            "color: #1E1B4B; font-size: 12px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Type d'absence
        type_lbl = QLabel("Type d'absence *")
        type_lbl.setStyleSheet("color: #1E1B4B; font-size: 11px; font-weight: bold; background: transparent;")
        grid.addWidget(type_lbl, 0, 0)

        self.type_combo = QComboBox()
        self.type_combo.addItems(TYPES_ABSENCE)
        self.type_combo.setMinimumHeight(34)
        self.type_combo.setStyleSheet(self._input_style())
        grid.addWidget(self.type_combo, 1, 0, 1, 2)

        # Date début
        debut_lbl = QLabel("Date de début *")
        debut_lbl.setStyleSheet("color: #1E1B4B; font-size: 11px; font-weight: bold; background: transparent;")
        grid.addWidget(debut_lbl, 2, 0)

        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        self.date_debut.setDisplayFormat("dd/MM/yyyy")
        self.date_debut.setMinimumHeight(34)
        self.date_debut.setStyleSheet(self._input_style())
        self.date_debut.dateChanged.connect(self._on_dates_changed)
        grid.addWidget(self.date_debut, 3, 0)

        # Date fin
        fin_lbl = QLabel("Date de fin *")
        fin_lbl.setStyleSheet("color: #1E1B4B; font-size: 11px; font-weight: bold; background: transparent;")
        grid.addWidget(fin_lbl, 2, 1)

        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addDays(5))
        self.date_fin.setDisplayFormat("dd/MM/yyyy")
        self.date_fin.setMinimumHeight(34)
        self.date_fin.setStyleSheet(self._input_style())
        self.date_fin.dateChanged.connect(self._on_dates_changed)
        grid.addWidget(self.date_fin, 3, 1)

        layout.addLayout(grid)

        # Compteur de jours ouvrés (dynamique)
        self.jours_label = QLabel()
        self.jours_label.setStyleSheet("""
            QLabel {
                background-color: #EEF2FF;
                color: #4338CA;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.jours_label)

        # Motif
        motif_lbl = QLabel("Motif")
        motif_lbl.setStyleSheet("color: #1E1B4B; font-size: 11px; font-weight: bold; background: transparent;")
        layout.addWidget(motif_lbl)

        self.motif_input = QTextEdit()
        self.motif_input.setPlaceholderText("Précisez le motif de l'absence (optionnel)...")
        self.motif_input.setFixedHeight(70)
        self.motif_input.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus { border-color: #4338CA; }
        """)
        layout.addWidget(self.motif_input)

        self._on_dates_changed()  # calcul initial
        return frame

    def _input_style(self) -> str:
        return """
            QComboBox, QDateEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QComboBox:focus, QDateEdit:focus { border-color: #4338CA; }
        """

    def _build_buttons_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-top: 1px solid #E2E8F0; }
        """)
        bar.setFixedHeight(60)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)

        cancel_btn = QPushButton("  Annuler")
        cancel_btn.setIcon(qta.icon("fa5s.times", color="#64748B"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9; color: #64748B;
                border: 1px solid #E2E8F0; border-radius: 6px;
                padding: 0 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        layout.addStretch()

        save_label = "Enregistrer" if self.is_edit_mode else "Créer l'absence"
        save_btn = QPushButton(f"  {save_label}")
        save_btn.setIcon(qta.icon("fa5s.check", color="#FFFFFF"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B; color: #FFFFFF;
                border: none; border-radius: 6px;
                padding: 0 18px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #D97706; }
        """)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)
        return bar

    # ====================================================================
    def _on_search_agent(self):
        matricule = self.matricule_input.text().strip().upper()
        if not matricule:
            QMessageBox.warning(self, "Champ requis", "Veuillez saisir un matricule.")
            return
        agent = PersonnelService.get_by_matricule(matricule)
        if not agent:
            QMessageBox.warning(
                self, "Introuvable",
                f"Aucun agent trouvé avec le matricule '{matricule}'.",
            )
            return
        self._set_agent(agent)

    def _preselect_agent(self, personnel_id: int):
        agent = PersonnelService.get_by_id(personnel_id)
        if agent:
            self._set_agent(agent)

    def _set_agent(self, agent: dict):
        self.selected_agent = agent
        self.matricule_input.setText(agent["matricule"])
        self.agent_info_label.setText(
            f"<b style='color:#1E1B4B;'>{agent['nom_complet']}</b> — "
            f"{agent.get('emploi', '')} @ {agent.get('structure_nom', '?')}"
        )
        self.agent_info_label.setStyleSheet(
            "color: #10B981; font-size: 11px; background: transparent;"
        )
        self._on_dates_changed()  # recalculer le quota avec l'agent choisi

    # ====================================================================
    def _on_dates_changed(self):
        """Recalcule le nombre de jours ouvrés + vérifie le quota."""
        d_debut = self.date_debut.date().toPyDate()
        d_fin = self.date_fin.date().toPyDate()

        if d_fin < d_debut:
            self.jours_label.setText("⚠ La date de fin doit être après la date de début.")
            self.jours_label.setStyleSheet("""
                QLabel { background-color: #FEE2E2; color: #DC2626;
                border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold; }
            """)
            self.quota_alert.hide()
            return

        nb_jours = AbsenceService.count_business_days(d_debut, d_fin)
        self.jours_label.setText(f"📅 {nb_jours} jour(s) ouvré(s) (weekends exclus)")
        self.jours_label.setStyleSheet("""
            QLabel { background-color: #EEF2FF; color: #4338CA;
            border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold; }
        """)

        # Vérifier quota si type = Congé annuel et agent sélectionné
        type_absence = self.type_combo.currentText()
        if type_absence in TYPES_AVEC_QUOTA and self.selected_agent:
            try:
                status = AbsenceService.get_quota_status(
                    self.selected_agent["id"], annee=d_debut.year
                )
                projection = status["jours_pris"] + nb_jours
                if self.is_edit_mode:
                    # En mode édition, ne pas double-compter l'absence existante
                    pass

                if projection > status["quota_total"]:
                    self.quota_alert.setText(
                        f"⚠ <b>Attention : dépassement du quota de congés annuels.</b><br/>"
                        f"Cet agent a déjà pris <b>{status['jours_pris']}</b> jour(s) sur "
                        f"{status['quota_total']} en {status['annee']}. "
                        f"Avec cette nouvelle demande de {nb_jours} jour(s), le total "
                        f"passerait à <b>{projection}</b> jours "
                        f"({projection - status['quota_total']} jour(s) de dépassement)."
                    )
                    self.quota_alert.setStyleSheet("""
                        QLabel { background-color: #FEF3C7; color: #92400E;
                        border: 1px solid #FBBF24; border-radius: 6px; padding: 12px; }
                    """)
                    self.quota_alert.show()
                else:
                    self.quota_alert.hide()
            except Exception:
                self.quota_alert.hide()
        else:
            self.quota_alert.hide()

    # ====================================================================
    def _load_absence(self):
        """Mode édition : charge l'absence existante."""
        absence = AbsenceService.get_by_id(self.absence_id)
        if not absence:
            QMessageBox.critical(self, "Erreur", "Absence introuvable.")
            self.reject()
            return

        agent = PersonnelService.get_by_id(absence["personnel_id"])
        if agent:
            self._set_agent(agent)

        idx = self.type_combo.findText(absence["type_absence"])
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        d_debut = datetime.fromisoformat(absence["date_debut"]).date()
        d_fin = datetime.fromisoformat(absence["date_fin"]).date()
        self.date_debut.setDate(QDate(d_debut.year, d_debut.month, d_debut.day))
        self.date_fin.setDate(QDate(d_fin.year, d_fin.month, d_fin.day))

        self.motif_input.setPlainText(absence.get("motif") or "")

    # ====================================================================
    def _on_save(self):
        if not self.selected_agent:
            QMessageBox.warning(self, "Agent requis", "Veuillez sélectionner un agent.")
            return

        d_debut = self.date_debut.date().toPyDate()
        d_fin = self.date_fin.date().toPyDate()
        if d_fin < d_debut:
            QMessageBox.warning(self, "Dates invalides", "La date de fin doit être après la date de début.")
            return

        data = {
            "personnel_id": self.selected_agent["id"],
            "type_absence": self.type_combo.currentText(),
            "date_debut": d_debut,
            "date_fin": d_fin,
            "motif": self.motif_input.toPlainText().strip() or None,
        }

        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"

            if self.is_edit_mode:
                AbsenceService.update(self.absence_id, data)
                QMessageBox.information(self, "Succès", "Absence modifiée avec succès.")
            else:
                result = AbsenceService.create(data, user_login=user_login, source="MANUAL")
                msg = "Absence enregistrée avec succès."
                if result.get("quota_warning"):
                    msg += (
                        f"\n\n⚠ Attention : le quota de congés annuels est dépassé "
                        f"({result['quota_status']['jours_pris']}/{result['quota_status']['quota_total']} jours)."
                    )
                QMessageBox.information(self, "Succès", msg)

            self.accept()

        except (AbsenceException, DatesInvalidesError, AbsenceIntrouvableError) as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Enregistrement échoué :\n{e}")