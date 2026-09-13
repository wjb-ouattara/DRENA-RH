"""
========================================================================
DRENAET-RH — Vue Documents (page de génération) - VERSION FINALE PROPRE
========================================================================
Page affichée quand l'utilisateur clique sur "Documents" dans la sidebar.

Affiche une grille de cartes (une par type de document).
Au clic sur une carte → ouvre le formulaire correspondant.

VERSION FINALE :
- Aucun émoji (0 caractère Unicode graphique)
- Icônes Font Awesome partout via qtawesome
- 8 documents distincts, aucun doublon
- Chaque document a sa propre description
"""

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal


class DocumentCard(QFrame):
    """Carte cliquable pour un type de document."""

    clicked = pyqtSignal(str)  # émet le type_document

    def __init__(self, type_doc: str, title: str, description: str,
                 icon_name: str, color: str, available: bool = True, parent=None):
        super().__init__(parent)
        self.type_doc = type_doc
        self.available = available
        self.color = color

        self.setObjectName("docCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor if available else Qt.CursorShape.ForbiddenCursor)
        self.setMinimumHeight(200)
        self.setStyleSheet(f"""
            QFrame#docCard {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }}
            QFrame#docCard:hover {{
                border: 2px solid {color};
                background-color: #FAFBFF;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # === Icône colorée (cercle de fond) ===
        icon_container = QLabel()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(
            f"background-color: {color}; "
            f"border-radius: 14px;"
        )
        icon_container.setPixmap(
            qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(28, 28))
        )
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_container)

        # === Titre ===
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #1E1B4B; font-size: 14px; font-weight: bold; padding-top: 6px;"
        )
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        # === Description ===
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(40)
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # === Footer avec vraie icône Font Awesome ===
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background: transparent;")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(6)

        if available:
            arrow_icon = QLabel()
            arrow_icon.setPixmap(
                qta.icon("fa5s.arrow-right", color=color).pixmap(QSize(12, 12))
            )
            arrow_icon.setStyleSheet("background: transparent;")
            footer_layout.addWidget(arrow_icon)

            footer_text = QLabel("Cliquer pour générer")
            footer_text.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 11px; background: transparent;"
            )
            footer_layout.addWidget(footer_text)
        else:
            lock_icon = QLabel()
            lock_icon.setPixmap(
                qta.icon("fa5s.lock", color="#94A3B8").pixmap(QSize(11, 11))
            )
            lock_icon.setStyleSheet("background: transparent;")
            footer_layout.addWidget(lock_icon)

            footer_text = QLabel("Disponible prochainement")
            footer_text.setStyleSheet(
                "color: #94A3B8; font-style: italic; font-size: 11px; background: transparent;"
            )
            footer_layout.addWidget(footer_text)

        footer_layout.addStretch()
        layout.addWidget(footer_widget)

    def mousePressEvent(self, event):
        """Émet le signal au clic."""
        if event.button() == Qt.MouseButton.LeftButton and self.available:
            self.clicked.emit(self.type_doc)
        super().mousePressEvent(event)


# ========================================================================
class DocumentsView(QWidget):
    """Page principale des Documents (grille de cartes)."""

    document_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
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

        # === En-tête de page ===
        header_card = self._build_header_card()
        layout.addWidget(header_card)

        # === Section titre AVEC icône Font Awesome ===
        section_widget = QWidget()
        section_widget.setStyleSheet("background: transparent;")
        section_layout = QHBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 8, 0, 0)
        section_layout.setSpacing(10)

        section_icon = QLabel()
        section_icon.setPixmap(
            qta.icon("fa5s.folder-open", color="#4338CA").pixmap(QSize(18, 18))
        )
        section_icon.setStyleSheet("background: transparent;")
        section_layout.addWidget(section_icon)

        section_title = QLabel("Choisissez le type de document à générer")
        section_title.setStyleSheet(
            "color: #1E1B4B; font-size: 16px; font-weight: bold; background: transparent;"
        )
        section_layout.addWidget(section_title)
        section_layout.addStretch()

        layout.addWidget(section_widget)

        # === Grille de cartes ===
        grid = QGridLayout()
        grid.setSpacing(16)

        # 8 documents distincts, aucun doublon
        docs_config = [
            (
                "autorisation_absence",
                "Autorisation d'Absence",
                "Demande d'autorisation d'absence avec désignation d'un intérimaire",
                "fa5s.calendar-check",
                "#4338CA",
                True,
            ),
            (
                "ordre_mission",
                "Ordre de Mission",
                "Ordre de mission officiel avec destination, objet, dates et moyen de déplacement",
                "fa5s.briefcase",
                "#7C3AED",
                True,
            ),
            (
                "attestation_travail",
                "Attestation de Travail",
                "Attestation officielle de travail au sein de la DRENAET de Katiola",
                "fa5s.file-signature",
                "#EC4899",
                True,
            ),
            (
                "attestation_presence",
                "Attestation de Présence au Poste",
                "Attestation certifiant la présence effective d'un agent à son poste",
                "fa5s.user-check",
                "#06B6D4",
                True,
            ),
            (
                "titre_conges",
                "Titre de Congés",
                "Titre officiel autorisant un agent à prendre ses congés",
                "fa5s.umbrella-beach",
                "#10B981",
                True,
            ),
            (
                "certificat_prise_service",
                "Certificat de Prise de Service",
                "Certificat de prise de service effective suite à un Arrêté de nomination",
                "fa5s.handshake",
                "#F59E0B",
                True,
            ),
            (
                "certificat_cessation",
                "Certificat de Cessation de Service",
                "Certificat de cessation de fonctions (mutation, retraite, démission)",
                "fa5s.sign-out-alt",
                "#DC2626",
                True,
            ),
            (
                "fiche_mutation",
                "Fiche d'inscription Mutation",
                "Fiche de demande de mutation pour Chef de Circonscription",
                "fa5s.exchange-alt",
                "#3B82F6",
                True,
            ),
        ]

        # Vérification anti-doublon (sécurité)
        seen_types = set()
        for type_doc, *_ in docs_config:
            if type_doc in seen_types:
                raise ValueError(f"Doublon détecté : {type_doc}")
            seen_types.add(type_doc)

        # Disposition 3 cartes par ligne
        cols = 3
        for i, (type_doc, title, desc, icon, color, dispo) in enumerate(docs_config):
            row, col = divmod(i, cols)
            card = DocumentCard(type_doc, title, desc, icon, color, dispo)
            card.clicked.connect(self.document_selected.emit)
            grid.addWidget(card, row, col)

        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _build_header_card(self) -> QFrame:
        """Carte d'en-tête avec dégradé + icône FA (pas d'émoji)."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338CA, stop:0.5 #7C3AED, stop:1 #EC4899);
                border-radius: 12px;
            }
            QFrame QLabel { color: #FFFFFF; background: transparent; }
        """)
        card.setMinimumHeight(110)

        outer_layout = QHBoxLayout(card)
        outer_layout.setContentsMargins(28, 20, 28, 20)
        outer_layout.setSpacing(20)

        # Icône Font Awesome à gauche
        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.file-alt", color="#FFFFFF").pixmap(QSize(48, 48))
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        outer_layout.addWidget(icon_label)

        # Textes à droite
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        title = QLabel("Génération de Documents Administratifs")
        title.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold;")
        text_layout.addWidget(title)

        subtitle = QLabel(
            "Générez en quelques clics les documents administratifs officiels. "
            "Chaque document est automatiquement numéroté, enregistré "
            "et archivé dans la base."
        )
        subtitle.setStyleSheet("color: #FFFFFF; font-size: 12px;")
        subtitle.setWordWrap(True)
        text_layout.addWidget(subtitle)

        outer_layout.addWidget(text_widget, stretch=1)

        return card