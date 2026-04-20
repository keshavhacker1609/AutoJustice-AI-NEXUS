"""
AutoJustice AI NEXUS - Database Layer

Current default : SQLite  (zero-setup, single-file, ideal for demos/prototypes)
Production path : PostgreSQL — change DATABASE_URL in .env, nothing else changes.

The entire data layer uses SQLAlchemy ORM.  No raw SQL is written anywhere in the
codebase, so the same Python code runs against SQLite, PostgreSQL, or MySQL without
modification to any business logic.

Migration checklist (SQLite → PostgreSQL):
  1. Set DATABASE_URL=postgresql://user:pass@host:5432/autojustice  in .env
  2. pip install psycopg2-binary
  3. Run: alembic upgrade head  (or recreate tables via Base.metadata.create_all)
  4. Done — all routes, models, and services work unchanged.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Auto-detect engine kwargs based on database dialect.
# SQLite requires check_same_thread=False for FastAPI's async thread pool.
# PostgreSQL / MySQL do not need (and reject) this argument.
_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # PostgreSQL connection pool settings (ignored by SQLite)
    pool_pre_ping=True,          # detect stale connections automatically
    pool_recycle=1800,           # recycle connections every 30 min
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
