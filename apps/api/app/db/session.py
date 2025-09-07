from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Default to SQLite for development if no DATABASE_URL is provided
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./app.db"

# Convert postgresql:// to postgresql+psycopg:// for psycopg3 compatibility
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1)

# Database engine configuration
engine_kwargs = {}

if "sqlite" in DATABASE_URL:
    # SQLite specific settings
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif "postgresql" in DATABASE_URL:
    # PostgreSQL specific settings
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
