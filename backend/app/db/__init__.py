"""Database models and migrations for TavernAI."""

import os
import sys
from typing import Optional, Any
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base

from app.db.models import Base


def init_db(engine: Engine, use_alembic: bool = True, base: Optional[Any] = None) -> None:
    """
    Initialize database schema using Alembic or create_all fallback.
    
    Args:
        engine: SQLAlchemy engine instance
        use_alembic: If True, run Alembic migrations; else use Base.metadata.create_all()
                    Useful for development: False gives instant schema, True tracks migrations
        base: SQLAlchemy declarative base to use. If None, uses app.db.models.Base.
              Allows backward compatibility with app.storage.models.Base and other schemas.
    
    Raises:
        RuntimeError: If Alembic migration fails or alembic directory not found
    """
    # Use provided base or default to the new db models base
    if base is None:
        base = Base
    
    if use_alembic:
        # Use Alembic for migration tracking (production-safe)
        # Note: Alembic only works with the app.db.models.Base schema that's configured in alembic/env.py
        try:
            from alembic.config import Config
            from alembic import command
            
            # Get the backend directory (one level up from this file: app/db/__init__.py -> backend/)
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            alembic_ini = os.path.join(backend_dir, "alembic.ini")
            
            if not os.path.exists(alembic_ini):
                raise RuntimeError(f"alembic.ini not found at {alembic_ini}")
            
            # Configure Alembic
            config = Config(alembic_ini)
            
            # Run upgrade to apply all pending migrations
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, "head")
                
        except ImportError:
            raise RuntimeError("Alembic not installed. Install with: pip install alembic")
        except Exception as e:
            raise RuntimeError(f"Alembic migration failed: {e}")
    else:
        # Fallback: create only missing tables (preserve existing data for development)
        print(f"[init_db] Creating missing tables from {base.__name__} schema (preserving existing data)...")
        try:
            base.metadata.create_all(engine)
            print(f"[init_db] [OK] Schema synchronized successfully (no data was dropped)")
        except Exception as e:
            print(f"[init_db] [WARNING] Error creating tables: {e}")
            raise RuntimeError(f"Failed to create database tables: {e}")



__all__ = ["Base", "init_db"]
