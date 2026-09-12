"""
========================================================================
DRENAET-RH — Script de migration : ajout de la table 'settings'
========================================================================
Ce script ajoute UNIQUEMENT la table 'settings' à une base de données
existante, SANS toucher aux autres tables ni aux données déjà présentes
(agents, structures, absences, documents générés, utilisateurs...).

Usage (une seule fois) :
    python scripts/migrate_add_settings_table.py

Il est prudent de relancer ce script même si la table existe déjà :
il vérifie avant de créer et ne fait rien si elle est déjà là.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect
from src.models.database import Base, engine
from src.models.settings_model import Settings  # noqa: F401 (import nécessaire pour enregistrer le modèle)


def main():
    print("=" * 60)
    print("  Migration : ajout de la table 'settings'")
    print("=" * 60)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "settings" in existing_tables:
        print("\n✓ La table 'settings' existe déjà. Rien à faire.")
        return 0

    print(f"\nTables actuelles en base : {existing_tables}")
    print("\n→ Création de la table 'settings'...")

    # create_all avec tables=[...] ne crée QUE les tables listées,
    # et seulement si elles n'existent pas déjà. Les autres tables
    # et leurs données ne sont absolument pas touchées.
    Base.metadata.create_all(bind=engine, tables=[Settings.__table__])

    # Vérification
    inspector = inspect(engine)
    if "settings" in inspector.get_table_names():
        print("✓ Table 'settings' créée avec succès.")
        print("\nVos données existantes (agents, structures, absences, "
              "documents, utilisateurs) sont intactes.")
        return 0
    else:
        print("✗ Échec : la table n'a pas pu être créée.")
        return 1


if __name__ == "__main__":
    sys.exit(main())