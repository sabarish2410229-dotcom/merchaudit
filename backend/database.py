"""
Database engine and session management.

Defaults to a local SQLite file so the project runs with zero setup.
For production, set DATABASE_URL to a Postgres connection string
(e.g. a Neon URL) — SQLAlchemy makes this a one-line swap, no code changes
needed elsewhere.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./merchaudit.db")

# Render (and Heroku) sometimes hand out URLs using the legacy "postgres://"
# scheme, which SQLAlchemy 1.4+/2.x no longer accepts - normalize it.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs this connect_arg for use with FastAPI's threaded request handling;
# Postgres/other engines ignore it if present, but we only pass it when needed.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call repeatedly (no-op if they already exist)."""
    from . import models_db  # noqa: F401  (ensures models are registered on Base)
    Base.metadata.create_all(bind=engine)
