"""
========================================================================
DRENAET-RH — PersonnelFormDialog (popup ajout / modification agent)
========================================================================
Popup unifiée pour créer un nouvel agent OU en modifier un existant.

Modes :
- CREATE : agent_id=None → tous les champs vides, bouton "Créer"
- EDIT   : agent_id=int → pré-remplissage + bouton "Enregistrer"

Design :
- Sections organisées (Identité / Contact / Carrière)
- Champs obligatoires marqués d'un astérisque rouge
- Validation en temps réel
- Combo box pour structures (chargée depuis BD + option "Nouvelle...")
"""

from datetime import date, datetime
from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QDateEdit, QPushButton, QFrame,
    QScrollArea, QMessageBox, QWidget, QInputDialog,
)

from src.ui.widgets.icon_label import IconLabel
from src.services.personnel_service import (
    PersonnelService, MatriculeExistantError,
    ChampObligatoireError, AgentIntrouvableError,
    StructureInvalideError,
)
from src.services.structure_service import (
    StructureService, TYPES_STRUCTURE, NomStructureExistantError,
)
from src.services.auth_service import UserSession


class PersonnelFormDialog(QDialog):
    """Popup ajout / modification d'un agent."""

    def __init__(self, agent_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.is_edit_mode = agent_id is not None
        self.agent_data: Optional[dict] = None

        title = "Modifier un agent" if self.is_edit_mode else "Ajouter un nouvel agent"
        self.setWindowTitle(title)
        self.resize(720, 780)
        self.setStyleSheet("background-color: #F8FAFC;")
        self.setModal(True)

        self._build_ui()

        # Si mode édition, charger les données
        if self.is_edit_mode:
            self._load_agent()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # === Header ===
        outer.addWidget(self._build_header())

        # === Scroll zone (formulaire) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 3 sections
        layout.addWidget(self._build_identite_section())
        layout.addWidget(self._build_contact_section())
        layout.addWidget(self._build_carriere_section())

        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # === Barre de boutons en bas ===
        outer.addWidget(self._build_buttons_bar())

    def _build_header(self) -> QFrame:
        frame = QFrame()
        color = "#3B82F6" if self.is_edit_mode else "#10B981"
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 #4338CA);
                border: none;
            }}
        """)
        frame.setFixedHeight(72)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        icon_lbl = QLabel()
        icon_name = "fa5s.user-edit" if self.is_edit_mode else "fa5s.user-plus"
        icon_lbl.setPixmap(qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(36, 36)))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(
            "Modifier un agent" if self.is_edit_mode else "Nouvel agent"
        )
        title.setStyleSheet(
            "color: #FFFFFF; font-size: 18px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        text_layout.addWidget(title)

        subtitle = QLabel(
            "Modifiez les informations de l'agent"
            if self.is_edit_mode
            else "Renseignez les informations du nouvel agent"
        )
        subtitle.setStyleSheet(
            "color: #FFFFFF; font-size: 12px; background: transparent; border: none;"
        )
        text_layout.addWidget(subtitle)

        layout.addLayout(text_layout, stretch=1)
        return frame

    # ====================================================================
    def _build_section_frame(self, title: str, icon_name: str) -> tuple:
        """Crée un frame de section (retourne frame + inner_layout)."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # Titre de section
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color="#4338CA").pixmap(QSize(16, 16)))
        icon.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Grille des champs
        grid = QGridLayout()
        grid.setSpacing(12)
        layout.addLayout(grid)

        return frame, grid

    def _add_field_to_grid(
        self,
        grid: QGridLayout,
        row: int,
        col: int,
        label: str,
        widget,
        required: bool = False,
        colspan: int = 1,
    ):
        """Ajoute un champ (label + widget) à une grille."""
        label_text = f"{label} <span style='color:#DC2626;'>*</span>" if required else label

        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)

        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)
        wrapper.addWidget(lbl)
        wrapper.addWidget(widget)

        # QGridLayout ne peut pas contenir de layout directement, wrap dans widget
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(wrapper)
        grid.addWidget(w, row, col, 1, colspan)

    def _make_input(self, placeholder: str = "") -> QLineEdit:
        """Crée un QLineEdit stylisé."""
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(34)
        inp.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QLineEdit:focus { border-color: #4338CA; }
        """)
        return inp

    def _make_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(34)
        combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QComboBox:focus { border-color: #4338CA; }
        """)
        return combo

    def _make_date(self) -> QDateEdit:
        d = QDateEdit()
        d.setCalendarPopup(True)
        d.setDate(QDate.currentDate())
        d.setDisplayFormat("dd/MM/yyyy")
        d.setSpecialValueText(" ")  # affiche vide si date min
        d.setMinimumHeight(34)
        d.setMinimumDate(QDate(1900, 1, 1))
        d.setStyleSheet("""
            QDateEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                color: #1E1B4B;
            }
            QDateEdit:focus { border-color: #4338CA; }
        """)
        return d

    # ====================================================================
    # SECTION 1 : IDENTITÉ
    # ====================================================================
    def _build_identite_section(self) -> QFrame:
        frame, grid = self._build_section_frame("Identité", "fa5s.id-card")

        # Matricule (obligatoire, disabled en mode edit)
        self.matricule_input = self._make_input("Ex : 233329C")
        if self.is_edit_mode:
            self.matricule_input.setEnabled(False)
            self.matricule_input.setStyleSheet(
                self.matricule_input.styleSheet()
                + "\nQLineEdit:disabled { background-color: #F1F5F9; color: #94A3B8; }"
            )
        self._add_field_to_grid(grid, 0, 0, "Matricule", self.matricule_input, required=True)

        # Sexe (obligatoire)
        self.sexe_combo = self._make_combo()
        self.sexe_combo.addItems(["", "M", "F"])
        self._add_field_to_grid(grid, 0, 1, "Sexe", self.sexe_combo, required=True)

        # Nom (obligatoire)
        self.nom_input = self._make_input("Ex : BABO")
        self._add_field_to_grid(grid, 1, 0, "Nom", self.nom_input, required=True)

        # Prénoms (obligatoire)
        self.prenoms_input = self._make_input("Ex : Assomane David")
        self._add_field_to_grid(grid, 1, 1, "Prénoms", self.prenoms_input, required=True)

        # Date de naissance (optionnelle)
        self.date_naissance = self._make_date()
        self.date_naissance.setDate(QDate(2000, 1, 1))
        self._add_field_to_grid(grid, 2, 0, "Date de naissance", self.date_naissance)

        # Lieu de naissance
        self.lieu_naissance_input = self._make_input("Ex : Katiola")
        self._add_field_to_grid(grid, 2, 1, "Lieu de naissance", self.lieu_naissance_input)

        # Situation matrimoniale
        self.sit_matri_combo = self._make_combo()
        self.sit_matri_combo.addItems([
            "", "Célibataire", "Marié(e)", "Divorcé(e)", "Veuf(ve)",
        ])
        self._add_field_to_grid(grid, 3, 0, "Situation matrimoniale", self.sit_matri_combo, colspan=2)

        return frame

    # ====================================================================
    # SECTION 2 : CONTACT
    # ====================================================================
    def _build_contact_section(self) -> QFrame:
        frame, grid = self._build_section_frame("Contact", "fa5s.address-book")

        # Téléphone
        self.telephone_input = self._make_input("Ex : 07 07 07 07 07")
        self._add_field_to_grid(grid, 0, 0, "Téléphone", self.telephone_input)

        # Email
        self.email_input = self._make_input("Ex : agent@drenaet-kla.ci")
        self._add_field_to_grid(grid, 0, 1, "Email", self.email_input)

        # Résidence
        self.residence_input = self._make_input("Ex : Katiola")
        self._add_field_to_grid(grid, 1, 0, "Résidence", self.residence_input, colspan=2)

        return frame

    # ====================================================================
    # SECTION 3 : CARRIÈRE
    # ====================================================================
    def _build_carriere_section(self) -> QFrame:
        frame, grid = self._build_section_frame("Carrière & Affectation", "fa5s.briefcase")

        # Emploi (obligatoire)
        self.emploi_input = self._make_input("Ex : Inspecteur Principal")
        self._add_field_to_grid(grid, 0, 0, "Emploi", self.emploi_input, required=True)

        # Grade
        self.grade_input = self._make_input("Ex : A4")
        self._add_field_to_grid(grid, 0, 1, "Grade", self.grade_input)

        # Fonction
        self.fonction_input = self._make_input("Ex : Directeur du CAFOP Katiola")
        self._add_field_to_grid(grid, 1, 0, "Fonction", self.fonction_input, colspan=2)

        # Structure (obligatoire) — combo + bouton "Nouvelle..."
        struct_widget = QWidget()
        struct_widget.setStyleSheet("background: transparent;")
        struct_layout = QHBoxLayout(struct_widget)
        struct_layout.setContentsMargins(0, 0, 0, 0)
        struct_layout.setSpacing(6)

        self.structure_combo = self._make_combo()
        self._load_structures()
        struct_layout.addWidget(self.structure_combo, stretch=1)

        new_struct_btn = QPushButton()
        new_struct_btn.setIcon(qta.icon("fa5s.plus", color="#FFFFFF"))
        new_struct_btn.setToolTip("Créer une nouvelle structure")
        new_struct_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_struct_btn.setFixedSize(34, 34)
        new_struct_btn.setStyleSheet("""
            QPushButton {
                background-color: #4338CA;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        new_struct_btn.clicked.connect(self._on_new_structure)
        struct_layout.addWidget(new_struct_btn)

        self._add_field_to_grid(grid, 2, 0, "Structure (établissement)", struct_widget, required=True, colspan=2)

        # Date prise de service
        self.date_prise = self._make_date()
        self._add_field_to_grid(grid, 3, 0, "Date de prise de service", self.date_prise)

        # Date affectation
        self.date_affectation = self._make_date()
        self._add_field_to_grid(grid, 3, 1, "Date d'affectation", self.date_affectation)

        # Statut
        self.statut_combo = self._make_combo()
        self.statut_combo.addItems([
            "Actif", "Inactif", "En congé", "Muté", "Retraité",
        ])
        self._add_field_to_grid(grid, 4, 0, "Statut", self.statut_combo, colspan=2)

        return frame

    def _load_structures(self):
        """Charge les structures depuis la BD dans le combo."""
        self.structure_combo.clear()
        try:
            structures = StructureService.list_all()
            self.structure_combo.addItem("— Sélectionner une structure —", userData=None)
            for s in structures:
                display = f"{s['nom']} ({s.get('type') or 'Autre'})"
                self.structure_combo.addItem(display, userData=s["id"])
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de charger les structures : {e}")

    def _on_new_structure(self):
        """Ouvre un dialogue rapide pour créer une nouvelle structure."""
        nom, ok = QInputDialog.getText(
            self,
            "Nouvelle structure",
            "Nom de la structure :",
            text="",
        )
        if not ok or not nom.strip():
            return

        type_struct, ok = QInputDialog.getItem(
            self,
            "Type de structure",
            f"Type de '{nom.strip()}' :",
            TYPES_STRUCTURE,
            editable=False,
        )
        if not ok:
            return

        localite, _ = QInputDialog.getText(
            self,
            "Localité",
            "Localité (optionnel) :",
            text="Katiola",
        )

        try:
            new_struct = StructureService.create({
                "nom": nom.strip(),
                "type": type_struct,
                "localite": localite.strip() if localite else None,
            })
            self._load_structures()
            # Sélectionner la nouvelle structure
            for i in range(self.structure_combo.count()):
                if self.structure_combo.itemData(i) == new_struct["id"]:
                    self.structure_combo.setCurrentIndex(i)
                    break
            QMessageBox.information(self, "Succès", f"Structure '{nom}' créée.")
        except NomStructureExistantError as e:
            QMessageBox.warning(self, "Doublon", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée : {e}")

    # ====================================================================
    # BARRE DE BOUTONS
    # ====================================================================
    def _build_buttons_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E2E8F0;
            }
        """)
        bar.setFixedHeight(64)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)

        cancel_btn = QPushButton("  Annuler")
        cancel_btn.setIcon(qta.icon("fa5s.times", color="#64748B"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(140)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        layout.addStretch()

        save_label = "Enregistrer" if self.is_edit_mode else "Créer l'agent"
        save_icon = "fa5s.save" if self.is_edit_mode else "fa5s.check"
        save_color = "#3B82F6" if self.is_edit_mode else "#10B981"

        save_btn = QPushButton(f"  {save_label}")
        save_btn.setIcon(qta.icon(save_icon, color="#FFFFFF"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(40)
        save_btn.setMinimumWidth(180)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {save_color};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3730A3; }}
        """)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        return bar

    # ====================================================================
    def _load_agent(self):
        """Charge un agent existant dans le formulaire (mode EDIT)."""
        agent = PersonnelService.get_by_id(self.agent_id)
        if not agent:
            QMessageBox.critical(self, "Erreur", "Agent introuvable.")
            self.reject()
            return
        self.agent_data = agent

        # Remplir les champs
        self.matricule_input.setText(agent.get("matricule") or "")
        self.nom_input.setText(agent.get("nom") or "")
        self.prenoms_input.setText(agent.get("prenoms") or "")

        sexe = agent.get("sexe") or ""
        idx = self.sexe_combo.findText(sexe)
        if idx >= 0:
            self.sexe_combo.setCurrentIndex(idx)

        if agent.get("date_naissance"):
            self._set_date_from_iso(self.date_naissance, agent["date_naissance"])

        self.lieu_naissance_input.setText(agent.get("lieu_naissance") or "")

        sit_matri = agent.get("situation_matrimoniale") or ""
        idx = self.sit_matri_combo.findText(sit_matri)
        if idx >= 0:
            self.sit_matri_combo.setCurrentIndex(idx)

        self.telephone_input.setText(agent.get("telephone") or "")
        self.email_input.setText(agent.get("email") or "")
        self.residence_input.setText(agent.get("residence") or "")

        self.emploi_input.setText(agent.get("emploi") or "")
        self.grade_input.setText(agent.get("grade") or "")
        self.fonction_input.setText(agent.get("fonction") or "")

        # Structure : sélectionner par ID
        struct_id = agent.get("structure_id")
        if struct_id is not None:
            for i in range(self.structure_combo.count()):
                if self.structure_combo.itemData(i) == struct_id:
                    self.structure_combo.setCurrentIndex(i)
                    break

        if agent.get("date_prise_service"):
            self._set_date_from_iso(self.date_prise, agent["date_prise_service"])
        if agent.get("date_affectation"):
            self._set_date_from_iso(self.date_affectation, agent["date_affectation"])

        statut = agent.get("statut") or "Actif"
        idx = self.statut_combo.findText(statut)
        if idx >= 0:
            self.statut_combo.setCurrentIndex(idx)

    def _set_date_from_iso(self, widget: QDateEdit, iso_str: str):
        """Convertit un ISO string en QDate."""
        try:
            d = datetime.fromisoformat(iso_str).date()
            widget.setDate(QDate(d.year, d.month, d.day))
        except (ValueError, TypeError):
            pass

    # ====================================================================
    def _on_save(self):
        """Valide le formulaire et enregistre l'agent."""
        # Récupérer les données
        data = self._collect_data()

        # Vérifications minimales côté UI (le service revalide en profondeur)
        if not data["matricule"]:
            QMessageBox.warning(self, "Champ manquant", "Le matricule est obligatoire.")
            self.matricule_input.setFocus()
            return
        if not data["nom"]:
            QMessageBox.warning(self, "Champ manquant", "Le nom est obligatoire.")
            self.nom_input.setFocus()
            return
        if not data["prenoms"]:
            QMessageBox.warning(self, "Champ manquant", "Les prénoms sont obligatoires.")
            self.prenoms_input.setFocus()
            return
        if not data["sexe"]:
            QMessageBox.warning(self, "Champ manquant", "Le sexe est obligatoire.")
            self.sexe_combo.setFocus()
            return
        if not data["emploi"]:
            QMessageBox.warning(self, "Champ manquant", "L'emploi est obligatoire.")
            self.emploi_input.setFocus()
            return
        if data["structure_id"] is None:
            QMessageBox.warning(
                self, "Champ manquant",
                "Vous devez sélectionner une structure. Utilisez le bouton + pour en créer une.",
            )
            self.structure_combo.setFocus()
            return

        # Appel du service
        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"
            user_role = session.role if session.is_authenticated else None

            if self.is_edit_mode:
                PersonnelService.update(
                    agent_id=self.agent_id,
                    data=data,
                    user_login=user_login,
                    user_role=user_role,
                    commentaire="Modification via UI",
                )
                QMessageBox.information(
                    self, "Succès",
                    f"L'agent {data['matricule']} a été modifié.",
                )
            else:
                PersonnelService.create(
                    data=data,
                    user_login=user_login,
                    user_role=user_role,
                    commentaire="Création via UI",
                )
                QMessageBox.information(
                    self, "Succès",
                    f"L'agent {data['matricule']} a été créé.",
                )

            self.accept()

        except MatriculeExistantError as e:
            QMessageBox.warning(self, "Matricule déjà utilisé", str(e))
        except ChampObligatoireError as e:
            QMessageBox.warning(self, "Champ obligatoire", str(e))
        except StructureInvalideError as e:
            QMessageBox.warning(self, "Structure invalide", str(e))
        except AgentIntrouvableError as e:
            QMessageBox.critical(self, "Agent introuvable", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Enregistrement échoué :\n{e}")

    def _collect_data(self) -> dict:
        """Collecte les données du formulaire."""
        struct_id = self.structure_combo.currentData()

        return {
            "matricule": self.matricule_input.text().strip().upper(),
            "nom": self.nom_input.text().strip().upper(),
            "prenoms": self.prenoms_input.text().strip(),
            "sexe": self.sexe_combo.currentText().strip(),
            "date_naissance": self.date_naissance.date().toPyDate(),
            "lieu_naissance": self.lieu_naissance_input.text().strip() or None,
            "situation_matrimoniale": self.sit_matri_combo.currentText().strip() or None,
            "telephone": self.telephone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "residence": self.residence_input.text().strip() or None,
            "emploi": self.emploi_input.text().strip(),
            "grade": self.grade_input.text().strip() or None,
            "fonction": self.fonction_input.text().strip() or None,
            "structure_id": struct_id,
            "date_prise_service": self.date_prise.date().toPyDate(),
            "date_affectation": self.date_affectation.date().toPyDate(),
            "statut": self.statut_combo.currentText().strip(),
        }