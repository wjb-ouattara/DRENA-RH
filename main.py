"""
========================================================================
DRENAET-RH — Point d'entrée de l'application
========================================================================
Lance l'application graphique DRENAET-RH.

Au 1er lancement :
- Crée la base de données SQLite
- Génère les 3 comptes par défaut (admin, operateur1, operateur2)
- Charge les 19 structures de la région Hambol
- Génère 80 agents fictifs pour la démonstration

Puis affiche l'écran de login.
"""

import sys
import logging
from pathlib import Path
from src.services.settings_service import SettingsService

# S'assurer que le dossier racine est dans le PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from config import settings
from src.models import init_db, get_session, Utilisateur, Personnel, Structure


# ============================================================
# LOGGING
# ============================================================
def setup_logging():
    """Configure le système de logs."""
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )


# ============================================================
# INITIALISATION
# ============================================================
def initialize_app():
    """Vérifie l'état de la BD et lance le seed si nécessaire."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"  Démarrage de {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    # Créer le schéma (idempotent)
    SettingsService.sync_to_runtime_config()
    init_db()
    logger.info("✓ Schéma BD vérifié")

    # Vérifier si la BD est vide
    with get_session() as db:
        nb_users = db.query(Utilisateur).count()
        nb_structs = db.query(Structure).count()
        nb_pers = db.query(Personnel).count()

    logger.info(f"  Utilisateurs : {nb_users}")
    logger.info(f"  Structures   : {nb_structs}")
    logger.info(f"  Agents       : {nb_pers}")

    # Si la BD est vide, on seed automatiquement
    if nb_users == 0:
        logger.info("→ Base vide, génération des données initiales...")
        from src.utils.seed_data import seed_all
        result = seed_all(nb_agents=80, force=False)
        logger.info(f"✓ Seed terminé : {result}")
        logger.warning("⚠ COMPTES PAR DÉFAUT CRÉÉS — Voir les comptes dans la doc")

    return True


# ============================================================
# MAIN
# ============================================================
def main():
    """Point d'entrée principal."""
    setup_logging()

    try:
        # 1. Initialiser la base de données
        if not initialize_app():
            print("ÉCHEC : impossible d'initialiser l'application.")
            return 1

        # 2. Lancer l'application PyQt6
        from src.ui.app import DrenaetRHApp
        app = DrenaetRHApp()
        return app.run()

    except Exception as e:
        logging.exception(f"Erreur fatale : {e}")
        print(f"\n❌ ERREUR FATALE : {e}")
        print("   Voir le fichier logs/app.log pour les détails")
        return 1


if __name__ == "__main__":
    sys.exit(main())
