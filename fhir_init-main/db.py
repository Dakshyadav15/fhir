# filename: db.py
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

# Configure database URL via env or default to local SQLite file
DB_URL = os.getenv("DB_URL", "sqlite:///ayush_lookup.db")

def _make_engine(url: str):
    kwargs = dict(future=True, echo=False, pool_pre_ping=True)
    # SQLite needs this when used from async/web servers with multiple threads
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)

engine = _make_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class LookupLog(Base):
    __tablename__ = "lookup_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, nullable=True, index=True)
    disease_text = Column(String, nullable=False)
    result_json = Column(JSON, nullable=False)  # stored as TEXT JSON in SQLite
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

@contextmanager
def session_scope():
    """Context manager for scripts/jobs."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# FastAPI dependency
def get_db():
    """Yield a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {DB_URL}")
