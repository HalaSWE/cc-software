"""
Database connection — connects to Supabase PostgreSQL
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set in .env file")

engine = create_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"), pool_pre_ping=True, pool_size=5)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency — provides a DB session per request, auto-closes after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
