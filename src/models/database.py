"""
Configuration de la connexion à la base de données SQLite.

Utilise SQLAlchemy 2.0 (ORM moderne). L'utilisation d'un ORM nous permet :
- D'écrire des requêtes en Python plutôt qu'en SQL brut
- De migrer facilement vers PostgreSQL plus tard si besoin
  (changer seulement DATABASE_URL dans settings.py)
- De bénéficier de validations automatiques
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from config import settings


# ============================================================
# CLASSE DE BASE POUR TOUS LES MODÈLES
# ============================================================
class Base(DeclarativeBase):
    """
    Classe de base abstraite dont héritent tous les modèles SQLAlchemy.
    """
    pass


# ============================================================
# ENGINE (moteur de connexion)
# ============================================================
engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Active les FK + meilleures performances + concurrence (WAL)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# ============================================================
# SESSION FACTORY
# ============================================================
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session avec commit/rollback auto.

    Usage :
        with get_session() as db:
            personnel = db.query(Personnel).filter_by(matricule="233329C").first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================
# INITIALISATION DE LA BASE
# ============================================================
def init_db() -> None:
    """
    Crée toutes les tables dans la base SQLite si elles n'existent pas.
    """
    # Imports nécessaires pour enregistrer les modèles dans Base.metadata
    from src.models import structure, personnel, document, absence, utilisateur, compteur  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Supprime toutes les tables (DANGER : dev/tests uniquement)."""
    Base.metadata.drop_all(bind=engine)
