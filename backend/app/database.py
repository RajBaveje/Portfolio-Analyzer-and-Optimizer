import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

# Explicitly load .env file in backend directory
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=backend_dir / ".env")

# Database Connection String
POSTGRES_USER = os.getenv("POSTGRES_USER") or "postgres_admin"
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") or "dev_password_2026"
POSTGRES_DB = os.getenv("POSTGRES_DB") or "portfolio_db"
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or "localhost"
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or "5432"

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Infrastructure Setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Central Declarative Base
class Base(DeclarativeBase):
    pass

def get_db():
    """FastAPI Dependency helper for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()