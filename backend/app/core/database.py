#!/usr/bin/env python3
"""
CodeGuard AI - Database Configuration

This module handles database connections, session management, and initialization
for the CodeGuard AI application using SQLAlchemy with PostgreSQL.
"""

import asyncio
from typing import AsyncGenerator

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()

# Database URL
DATABASE_URL = settings.DATABASE_URL

# For SQLite, we'll use synchronous operations
# Create sync engine
sync_engine = create_engine(
    DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# For compatibility, we'll use the sync engine as the main engine
engine = sync_engine

# Session makers
SessionLocal = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
)

# For compatibility with async code, we'll create a simple wrapper
AsyncSessionLocal = SessionLocal

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_db():
    """
    Dependency to get database session.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_sync_db():
    """Get synchronous database session for migrations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    try:
        # Import all models to ensure they are registered
        from ..models import analysis, user, project
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
            
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


def close_db() -> None:
    """Close database connections."""
    engine.dispose()


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        with SessionLocal() as session:
            session.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


class DatabaseManager:
    """Database manager for handling connections and operations."""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = SessionLocal
    
    def create_session(self):
        """Create a new database session."""
        return self.session_maker()
    
    def execute_query(self, query: str, params: dict = None):
        """Execute a raw SQL query."""
        with self.session_maker() as session:
            result = session.execute(text(query), params or {})
            session.commit()
            return result
    
    def health_check(self) -> dict:
        """Perform database health check."""
        try:
            with self.session_maker() as session:
                result = session.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                return {
                    "status": "healthy",
                    "database": "sqlite",
                    "version": version,
                    "connection": "active"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }


# Global database manager instance
db_manager = DatabaseManager()