"""
========================================================================
DRENAET-RH — Barre titre personnalisée (CustomTitleBar)
========================================================================
Remplace la barre titre native Windows par une barre custom avec :
- Logo DRENA + nom de l'application à gauche
- Zone de drag au centre (permet de déplacer la fenêtre)
- Bouton minimize / maximize / close à droite (recodés)

La barre gère le déplacement de la fenêtre quand l'utilisateur fait
glisser la souris sur la zone de titre.
"""

from pathlib import Path

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)


class CustomTitleBar(QFrame):
    """Barre de titre personnalisée pour la fenêtre frameless."""

    # Signaux émis quand l'utilisateur clique sur les boutons
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    toggle_sidebar_requested = pyqtSignal()  # NOUVEAU : bouton hamburger

    HEIGHT = 44  # Hauteur en pixels

    def __init__(self, title: str = "DRENAET-RH",
                 subtitle: str = "Gestion des Ressources Humaines",
                 logo_path: str = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(self.HEIGHT)

        # Pour gérer le drag
        self._drag_pos: QPoint = None
        self._is_maximized = False

        self._build_ui(title, subtitle, logo_path)
        self._apply_style()

    # ====================================================================
    def _build_ui(self, title: str, subtitle: str, logo_path: str):
        """Construit l'interface de la barre titre."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 0, 0)  # pas de marge à droite (boutons collés)
        layout.setSpacing(10)

        # === Bouton HAMBURGER (toggle sidebar) ===
        self.btn_hamburger = QPushButton()
        self.btn_hamburger.setObjectName("btnHamburger")
        self.btn_hamburger.setIcon(qta.icon("fa5s.bars", color="#57534E"))
        self.btn_hamburger.setIconSize(QSize(16, 16))
        self.btn_hamburger.setFixedSize(40, self.HEIGHT)
        self.btn_hamburger.setToolTip("Réduire / Étendre le menu")
        self.btn_hamburger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hamburger.setFlat(True)
        self.btn_hamburger.clicked.connect(self.toggle_sidebar_requested.emit)
        layout.addWidget(self.btn_hamburger)

        # === Logo (si fourni) ===
        if logo_path and Path(logo_path).exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            scaled = pixmap.scaled(
                QSize(28, 28),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
            logo_label.setObjectName("titleBarLogo")
            layout.addWidget(logo_label)
        else:
            # Fallback : icône graduation-cap
            icon_label = QLabel()
            icon_label.setPixmap(
                qta.icon("fa5s.graduation-cap", color="#F97316").pixmap(QSize(20, 20))
            )
            layout.addWidget(icon_label)

        # === Titre + sous-titre ===
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QHBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("titleBarTitle")
        text_layout.addWidget(title_label)

        sep_label = QLabel("—")
        sep_label.setObjectName("titleBarSeparator")
        text_layout.addWidget(sep_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("titleBarSubtitle")
        text_layout.addWidget(subtitle_label)

        layout.addWidget(text_widget)

        # === Zone de drag flexible (étire au milieu) ===
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        layout.addWidget(spacer)

        # === Boutons fenêtre ===
        # Bouton Minimize
        self.btn_minimize = self._build_window_button(
            icon_name="fa5s.window-minimize",
            tooltip="Réduire",
            object_name="btnMinimize",
        )
        self.btn_minimize.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self.btn_minimize)

        # Bouton Maximize/Restore
        self.btn_maximize = self._build_window_button(
            icon_name="fa5s.window-maximize",
            tooltip="Agrandir",
            object_name="btnMaximize",
        )
        self.btn_maximize.clicked.connect(self.maximize_requested.emit)
        layout.addWidget(self.btn_maximize)

        # Bouton Close
        self.btn_close = self._build_window_button(
            icon_name="fa5s.times",
            tooltip="Fermer",
            object_name="btnClose",
        )
        self.btn_close.clicked.connect(self.close_requested.emit)
        self.btn_close.installEventFilter(self)
        layout.addWidget(self.btn_close)

    # ====================================================================
    def _build_window_button(self, icon_name: str, tooltip: str,
                              object_name: str) -> QPushButton:
        """Crée un bouton de fenêtre (minimize/maximize/close)."""
        btn = QPushButton()
        btn.setObjectName(object_name)
        btn.setIcon(qta.icon(icon_name, color="#57534E"))
        btn.setIconSize(QSize(12, 12))
        btn.setFixedSize(46, self.HEIGHT)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        return btn

    # ====================================================================
    def _apply_style(self):
        """Applique le style à la barre titre — palette 'Light & Ember'."""
        self.setStyleSheet("""
            QFrame#customTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F1F5F9;
            }
            QLabel#titleBarLogo {
                background: transparent;
            }
            QLabel#titleBarTitle {
                color: #1C1917;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }
            QLabel#titleBarSeparator {
                color: #D6D3D1;
                font-size: 13px;
                background: transparent;
            }
            QLabel#titleBarSubtitle {
                color: #78716C;
                font-size: 12px;
                background: transparent;
            }
            QPushButton#btnMinimize, QPushButton#btnMaximize {
                background-color: transparent;
                border: none;
            }
            QPushButton#btnMinimize:hover, QPushButton#btnMaximize:hover {
                background-color: #F5F5F4;
            }
            QPushButton#btnHamburger {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton#btnHamburger:hover {
                background-color: #FFEDD5;
            }
            QPushButton#btnClose {
                background-color: transparent;
                border: none;
            }
            QPushButton#btnClose:hover {
                background-color: #DC2626;
            }
        """)

    def paintEvent(self, event):
        """Peint le fond (via QSS) PUIS un fin liseré tricolore sous la barre
        — signature de marque reprise sur tous les écrans (login, dashboard) :
        orange / blanc / vert (drapeau CI)."""
        super().paintEvent(event)

        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        strip_h = 3
        y = self.height() - strip_h
        w = self.width()
        thirds = w / 3

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F97316"))
        painter.drawRect(0, y, int(thirds), strip_h)
        painter.setBrush(QColor("#E7E5E4"))
        painter.drawRect(int(thirds), y, int(thirds), strip_h)
        painter.setBrush(QColor("#128A4D"))
        painter.drawRect(int(thirds * 2), y, w - int(thirds * 2), strip_h)

        painter.end()

    # ====================================================================
    def eventFilter(self, obj, event):
        """Bascule l'icône du bouton Fermer en blanc au survol (fond rouge)."""
        from PyQt6.QtCore import QEvent
        if obj is self.btn_close:
            if event.type() == QEvent.Type.Enter:
                self.btn_close.setIcon(qta.icon("fa5s.times", color="#FFFFFF"))
            elif event.type() == QEvent.Type.Leave:
                self.btn_close.setIcon(qta.icon("fa5s.times", color="#57534E"))
        return super().eventFilter(obj, event)

    # ====================================================================
    def update_maximize_icon(self, is_maximized: bool):
        """Change l'icône du bouton maximize selon l'état."""
        self._is_maximized = is_maximized
        if is_maximized:
            self.btn_maximize.setIcon(qta.icon("fa5s.clone", color="#57534E"))
            self.btn_maximize.setToolTip("Restaurer")
        else:
            self.btn_maximize.setIcon(qta.icon("fa5s.window-maximize", color="#57534E"))
            self.btn_maximize.setToolTip("Agrandir")

    # ====================================================================
    # GESTION DU DRAG (déplacement de la fenêtre)
    # ====================================================================
    def mousePressEvent(self, event: QMouseEvent):
        """Capture la position de la souris au clic gauche."""
        # Ne pas déclencher le drag si on clique sur le hamburger
        child = self.childAt(event.position().toPoint())
        if child == self.btn_hamburger:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # On stocke la position globale moins la position de la fenêtre parent
            window = self.window()
            self._drag_pos = event.globalPosition().toPoint() - window.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Déplace la fenêtre quand l'utilisateur fait glisser."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            window = self.window()
            # Si la fenêtre est maximisée, on la restaure d'abord
            if window.isMaximized():
                # Restaurer la fenêtre
                window.showNormal()
                # Recalculer le drag pour que ça suive correctement la souris
                # Centrer la fenêtre sous la souris
                self._drag_pos = QPoint(
                    int(window.width() / 2),
                    int(self.HEIGHT / 2),
                )
                self.update_maximize_icon(False)
            # Déplacer la fenêtre
            window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Relâche le drag."""
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Double-clic sur la barre titre = maximiser/restaurer."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()