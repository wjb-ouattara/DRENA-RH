"""
========================================================================
DRENAET-RH — AdministrationView (conteneur avec onglets)
========================================================================
Vue principale du module Administration.

2 onglets :
- Utilisateurs : gestion des comptes (CRUD, mot de passe, activation)
- Journal d'audit : consultation globale de toutes les actions tracées
"""

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QStackedWidget,
)

from src.ui.administration.users_view import UsersView
from src.ui.administration.audit_log_view import AuditLogView


class AdministrationView(QWidget):
    """Vue conteneur du module Administration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_tabs_bar())

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #F8FAFC;")

        self.users_view = UsersView()
        self.stack.addWidget(self.users_view)

        self.audit_view = AuditLogView()
        self.stack.addWidget(self.audit_view)

        layout.addWidget(self.stack, stretch=1)

    def _build_tabs_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("QFrame { background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0; }")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(4)

        self._tab_buttons = []
        tabs = [("fa5s.users-cog", "Utilisateurs"), ("fa5s.history", "Journal d'audit")]
        for i, (icon, label) in enumerate(tabs):
            btn = QPushButton(f"   {label}")
            btn.setIcon(qta.icon(icon, color="#64748B"))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(52)
            btn.setMinimumWidth(180)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #64748B; border: none;
                    border-bottom: 3px solid transparent; padding: 0 20px;
                    font-size: 13px; font-weight: 500; text-align: left;
                }
                QPushButton:hover { color: #4338CA; background-color: #F1F5F9; }
                QPushButton:checked {
                    color: #4338CA; border-bottom: 3px solid #4338CA;
                    font-weight: bold; background-color: #FFFFFF;
                }
            """)
            btn.toggled.connect(
                lambda checked, ic=icon, b=btn: b.setIcon(
                    qta.icon(ic, color="#4338CA" if checked else "#64748B")
                )
            )
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_click(idx))
            layout.addWidget(btn)
            self._tab_buttons.append(btn)

        layout.addStretch()
        self._tab_buttons[0].setChecked(True)
        return bar

    def _on_tab_click(self, index: int):
        for i, b in enumerate(self._tab_buttons):
            b.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.users_view.refresh()
        else:
            self.audit_view.refresh()