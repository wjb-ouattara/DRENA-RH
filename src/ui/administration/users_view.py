"""
========================================================================
DRENAET-RH — UsersView (gestion des comptes utilisateurs)
========================================================================
Vue Administration > Utilisateurs.

Fonctionnalités :
- Table de tous les comptes (login, nom, rôle, statut)
- Créer un nouvel utilisateur (popup)
- Modifier nom/rôle
- Réinitialiser le mot de passe
- Activer/désactiver un compte
- Supprimer (avec protection anti-auto-suppression)
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QDialog, QLineEdit,
    QComboBox, QGridLayout,
)

from src.services.user_service import (
    UserService, UserServiceException, LoginExistantError,
    UtilisateurIntrouvableError, ChampObligatoireError,
    SchemaUtilisateurInconnuError,
)
from src.services.auth_service import UserSession


ROLE_LABELS = {"admin": "Administrateur", "operateur": "Opérateur"}
ROLE_COLORS = {"admin": "#DC2626", "operateur": "#3B82F6"}


class UsersView(QWidget):
    """Vue de gestion des utilisateurs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # ====================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        layout.addWidget(self._build_header())

        self.table = self._build_table()
        layout.addWidget(self.table, stretch=1)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title = QLabel("Gestion des utilisateurs")
        title.setStyleSheet("color: #1E1B4B; font-size: 20px; font-weight: bold; background: transparent;")
        title_col.addWidget(title)

        self.total_lbl = QLabel("Chargement...")
        self.total_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        title_col.addWidget(self.total_lbl)
        layout.addLayout(title_col)

        layout.addStretch()

        new_btn = QPushButton("  Nouvel utilisateur")
        new_btn.setIcon(qta.icon("fa5s.user-plus", color="#FFFFFF"))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setFixedHeight(40)
        new_btn.setStyleSheet("""
            QPushButton { background-color: #4338CA; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 0 18px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #3730A3; }
        """)
        new_btn.clicked.connect(self._on_new_user)
        layout.addWidget(new_btn)

        return w

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Login", "Nom complet", "Rôle", "Statut", "Actions"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 8px; gridline-color: #F1F5F9; font-size: 12px; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section { background-color: #F1F5F9; color: #1E1B4B;
            padding: 10px; border: none; border-right: 1px solid #E2E8F0;
            font-weight: bold; font-size: 11px; }
        """)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 150)
        table.setColumnWidth(1, 220)
        table.setColumnWidth(2, 140)
        table.setColumnWidth(3, 110)
        table.verticalHeader().setDefaultSectionSize(46)
        return table

    # ====================================================================
    def refresh(self):
        # Garde défensive : aucune liste de comptes ne doit être chargée pour
        # un utilisateur non administrateur, même si la vue était atteinte.
        if not UserSession.get_instance().is_admin:
            self.total_lbl.setText("Accès réservé à l'Administrateur")
            self._fill_table([])
            return

        try:
            users = UserService.list_all()
        except SchemaUtilisateurInconnuError as e:
            QMessageBox.critical(
                self, "Configuration requise",
                f"{e}\n\nCe module a besoin d'un petit ajustement pour "
                f"correspondre exactement à ton modèle Utilisateur.",
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement échoué :\n{e}")
            return

        self.total_lbl.setText(f"{len(users)} utilisateur(s)")
        self._fill_table(users)

    def _fill_table(self, users: list):
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(u.get("login") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(u.get("nom_complet") or ""))

            role = u.get("role") or "?"
            role_item = QTableWidgetItem(ROLE_LABELS.get(role, role))
            role_item.setForeground(QColor(ROLE_COLORS.get(role, "#64748B")))
            self.table.setItem(row, 2, role_item)

            actif = u.get("actif", True)
            statut_item = QTableWidgetItem("Actif" if actif else "Désactivé")
            statut_item.setForeground(QColor("#10B981" if actif else "#94A3B8"))
            self.table.setItem(row, 3, statut_item)

            self.table.setCellWidget(row, 4, self._build_actions_cell(u))

    def _build_actions_cell(self, user: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#3B82F6"))
        edit_btn.setToolTip("Modifier")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #DBEAFE; }")
        edit_btn.clicked.connect(lambda: self._on_edit(user))
        layout.addWidget(edit_btn)

        pwd_btn = QPushButton()
        pwd_btn.setIcon(qta.icon("fa5s.key", color="#F59E0B"))
        pwd_btn.setToolTip("Réinitialiser le mot de passe")
        pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pwd_btn.setFixedSize(30, 30)
        pwd_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #FEF3C7; }")
        pwd_btn.clicked.connect(lambda: self._on_reset_password(user))
        layout.addWidget(pwd_btn)

        toggle_btn = QPushButton()
        is_actif = user.get("actif", True)
        toggle_btn.setIcon(qta.icon("fa5s.user-slash" if is_actif else "fa5s.user-check",
                                     color="#DC2626" if is_actif else "#10B981"))
        toggle_btn.setToolTip("Désactiver" if is_actif else "Activer")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setFixedSize(30, 30)
        toggle_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #F1F5F9; }")
        toggle_btn.clicked.connect(lambda: self._on_toggle_actif(user))
        layout.addWidget(toggle_btn)

        del_btn = QPushButton()
        del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#DC2626"))
        del_btn.setToolTip("Supprimer")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background-color: #FEE2E2; }")
        del_btn.clicked.connect(lambda: self._on_delete(user))
        layout.addWidget(del_btn)

        return w

    # ====================================================================
    def _on_new_user(self):
        dialog = UserFormDialog(parent=self)
        if dialog.exec():
            self.refresh()

    def _on_edit(self, user: dict):
        dialog = UserFormDialog(user_data=user, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_reset_password(self, user: dict):
        dialog = ResetPasswordDialog(user, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_toggle_actif(self, user: dict):
        try:
            UserService.toggle_actif(user["id"])
            self.refresh()
        except UserServiceException as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _on_delete(self, user: dict):
        session = UserSession.get_instance()
        current_login = session.login if session.is_authenticated else None

        if user.get("role") == "admin" and UserService.count_admins() <= 1:
            QMessageBox.warning(
                self, "Suppression bloquée",
                "Impossible de supprimer le dernier administrateur : "
                "cela verrouillerait l'accès à l'administration.",
            )
            return

        reply = QMessageBox.warning(
            self, "Confirmer la suppression",
            f"<b>Supprimer l'utilisateur '{user['login']}' ?</b><br/><br/>"
            f"Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            UserService.delete(user["id"], current_user_login=current_login)
            self.refresh()
        except UserServiceException as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


# ========================================================================
# POPUP CRÉATION / MODIFICATION
# ========================================================================
class UserFormDialog(QDialog):
    """Popup ajout / modification d'un utilisateur."""

    def __init__(self, user_data: dict = None, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.is_edit_mode = user_data is not None

        self.setWindowTitle("Modifier un utilisateur" if self.is_edit_mode else "Nouvel utilisateur")
        self.resize(440, 380)
        self.setStyleSheet("background-color: #F8FAFC;")
        self.setModal(True)
        self._build_ui()

        if self.is_edit_mode:
            self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Modifier un utilisateur" if self.is_edit_mode else "Nouvel utilisateur")
        title.setStyleSheet("color: #1E1B4B; font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.login_input = self._make_input("Ex : operateur3")
        if self.is_edit_mode:
            self.login_input.setEnabled(False)
        self._add_field(grid, 0, "Login *", self.login_input)

        if not self.is_edit_mode:
            self.password_input = self._make_input("Minimum 6 caractères")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._add_field(grid, 1, "Mot de passe *", self.password_input)
            next_row = 2
        else:
            next_row = 1

        self.nom_input = self._make_input("Ex : Jean KOUAME")
        self._add_field(grid, next_row, "Nom complet *", self.nom_input)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Opérateur", userData="operateur")
        self.role_combo.addItem("Administrateur", userData="admin")
        self.role_combo.setMinimumHeight(34)
        self.role_combo.setStyleSheet("""
            QComboBox { background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
            border-radius: 6px; padding: 4px 10px; font-size: 12px; }
        """)
        self._add_field(grid, next_row + 1, "Rôle *", self.role_combo)

        layout.addLayout(grid)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0;
            border-radius: 6px; padding: 0 16px; font-size: 12px; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        save_btn = QPushButton("Enregistrer" if self.is_edit_mode else "Créer")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 0 18px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #059669; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _make_input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(34)
        inp.setStyleSheet("""
            QLineEdit { background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
            border-radius: 6px; padding: 4px 10px; font-size: 12px; }
            QLineEdit:focus { border-color: #4338CA; }
        """)
        return inp

    def _add_field(self, grid: QGridLayout, row: int, label: str, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #1E1B4B; font-size: 11px; font-weight: bold; background: transparent;")
        grid.addWidget(lbl, row * 2, 0)
        grid.addWidget(widget, row * 2 + 1, 0)

    def _load_data(self):
        self.login_input.setText(self.user_data.get("login", ""))
        self.nom_input.setText(self.user_data.get("nom_complet", ""))
        role = self.user_data.get("role", "operateur")
        idx = self.role_combo.findData(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    def _on_save(self):
        nom = self.nom_input.text().strip()
        role = self.role_combo.currentData()

        if not nom:
            QMessageBox.warning(self, "Champ requis", "Le nom complet est obligatoire.")
            return

        try:
            if self.is_edit_mode:
                UserService.update(self.user_data["id"], {"nom_complet": nom, "role": role})
                QMessageBox.information(self, "Succès", "Utilisateur modifié.")
            else:
                login = self.login_input.text().strip()
                password = self.password_input.text()
                if not login:
                    QMessageBox.warning(self, "Champ requis", "Le login est obligatoire.")
                    return
                if len(password) < 6:
                    QMessageBox.warning(self, "Mot de passe trop court", "Minimum 6 caractères.")
                    return
                UserService.create({
                    "login": login, "password": password, "nom_complet": nom, "role": role,
                })
                QMessageBox.information(self, "Succès", f"Utilisateur '{login}' créé.")
            self.accept()

        except LoginExistantError as e:
            QMessageBox.warning(self, "Login déjà utilisé", str(e))
        except ChampObligatoireError as e:
            QMessageBox.warning(self, "Champ requis", str(e))
        except SchemaUtilisateurInconnuError as e:
            QMessageBox.critical(self, "Configuration requise", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Enregistrement échoué :\n{e}")


# ========================================================================
# POPUP RÉINITIALISATION MOT DE PASSE
# ========================================================================
class ResetPasswordDialog(QDialog):
    """Popup de réinitialisation de mot de passe."""

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle("Réinitialiser le mot de passe")
        self.resize(400, 220)
        self.setStyleSheet("background-color: #F8FAFC;")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(f"Nouveau mot de passe pour '{self.user_data['login']}'")
        title.setStyleSheet("color: #1E1B4B; font-size: 14px; font-weight: bold; background: transparent;")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimum 6 caractères")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(36)
        self.password_input.setStyleSheet("""
            QLineEdit { background-color: #FFFFFF; border: 1.5px solid #E2E8F0;
            border-radius: 6px; padding: 4px 10px; font-size: 12px; }
        """)
        layout.addWidget(self.password_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0;
            border-radius: 6px; padding: 0 14px; font-size: 12px; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        save_btn = QPushButton("Réinitialiser")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #F59E0B; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 0 16px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #D97706; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        password = self.password_input.text()
        if len(password) < 6:
            QMessageBox.warning(self, "Trop court", "Le mot de passe doit contenir au moins 6 caractères.")
            return

        try:
            UserService.reset_password(self.user_data["id"], password)
            QMessageBox.information(self, "Succès", "Mot de passe réinitialisé.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Réinitialisation échouée :\n{e}")