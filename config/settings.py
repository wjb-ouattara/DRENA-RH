"""
Configuration globale de l'application DRENAET-RH.

Centralise tous les paramètres : chemins, couleurs, métadonnées DRENAET.
Toute modification de comportement passe par ce fichier.
"""
import os
import shutil
import sys
from pathlib import Path


def get_resource_dir() -> Path:
    """
    Dossier des ressources EN LECTURE SEULE (code, feuilles de style,
    modèles, images d'origine).

    - Exécutable PyInstaller "onefile" : dossier temporaire de décompression
      (sys._MEIPASS), effacé à la fermeture de l'application.
    - Développement : racine du projet (ce fichier est dans config/).

    ⚠ Ne JAMAIS écrire dans ce dossier : en mode gelé il disparaît.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass).resolve()
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """
    Dossier des données UTILISATEUR, en lecture ET écriture (base SQLite,
    documents générés, logs, logo personnalisé).

    - Exécutable PyInstaller : %LOCALAPPDATA%\\DRENAET-RH
      Les données survivent ainsi au déplacement ou au remplacement de
      l'exécutable : un seul fichier .exe suffit à distribuer l'application.
    - Développement : racine du projet, pour ne rien changer au flux de
      travail habituel (data/, output/, logs/ restent dans le projet).
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base).resolve() / "DRENAET-RH"
        # Filet de sécurité si les variables d'environnement manquent
        return Path.home() / ".drenaet-rh"
    return Path(__file__).resolve().parent.parent

# ============================================================
# MÉTADONNÉES DE L'APPLICATION
# ============================================================
# L'application porte le nom de la structure qui l'utilise : la Direction
# Régionale (DRENAET) de Katiola, et non le ministère de tutelle (MENAET).
# Ce dernier ne subsiste que dans les références administratives officielles
# des documents (voir NUMERO_SUFFIX et DOCUMENT_REF_FORMAT plus bas), où il
# est parfaitement légitime.
APP_NAME = "DRENAET-RH"
APP_FULL_NAME = "DRENAET-RH - Gestion des Ressources Humaines"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Étudiant Génie Informatique"
APP_ORGANIZATION = "DRENAET de Katiola"
APP_DESCRIPTION = "Outil de gestion des ressources humaines"

# ============================================================
# CHEMINS DU PROJET
# ============================================================
# Deux racines distinctes — c'est ce qui rend l'exécutable autonome :
#   RESOURCE_ROOT  : lecture seule  (embarqué dans le .exe)
#   USER_DATA_ROOT : lecture/écriture (%LOCALAPPDATA%\DRENAET-RH)
# En développement, les deux pointent sur la racine du projet.
RESOURCE_ROOT = get_resource_dir()
USER_DATA_ROOT = get_user_data_dir()

# Conservé pour compatibilité avec du code existant qui l'importerait
PROJECT_ROOT = RESOURCE_ROOT

# --- Ressources en LECTURE SEULE (embarquées) ---
RESOURCES_DIR = RESOURCE_ROOT / "ressources"
ICONS_DIR = RESOURCES_DIR / "icons"
STYLES_DIR = RESOURCES_DIR / "styles"
TEMPLATES_DIR = RESOURCES_DIR / "templates"

# Images d'origine embarquées : servent de source lors de l'amorçage
BUNDLED_IMAGES_DIR = RESOURCES_DIR / "images"

# Base de données modèle embarquée (copiée au 1er lancement si présente)
BUNDLED_DATABASE_FILE = RESOURCE_ROOT / "data" / "drenaet.db"

# --- Données UTILISATEUR en ÉCRITURE ---
DATA_DIR = USER_DATA_ROOT / "data"
OUTPUT_DIR = USER_DATA_ROOT / "output"
LOG_DIR = USER_DATA_ROOT / "logs"
BACKUP_DIR = DATA_DIR / "backups"

# IMAGES_DIR est écrivable : l'écran Paramètres permet de remplacer le logo
# (voir src/ui/settings/settings_view.py). En développement il s'agit du même
# dossier que BUNDLED_IMAGES_DIR, donc rien ne change.
IMAGES_DIR = USER_DATA_ROOT / "ressources" / "images"

# Fichier de base de données SQLite
DATABASE_FILE = DATA_DIR / "drenaet.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Feuille de style principale
STYLESHEET = STYLES_DIR / "main.qss"

# ============================================================
# IDENTITÉ DE LA DRENAET (utilisée dans les documents)
# ============================================================
DRENAET_NOM_COMPLET = (
    "Direction Régionale de l'Éducation Nationale, "
    "de l'Alphabétisation et de l'Enseignement Technique de Katiola"
)
DRENAET_VILLE = "Katiola"
DRENAET_REGION = "Hambol"
DRENAET_BP = "BP 436 Katiola"
DRENAET_TELEPHONE = "27 23 59 70 29"
DRENAET_EMAIL = "katioladren@yahoo.fr"
MINISTERE = (
    "MINISTERE DE L'EDUCATION NATIONALE, "
    "DE L'ALPHABETISATION ET DE L'ENSEIGNEMENT TECHNIQUE"
)
DEVISE_NATIONALE = "Union – Discipline – Travail"
REPUBLIQUE = "REPUBLIQUE DE CÔTE D'IVOIRE"

# Format de numérotation : ex. "169/MENAET/DRENAET-KLA/SRH"
NUMERO_SUFFIX = "/MENAET/DRENAET-KLA/SRH"

# ============================================================
# PALETTE DE COULEURS
# ============================================================
COLORS = {
    # Couleurs principales
    "primary":        "#4338CA",   # Indigo profond
    "primary_dark":   "#3730A3",
    "primary_light":  "#6366F1",
    "primary_50":     "#E0E7FF",
    "secondary":      "#7C3AED",   # Violet
    "secondary_dark": "#6D28D9",

    # Accents
    "success":  "#10B981",         # Émeraude
    "warning":  "#F59E0B",         # Ambre
    "danger":   "#DC2626",         # Rouge
    "info":     "#3B82F6",         # Bleu
    "pink":     "#EC4899",
    "cyan":     "#06B6D4",

    # Neutres
    "background":   "#FAFBFF",     # Fond très clair (teinte violette)
    "surface":      "#FFFFFF",     # Blanc des cartes
    "border":       "#E2E8F0",
    "border_light": "#F1F5F9",

    # Texte
    "text_primary":   "#1E1B4B",   # Indigo très foncé
    "text_secondary": "#64748B",   # Gris
    "text_disabled":  "#94A3B8",
    "text_white":     "#FFFFFF",
}

# ============================================================
# TYPOGRAPHIE
# ============================================================
FONTS = {
    "primary":   "Inter",
    "fallback":  "Segoe UI",
    "monospace": "Consolas",
    "size_xs":   9,
    "size_sm":   10,
    "size_base": 11,
    "size_lg":   13,
    "size_xl":   16,
    "size_2xl":  22,
    "size_3xl":  28,
}

# ============================================================
# DIMENSIONS DE L'INTERFACE
# ============================================================
WINDOW_DEFAULT_WIDTH  = 1280
WINDOW_DEFAULT_HEIGHT = 800
WINDOW_MIN_WIDTH      = 1024
WINDOW_MIN_HEIGHT     = 700

SIDEBAR_WIDTH           = 240
SIDEBAR_COLLAPSED_WIDTH = 70
HEADER_HEIGHT           = 60

# ============================================================
# SÉCURITÉ
# ============================================================
SESSION_TIMEOUT_MINUTES = 30
MAX_LOGIN_ATTEMPTS      = 5
BCRYPT_ROUNDS           = 12

# ============================================================
# COMPTES PAR DÉFAUT (créés au 1er lancement)
# ⚠️ À CHANGER EN PRODUCTION
# ============================================================
DEFAULT_USERS = [
    {
        "login":        "admin",
        "password":     "admin2026",
        "nom_complet":  "Administrateur",
        "role":         "admin",
    },
    {
        "login":        "operateur1",
        "password":     "passer123",
        "nom_complet":  "Opérateur 1",
        "role":         "operateur",
    },
    {
        "login":        "operateur2",
        "password":     "passer123",
        "nom_complet":  "Opérateur 2",
        "role":         "operateur",
    },
]

# ============================================================
# SAUVEGARDE AUTOMATIQUE
# ============================================================
AUTO_BACKUP_ENABLED    = True
AUTO_BACKUP_HOUR       = 18
BACKUP_RETENTION_DAYS  = 30


def ensure_directories() -> None:
    """
    Crée les dossiers ÉCRIVABLES nécessaires s'ils n'existent pas.

    Les dossiers de ressources (ICONS_DIR, STYLES_DIR, TEMPLATES_DIR) ne sont
    volontairement pas créés ici : ils sont embarqués en lecture seule.
    """
    for directory in (DATA_DIR, BACKUP_DIR, OUTPUT_DIR, LOG_DIR, IMAGES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def bootstrap_user_data() -> None:
    """
    Amorçage au premier lancement de l'exécutable.

    Copie depuis le bundle vers le dossier de données utilisateur ce qui doit
    y être présent et modifiable :
      - la base de données modèle (structures de la région Hambol, comptes),
        si elle est embarquée et qu'aucune base utilisateur n'existe encore ;
      - les images officielles (logo, armoiries), pour que l'écran Paramètres
        puisse remplacer le logo.

    Sans effet en développement (les deux racines sont identiques) et
    idempotente : rien n'est jamais écrasé.
    """
    ensure_directories()

    # En développement les deux racines se confondent : rien à copier.
    if RESOURCE_ROOT == USER_DATA_ROOT:
        return

    # --- Base de données modèle ---
    if not DATABASE_FILE.exists() and BUNDLED_DATABASE_FILE.exists():
        try:
            shutil.copy2(BUNDLED_DATABASE_FILE, DATABASE_FILE)
        except OSError:
            # Échec non bloquant : main.py créera une base vierge puis
            # lancera le seed des données initiales.
            pass

    # --- Images officielles ---
    if BUNDLED_IMAGES_DIR.is_dir():
        for source in BUNDLED_IMAGES_DIR.iterdir():
            if not source.is_file():
                continue
            destination = IMAGES_DIR / source.name
            if destination.exists():
                continue
            try:
                shutil.copy2(source, destination)
            except OSError:
                pass


# Appelé automatiquement à l'import
bootstrap_user_data()


# ============================================================
# DEBUG / LOGS
# ============================================================
DEBUG = False  # Mettre True en développement pour voir les requêtes SQL
LOG_LEVEL = "INFO"


# ============================================================
# FORMAT DES NUMÉROS DE DOCUMENTS
# ============================================================
# Format officiel : 169/MENAET/DRENAET-KLA/SRH
DOCUMENT_REF_FORMAT = "{num}/MENAET/DRENAET-KLA/SRH"


# ============================================================
# INFORMATIONS OFFICIELLES DRENAET KATIOLA
# ============================================================
# Ces informations apparaissent sur tous les documents générés.
# Modifiables par l'administrateur dans Paramètres (à venir au Sprint 8).

DRENAET_INFO = {
    # Identité du Directeur Régional (signataire des documents)
    "directeur_regional_nom": "Monsieur le Directeur Régional",  # À personnaliser
    "directeur_regional_titre": "Directeur Régional",
    "directeur_par_procuration": False,  # True si signature "PO" par le Secrétaire Général

    # Coordonnées officielles
    "bp": "BP 436 Katiola",
    "telephone": "27 23 59 70 29",
    "email": "katioladren@yahoo.fr",
    "ville": "Katiola",
    "region": "Hambol",

    # Nom complet officiel (apparait dans les préambules)
    "nom_officiel": "Direction Régionale de l'Éducation Nationale, "
                    "de l'Alphabétisation et de l'Enseignement Technique de Katiola",
    "ministere": "Ministère de l'Éducation Nationale, "
                 "de l'Alphabétisation et de l'Enseignement Technique",
}
