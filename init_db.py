#!/usr/bin/env python3
"""
Database initialization script.
This script runs Alembic migrations to set up the database schema.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from alembic import command
from alembic.config import Config
from db.config import load_db_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run Alembic migrations to create/update database schema."""
    try:
        # Load database configuration
        db_config = load_db_config()

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.url)

        # Always start fresh - clean up any existing migration files
        versions_dir = Path("alembic/versions")
        if versions_dir.exists():
            for migration_file in versions_dir.glob("*.py"):
                migration_file.unlink()
                logger.info(f"Removed old migration: {migration_file}")
        
        # Drop alembic_version table to start completely fresh
        try:
            import asyncio
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text as sql_text
            
            async def drop_alembic_table():
                engine = create_async_engine(db_config.url)
                async with engine.begin() as conn:
                    await conn.execute(sql_text("DROP TABLE IF EXISTS alembic_version"))
                await engine.dispose()
            
            asyncio.run(drop_alembic_table())
            logger.info("Dropped existing alembic_version table")
        except Exception as e:
            logger.info(f"Could not drop alembic_version table (may not exist): {e}")
        
        logger.info("Creating fresh initial migration...")
        # Create initial migration based on current models
        command.revision(alembic_cfg, message="Initial migration", autogenerate=True)
        logger.info("Initial migration created.")

        # Run all pending migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migrations completed successfully.")

    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
