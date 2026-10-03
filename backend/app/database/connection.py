import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    connect_args = {}
    
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(db_url, connect_args=connect_args, echo=False)
    
    try:
        # Attempt PostgreSQL connection
        engine = create_engine(db_url, pool_pre_ping=True, echo=False)
        # Test connection
        with engine.connect() as conn:
            pass
        logger.info("Connected successfully to PostgreSQL database.")
        return engine
    except Exception as e:
        if settings.POSTGRES_FALLBACK_SQLITE:
            fallback_url = "sqlite:///./data/risk_engine.db"
            logger.warning(
                f"Could not connect to PostgreSQL ({e}). "
                f"Falling back to local SQLite: {fallback_url}"
            )
            return create_engine(fallback_url, connect_args={"check_same_thread": False}, echo=False)
        raise e

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from . import models  # noqa: F401
    from .migrations import run_migrations
    run_migrations()
    logger.info("Database schemas and migrations initialized.")
