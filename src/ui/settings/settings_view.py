"""
========================================================================
DRENAET-RH — SettingsView (VERSION 2 — Redesign sans encadrés)
========================================================================
Refonte complète de l'UI. Backend INCHANGÉ : mêmes appels exacts à
SettingsService (get_all / update / reset_to_defaults) — zéro risque.

Concept :
- Formulaire "underline" (champs soulignés type Material Design), PAS de
  cartes/boîtes bordées empilées comme avant — juste des sections aérées
  séparées par un filet fin (1px) et une hiérarchie typographique claire.
- Colonne de droite : APERÇU LIVE d'un en-tête de document officiel, qui
  se met à jour en temps réel pendant la saisie. C'est l'élément
  "innovant" : on voit concrètement l'effet des réglages sur les PDFs
  générés, pas juste un formulaire abstrait.
"""

import shutil
from pathlib import Path

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QScrollArea, QCheckBox, QSpinBox, QMessageBox, QFileDialog,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QColor

from src.services.settings_service import SettingsService
from src.services.auth_service import UserSession


# ========================================================================
# PALETTE — cohérente avec le reste de l'app (Light & Ember)
# ========================================================================
ORANGE_PRIMARY = "#F97316"
ORANGE_DARK = "#C2410C"
TEXT_DARK = "#1C1917"
TEXT_MUTED = "#78716C"
BORDER_LIGHT = "#E7E5E4"
BORDER_FOCUS = ORANGE_PRIMARY


# ========================================================================
# CHAMP "UNDERLINE" (pas de boîte, juste un soulignement)
# ========================================================================
class UnderlineField(QWidget):
    """Champ de saisie sans bordure encadrante — juste un label flottant
    au-dessus et un soulignement qui s'illumine en orange au focus."""

    def __init__(self, label: str, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel(label.upper())
        self.label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; "
            "letter-spacing: 0.5px; background: transparent; border: none;"
        )
        layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setMinimumHeight(30)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                border-bottom: 2px solid {BORDER_LIGHT};
                border-radius: 0px;
                padding: 2px 2px 6px 2px;
                font-size: 13px;
                color: {TEXT_DARK};
            }}
            QLineEdit:focus {{
                border-bottom: 2px solid {BORDER_FOCUS};
            }}
        """)
        layout.addWidget(self.input)

        # Live update hook (branché depuis l'extérieur)
        self.input.textChanged.connect(self._notify)
        self._on_change_callback = None

    def _notify(self, _text):
        if self._on_change_callback:
            self._on_change_callback()

    def on_change(self, callback):
        self._on_change_callback = callback

    def text(self) -> str:
        return self.input.text().strip()

    def setText(self, value: str):
        self.input.setText(value or "")


# ========================================================================
# SECTION (titre + filet, PAS de carte encadrée)
# ========================================================================
def build_section_header(title: str, icon_name: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    title_row = QHBoxLayout()
    title_row.setSpacing(8)
    icon = QLabel()
    icon.setPixmap(qta.icon(icon_name, color=ORANGE_PRIMARY).pixmap(QSize(15, 15)))
    icon.setStyleSheet("background: transparent; border: none;")
    title_row.addWidget(icon)

    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(
        f"color: {TEXT_DARK}; font-size: 14px; font-weight: bold; background: transparent; border: none;"
    )
    title_row.addWidget(title_lbl)
    title_row.addStretch()
    layout.addLayout(title_row)

    rule = QFrame()
    rule.setFixedHeight(1)
    rule.setStyleSheet(f"background-color: {BORDER_LIGHT}; border: none;")
    layout.addWidget(rule)

    return w


# ========================================================================
# APERÇU LIVE — reproduit l'en-tête d'un document officiel
# ========================================================================
class DocumentPreview(QFrame):
    """Carte 'papier' avec ombre douce, qui mime l'en-tête réel des PDFs
    générés. C'est la seule chose qui a volontairement une bordure/ombre
    dans cette page : elle représente une vraie feuille de papier."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(340)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 4px;
                border: 1px solid #F1F5F9;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 35))
        self.setGraphicsEffect(shadow)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(0)

        self.ministere_lbl = QLabel("MINISTÈRE DE L'ÉDUCATION NATIONALE")
        self.ministere_lbl.setWordWrap(True)
        self.ministere_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ministere_lbl.setStyleSheet(
            "color: #57534E; font-size: 8.5px; font-weight: bold; "
            "letter-spacing: 0.5px; background: transparent; border: none;"
        )
        layout.addWidget(self.ministere_lbl)

        layout.addSpacing(10)

        self.nom_lbl = QLabel("DRENAET DE KATIOLA")
        self.nom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nom_lbl.setWordWrap(True)
        self.nom_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        layout.addWidget(self.nom_lbl)

        self.ville_lbl = QLabel("Katiola — Région du Hambol")
        self.ville_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ville_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; background: transparent; border: none;"
        )
        layout.addWidget(self.ville_lbl)

        layout.addSpacing(14)

        # Filet orange fin (signature de marque)
        rule = QFrame()
        rule.setFixedHeight(2)
        rule.setStyleSheet(f"background-color: {ORANGE_PRIMARY}; border: none;")
        layout.addWidget(rule)

        layout.addSpacing(10)

        self.contact_lbl = QLabel("BP 436 Katiola  ·  27 23 59 70 29  ·  katioladren@yahoo.fr")
        self.contact_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contact_lbl.setWordWrap(True)
        self.contact_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; background: transparent; border: none;"
        )
        layout.addWidget(self.contact_lbl)

        layout.addSpacing(36)

        # Zone corps de document (placeholder discret)
        body_placeholder = QLabel("···")
        body_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_placeholder.setStyleSheet(
            "color: #E7E5E4; font-size: 20px; background: transparent; border: none;"
        )
        layout.addWidget(body_placeholder)

        layout.addSpacing(30)

        # Bloc signature (aligné à droite comme sur les vrais documents)
        sign_row = QHBoxLayout()
        sign_row.addStretch()
        sign_col = QVBoxLayout()
        sign_col.setSpacing(2)

        sign_lieu = QLabel("Fait à Katiola, le 04/09/2026")
        sign_lieu.setAlignment(Qt.AlignmentFlag.AlignRight)
        sign_lieu.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 8.5px; background: transparent; border: none;"
        )
        sign_col.addWidget(sign_lieu)

        self.sign_titre_lbl = QLabel("Le Directeur Régional")
        self.sign_titre_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.sign_titre_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 9.5px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        sign_col.addWidget(self.sign_titre_lbl)

        self.sign_nom_lbl = QLabel("Monsieur KOUAME Jean")
        self.sign_nom_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.sign_nom_lbl.setWordWrap(True)
        self.sign_nom_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 9.5px; background: transparent; border: none;"
        )
        sign_col.addWidget(self.sign_nom_lbl)

        sign_row.addLayout(sign_col)
        layout.addLayout(sign_row)

    # ====================================================================
    def update_preview(self, data: dict):
        """Met à jour l'aperçu en temps réel avec les valeurs saisies."""
        ministere = data.get("ministere") or "MINISTÈRE DE L'ÉDUCATION NATIONALE"
        self.ministere_lbl.setText(ministere.upper())

        nom = data.get("nom_officiel") or "DRENAET DE KATIOLA"
        self.nom_lbl.setText(nom.upper())

        ville = data.get("ville") or "Katiola"
        region = data.get("region") or "Hambol"
        self.ville_lbl.setText(f"{ville} — Région du {region}")

        bp = data.get("bp") or "BP 436 Katiola"
        tel = data.get("telephone") or "27 23 59 70 29"
        email = data.get("email") or "katioladren@yahoo.fr"
        self.contact_lbl.setText(f"{bp}  ·  {tel}  ·  {email}")

        titre = data.get("directeur_regional_titre") or "Directeur Régional"
        if str(data.get("directeur_par_procuration", "False")).lower() == "true":
            titre = f"P.O. {titre}"
        self.sign_titre_lbl.setText(titre)

        dr_nom = data.get("directeur_regional_nom") or "Monsieur/Madame ..."
        self.sign_nom_lbl.setText(dr_nom)


# ========================================================================
# VUE PRINCIPALE
# ========================================================================
class SettingsView(QWidget):
    """Vue de configuration — formulaire épuré + aperçu live."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = {}
        self._build_ui()
        self._load_settings()

    # ====================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(40, 28, 40, 40)
        main_layout.setSpacing(48)

        # Colonne gauche : formulaire
        form_col = QVBoxLayout()
        form_col.setSpacing(28)

        form_col.addWidget(build_section_header("Identité DRENAET", "fa5s.building"))
        form_col.addWidget(self._build_identite_fields())

        form_col.addWidget(build_section_header("Directeur Régional", "fa5s.user-tie"))
        form_col.addWidget(self._build_direction_fields())

        form_col.addWidget(build_section_header("Logo & Documents", "fa5s.sliders-h"))
        form_col.addWidget(self._build_misc_fields())

        form_col.addWidget(self._build_actions_bar())
        form_col.addStretch()

        main_layout.addLayout(form_col, stretch=3)

        # Colonne droite : aperçu live (sticky visuellement via alignement haut)
        preview_col = QVBoxLayout()
        preview_col.setSpacing(12)

        preview_label = QLabel("APERÇU EN TEMPS RÉEL")
        preview_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent;"
        )
        preview_col.addWidget(preview_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.preview = DocumentPreview()
        preview_col.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)

        hint = QLabel("Cet aperçu simule l'en-tête d'un document généré.\nIl se met à jour pendant votre saisie.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10.5px; background: transparent;")
        preview_col.addWidget(hint)

        preview_col.addStretch()
        main_layout.addLayout(preview_col, stretch=2)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(40, 26, 40, 0)
        layout.setSpacing(4)

        title = QLabel("Paramètres")
        title.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 20px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Ces informations apparaissent automatiquement sur tous les documents administratifs générés."
        )
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; background: transparent;")
        layout.addWidget(subtitle)

        return w

    # ====================================================================
    def _add_field(self, container_layout, key: str, label: str, placeholder: str = ""):
        field = UnderlineField(label, placeholder)
        field.on_change(self._refresh_preview)
        self.fields[key] = field
        container_layout.addWidget(field)
        return field

    def _build_identite_fields(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(18)

        self._add_field(v, "nom_officiel", "Nom officiel", "Ex : DRENAET de Katiola")
        self._add_field(v, "ministere", "Ministère de tutelle", "Ex : Ministère de l'Éducation Nationale")

        row1 = QHBoxLayout()
        row1.setSpacing(24)
        f_ville = UnderlineField("Ville", "Ex : Katiola")
        f_ville.on_change(self._refresh_preview)
        self.fields["ville"] = f_ville
        row1.addWidget(f_ville)

        f_region = UnderlineField("Région", "Ex : Hambol")
        f_region.on_change(self._refresh_preview)
        self.fields["region"] = f_region
        row1.addWidget(f_region)
        v.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(24)
        f_bp = UnderlineField("Boîte postale (BP)", "Ex : BP 436 Katiola")
        f_bp.on_change(self._refresh_preview)
        self.fields["bp"] = f_bp
        row2.addWidget(f_bp)

        f_tel = UnderlineField("Téléphone", "Ex : 27 23 59 70 29")
        f_tel.on_change(self._refresh_preview)
        self.fields["telephone"] = f_tel
        row2.addWidget(f_tel)
        v.addLayout(row2)

        self._add_field(v, "email", "Email", "Ex : katioladren@yahoo.fr")

        return w

    def _build_direction_fields(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(18)

        self._add_field(v, "directeur_regional_nom", "Nom du Directeur Régional", "Ex : Monsieur KOUAME Jean")
        self._add_field(v, "directeur_regional_titre", "Titre", "Ex : Directeur Régional")

        self.procuration_check = QCheckBox("Signature par procuration (P.O. — Secrétaire Général signe à sa place)")
        self.procuration_check.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 12px; background: transparent;"
        )
        self.procuration_check.stateChanged.connect(self._refresh_preview)
        v.addWidget(self.procuration_check)

        return w

    def _build_misc_fields(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(18)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setSpacing(16)

        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(56, 56)
        self.logo_preview.setStyleSheet(
            f"background-color: #FAFAF9; border: 1px dashed {BORDER_LIGHT}; border-radius: 8px;"
        )
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.addWidget(self.logo_preview)

        logo_col = QVBoxLayout()
        logo_col.setSpacing(6)
        logo_label = QLabel("LOGO SIDEBAR")
        logo_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; background: transparent;"
        )
        logo_col.addWidget(logo_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        change_btn = QPushButton("Changer")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.setFixedHeight(30)
        change_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {ORANGE_DARK}; border: none;
            font-size: 12px; font-weight: bold; text-decoration: underline; }}
            QPushButton:hover {{ color: {ORANGE_PRIMARY}; }}
        """)
        change_btn.clicked.connect(self._on_change_logo)
        btn_row.addWidget(change_btn)

        reset_logo_btn = QPushButton("Réinitialiser")
        reset_logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_logo_btn.setFixedHeight(30)
        reset_logo_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEXT_MUTED}; border: none; font-size: 12px; }}
            QPushButton:hover {{ color: {TEXT_DARK}; }}
        """)
        reset_logo_btn.clicked.connect(self._on_reset_logo)
        btn_row.addWidget(reset_logo_btn)
        btn_row.addStretch()
        logo_col.addLayout(btn_row)

        logo_row.addLayout(logo_col, stretch=1)
        v.addLayout(logo_row)

        # Quota congés
        quota_row = QHBoxLayout()
        quota_label_col = QVBoxLayout()
        quota_label_col.setSpacing(4)
        quota_title = QLabel("QUOTA DE CONGÉS ANNUELS")
        quota_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; background: transparent;"
        )
        quota_label_col.addWidget(quota_title)
        quota_sub = QLabel("Nombre de jours ouvrés par agent et par an")
        quota_sub.setStyleSheet(f"color: {TEXT_DARK}; font-size: 12px; background: transparent;")
        quota_label_col.addWidget(quota_sub)
        quota_row.addLayout(quota_label_col)
        quota_row.addStretch()

        self.quota_spin = QSpinBox()
        self.quota_spin.setRange(1, 90)
        self.quota_spin.setSuffix(" jours")
        self.quota_spin.setFixedWidth(110)
        self.quota_spin.setMinimumHeight(34)
        self.quota_spin.setStyleSheet(f"""
            QSpinBox {{ background: transparent; border: none; border-bottom: 2px solid {BORDER_LIGHT};
            padding: 4px; font-size: 13px; color: {TEXT_DARK}; }}
            QSpinBox:focus {{ border-bottom: 2px solid {BORDER_FOCUS}; }}
        """)
        quota_row.addWidget(self.quota_spin)
        v.addLayout(quota_row)

        return w

    # ====================================================================
    def _build_actions_bar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 12, 0, 0)

        reset_btn = QPushButton("Réinitialiser tout")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setFixedHeight(40)
        reset_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #DC2626; border: none;
            font-size: 12px; font-weight: 600; }
            QPushButton:hover { text-decoration: underline; }
        """)
        reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(reset_btn)

        layout.addStretch()

        save_btn = QPushButton("  Enregistrer les modifications")
        save_btn.setIcon(qta.icon("fa5s.check", color="#FFFFFF"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(42)
        save_btn.setMinimumWidth(240)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {ORANGE_PRIMARY}; color: #FFFFFF; border: none;
            border-radius: 8px; padding: 0 20px; font-size: 12px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {ORANGE_DARK}; }}
        """)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        return w

    # ====================================================================
    def _collect_current_values(self) -> dict:
        data = {k: f.text() for k, f in self.fields.items()}
        data["directeur_par_procuration"] = str(self.procuration_check.isChecked())
        return data

    def _refresh_preview(self):
        self.preview.update_preview(self._collect_current_values())

    # ====================================================================
    def _load_settings(self):
        try:
            current = SettingsService.get_all()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Chargement des paramètres échoué :\n{e}")
            return

        for key, field in self.fields.items():
            field.setText(current.get(key, ""))

        self.procuration_check.setChecked(
            str(current.get("directeur_par_procuration", "False")).lower() == "true"
        )

        try:
            self.quota_spin.setValue(int(current.get("quota_conges_annuel", 30)))
        except (ValueError, TypeError):
            self.quota_spin.setValue(30)

        self._refresh_logo_preview(current.get("logo_path", ""))
        self._refresh_preview()

    def _refresh_logo_preview(self, logo_path: str):
        from config import settings as app_config

        path = Path(logo_path) if logo_path else app_config.IMAGES_DIR / "logo_drena.png"
        if path.exists():
            pixmap = QPixmap(str(path))
            scaled = pixmap.scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_preview.setPixmap(scaled)
        else:
            self.logo_preview.clear()
            self.logo_preview.setText("—")

    # ====================================================================
    def _on_change_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un logo", str(Path.home()), "Images (*.png *.jpg *.jpeg)",
        )
        if not path:
            return

        from config import settings as app_config
        dest = app_config.IMAGES_DIR / "logo_drena.png"
        try:
            shutil.copy(path, dest)
            self._refresh_logo_preview("")
            QMessageBox.information(
                self, "Logo mis à jour",
                "Redémarrez l'application pour voir le nouveau logo dans la sidebar.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de copier le logo :\n{e}")

    def _on_reset_logo(self):
        reply = QMessageBox.question(
            self, "Réinitialiser le logo", "Revenir au logo par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                SettingsService.update({"logo_path": ""})
                self._refresh_logo_preview("")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # ====================================================================
    def _on_save(self):
        data = self._collect_current_values()
        data["quota_conges_annuel"] = str(self.quota_spin.value())

        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"
            SettingsService.update(data, user_login=user_login)
            QMessageBox.information(
                self, "Succès",
                "Paramètres enregistrés. Les prochains documents générés "
                "utiliseront automatiquement ces nouvelles informations.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Enregistrement échoué :\n{e}")

    def _on_reset(self):
        reply = QMessageBox.warning(
            self, "Réinitialiser tous les paramètres",
            "Voulez-vous vraiment réinitialiser TOUS les paramètres à leurs valeurs par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            session = UserSession.get_instance()
            user_login = session.login if session.is_authenticated else "unknown"
            SettingsService.reset_to_defaults(user_login=user_login)
            self._load_settings()
            QMessageBox.information(self, "Réinitialisé", "Les paramètres par défaut ont été restaurés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))