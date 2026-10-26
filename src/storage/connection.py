"""SQLite database connection and session management."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.storage.models import Base

DEFAULT_DB_URL = "sqlite:///./data/omnivore.db"


def get_database_url() -> str:
    """Retrieve DATABASE_URL from environment and ensure parent directory exists."""
    db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    if db_url.startswith("sqlite:///"):
        db_file = Path(db_url.replace("sqlite:///", ""))
        db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_url


engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all SQLAlchemy tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session]:
    """Transactional context manager for database operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()