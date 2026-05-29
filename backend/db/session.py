"""
Database session management.
"""

import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import get_settings

settings = get_settings()


def _sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _probe_sqlite_path(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA user_version")
            conn.execute("CREATE TABLE IF NOT EXISTS __db_probe (id INTEGER)")
            conn.execute("DROP TABLE __db_probe")
            conn.commit()
        return True
    except sqlite3.Error:
        return False


def _resolve_database_url(database_url: str) -> str:
    """Fallback to a writable temp SQLite database when the configured one fails."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return database_url

    raw_path = database_url[len(prefix):]
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    if _probe_sqlite_path(db_path):
        return _sqlite_url_for_path(db_path)

    fallback_path = Path(tempfile.gettempdir()) / "cyber_trainer.db"
    print(
        f"[warning] SQLite database is not writable at {db_path}; "
        f"using {fallback_path}"
    )
    return _sqlite_url_for_path(fallback_path)


DATABASE_URL = _resolve_database_url(settings.DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLiteneed
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI依赖注in: getgetdatalibsession"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """initdatalibtable"""
    Base.metadata.create_all(bind=engine)
