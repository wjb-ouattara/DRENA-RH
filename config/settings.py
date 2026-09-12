"""
Configuration globale de l'application DRENAET-RH.

Centralise tous les paramètres : chemins, couleurs, métadonnées DRENAET.
Toute modification de comportement passe par ce fichier.
"""
import sys
from pathlib import Path

# ============================================================
# MÉTADONNÉES DE L'APPLICATION
# ============================================================
APP_NAME = "DRENAET-RH"
APP_FULL_NAME = "DRENAET-RH — Gestion des Ressources Humaines"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Étudiant Génie Informatique"
APP_ORGANIZATION = "DRENAET de Katiola"
APP_DESCRIPTION = "Outil de gestion des ressources humaines"
ORGANIZATION = "DRENAET de Katiola"

# ============================================================
# CHEMINS DU PROJET
# ============================================================
# Racine du projet (calculée dynamiquement)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Dossiers principaux
DATA_DIR = PROJECT_ROOT / "data"
RESOURCES_DIR = PROJECT_ROOT / "ressources"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKUP_DIR = DATA_DIR / "backups"

# Dossiers ressources
ICONS_DIR = RESOURCES_DIR / "icons"
IMAGES_DIR = RESOURCES_DIR / "images"
STYLES_DIR = RESOURCES_DIR / "styles"
TEMPLATES_DIR = RESOURCES_DIR / "templates"

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
    """Crée tous les dossiers nécessaires s'ils n'existent pas."""
    for directory in (DATA_DIR, BACKUP_DIR, OUTPUT_DIR,
                      ICONS_DIR, IMAGES_DIR, STYLES_DIR, TEMPLATES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


# Appelé automatiquement à l'import
ensure_directories()


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

def get_base_dir() -> Path:
    """
    Retourne le dossier racine de l'application, que celle-ci tourne
    depuis les sources Python OU depuis un exécutable PyInstaller.
    """
    if getattr(sys, "frozen", False):
        # Application "gelée" (exécutable PyInstaller)
        # sys.executable = chemin vers DRENAET-RH.exe
        return Path(sys.executable).resolve().parent
    else:
        # Développement : ce fichier est dans config/, la racine est un niveau au-dessus
        return Path(__file__).resolve().parent.parent
 
 
BASE_DIR = get_base_dir()
 
# Les autres chemins (RESOURCES_DIR, IMAGES_DIR, STYLES_DIR, OUTPUT_DIR,
# DATA_DIR...) qui étaient déjà définis relativement à BASE_DIR n'ont
# PAS besoin d'être modifiés : ils continueront de fonctionner tels quels
# puisqu'ils dérivent de BASE_DIR.
#
# Exemple (à titre indicatif, ne remplace que si tu as des lignes similaires) :
#   RESOURCES_DIR = BASE_DIR / "ressources"
#   IMAGES_DIR    = RESOURCES_DIR / "images"
#   STYLES_DIR    = RESOURCES_DIR / "styles"
#   DATA_DIR      = BASE_DIR / "data"
#   OUTPUT_DIR    = BASE_DIR / "outputs"