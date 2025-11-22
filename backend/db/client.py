from __future__ import annotations

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session


load_dotenv()

class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("NEON_DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "NEON_DATABASE_URL is not set. "
        "Set it to your Neon Postgres connection string."
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = f"postgresql+psycopg://{DATABASE_URL.split('://')[-1]}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


@contextmanager
def get_session() -> Session:
    """
    Context manager for DB sessions.

    Usage:
        with get_session() as db:
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
