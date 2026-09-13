# -*- mode: python ; coding: utf-8 -*-
"""
========================================================================
DRENAET-RH — Configuration PyInstaller (mode ONEFILE)
========================================================================
Produit UN SEUL fichier : dist\\DRENAET-RH.exe

Ce fichier est autonome : il peut être copié n'importe où (Bureau, clé USB,
autre poste) et lancé sans son dossier d'origine.

Où vont les données ?
    Les ressources (images, feuille de style, base modèle) sont embarquées
    dans l'exécutable, en lecture seule.
    La base de données, les documents générés et les logs sont écrits dans
    %LOCALAPPDATA%\\DRENAET-RH — voir config/settings.py (get_user_data_dir).
    Les données du professeur survivent donc au remplacement de l'exe :
    une mise à jour consiste simplement à écraser le fichier.

Construction :
    .\\build.ps1
ou directement :
    venv\\Scripts\\pyinstaller.exe main.spec --noconfirm
"""

from pathlib import Path

BASE_DIR = Path(SPECPATH)

# ========================================================================
# FICHIERS DE DONNÉES EMBARQUÉS
# ========================================================================
# Format : (source sur le disque, dossier de destination dans le bundle)
# La destination doit reproduire l'arborescence attendue par
# config/settings.py, qui lit les ressources depuis sys._MEIPASS.
datas = []

# --- Ressources (images, styles, modèles, icônes) ---
for nom_dossier in ("images", "styles", "templates", "icons"):
    dossier = BASE_DIR / "ressources" / nom_dossier
    if dossier.is_dir():
        datas.append((str(dossier), f"ressources/{nom_dossier}"))

# --- Base de données modèle ---
# Embarquée pour que le professeur démarre avec les structures de la région
# Hambol et les comptes déjà en place. Copiée dans %LOCALAPPDATA% au premier
# lancement par bootstrap_user_data(), puis jamais réécrasée.
base_modele = BASE_DIR / "data" / "drenaet.db"
if base_modele.is_file():
    datas.append((str(base_modele), "data"))

# ========================================================================
# IMPORTS À FORCER
# ========================================================================
# PyInstaller analyse les imports statiquement : tout ce qui est importé
# dynamiquement (dans une fonction, via un nom construit) doit être déclaré.
hiddenimports = [
    # Chargé dans main.py uniquement si la base est vide
    "src.utils.seed_data",

    # Les 8 formulaires de documents sont importés dans
    # MainWindow._add_pages(), donc à l'intérieur d'une méthode
    "src.ui.documents.documents_view",
    "src.ui.documents.autorisation_form",
    "src.ui.documents.ordre_mission_form",
    "src.ui.documents.attestation_travail_form",
    "src.ui.documents.attestation_presence_form",
    "src.ui.documents.titre_conges_form",
    "src.ui.documents.certificat_prise_service_form",
    "src.ui.documents.certificat_cessation_form",
    "src.ui.documents.fiche_mutation_form",

    # Popup de changement de mot de passe (import différé dans main_window)
    "src.ui.widgets.change_password_dialog",

    # Modèles SQLAlchemy chargés dans init_db()
    "src.models.structure",
    "src.models.personnel",
    "src.models.document",
    "src.models.absence",
    "src.models.utilisateur",
    "src.models.compteur",
    "src.models.audit_log",
    "src.models.import_log",
    "src.models.settings_model",

    # Polices d'icônes de qtawesome
    "qtawesome",

    # Pilote SQLite
    "sqlalchemy.dialects.sqlite",
]

# ========================================================================
# MODULES EXCLUS (allègent nettement le fichier final)
# ========================================================================
excludes = [
    "tkinter",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtMultimedia",
    "PyQt6.Qt3DCore",
    "PySide6",
    "PyQt5",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
]

# ========================================================================
a = Analysis(
    ["main.py"],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Icône de l'exécutable : PyInstaller attend un .ico, pas un .png
chemin_icone = BASE_DIR / "ressources" / "images" / "logo_drena.ico"
icone = str(chemin_icone) if chemin_icone.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DRENAET-RH",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # application graphique : pas de console noire
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icone,
    version=None,
)
