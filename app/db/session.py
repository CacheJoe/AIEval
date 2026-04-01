"""Database session and engine factory."""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.utils.config import get_settings

settings = get_settings()


# ---------------------------------------------------------
# Decide database location
# ---------------------------------------------------------

def resolve_database_url() -> str:

    original_url = settings.database_url

    if original_url.startswith("sqlite"):

        # Detect Streamlit environment
        running_on_streamlit = (
            os.getenv("STREAMLIT_SERVER_RUNNING")
            or Path("/mount/src").exists()
        )

        if running_on_streamlit:

            db_path = Path("/tmp/aiales.db")

            # Ensure directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            print("Using writable SQLite database at:", db_path)

            return f"sqlite:///{db_path}"

    return original_url


database_url = resolve_database_url()


# ---------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------

engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "future": True,
}

if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False
    }


engine: Engine = create_engine(
    database_url,
    **engine_kwargs,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db():

    import app.models

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
