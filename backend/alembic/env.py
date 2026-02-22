"""Alembic environment configuration for TavernAI database migrations.

This script runs whenever Alembic command-line tools are run.
It targets the canonical models in app.db.models.Base.metadata.
"""

from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config, pool

# Add the backend directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from app.db.models import Base

# Load Alembic config
config = context.config

# Alembic logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    # Check for APP_DATABASE_URL env var
    db_url = os.getenv("APP_DATABASE_URL")
    
    # Default to in-memory SQLite for development/testing if not set
    if not db_url:
        db_url = "sqlite:///./tavern.db"
    
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    In offline mode, the engine is created from a URL string without
    actually making a database connection. This is useful for generating
    SQL without a running database.
    """
    url = get_database_url()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In online mode, a database engine is created and a connection is opened
    so that Alembic can execute statements directly against the database.
    """
    url = get_database_url()
    
    # Create engine based on URL
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
