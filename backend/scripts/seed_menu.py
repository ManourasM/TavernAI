"""
Seed menu from menu.json into MenuVersion and MenuItem records.

This script provides idempotent menu seeding:
- If identical menu JSON already exists, skip (idempotent)
- If menu JSON differs, create new MenuVersion with updated MenuItems
- Uses external_id for matching when available

Usage:
    python -m scripts.seed_menu [--menu-file path/to/menu.json] [--user-id 1] [--force]
    
Environment:
    APP_DATABASE_URL: Database connection (default: sqlite:///tavern.db)
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_menu_json(menu_file: str) -> Dict[str, Any]:
    """
    Load menu from JSON file.
    
    Args:
        menu_file: Path to menu.json
        
    Returns:
        Parsed menu dictionary
    """
    if not os.path.exists(menu_file):
        raise FileNotFoundError(f"Menu file not found: {menu_file}")
    
    with open(menu_file, 'r', encoding='utf-8') as f:
        menu = json.load(f)
    
    logger.info(f"Loaded menu from {menu_file} with {len(menu)} categories")
    return menu


def seed_menu(
    session: Session,
    menu_dict: Dict[str, Any],
    force: bool = False,
    created_by_user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Seed menu into database idempotently.
    
    Args:
        session: SQLAlchemy session
        menu_dict: Menu dictionary from menu.json
        force: Force create new version even if identical (useful for testing)
        created_by_user_id: Optional user ID for who created this version
        
    Returns:
        Dictionary with statistics: {
            'created_version': bool,
            'version_id': int,
            'items_created': int,
            'items_updated': int
        }
    """
    from app.db.models import MenuVersion, MenuItem
    from app.db.menu_utils import (
        menu_version_exists,
        create_menu_version,
        upsert_menu_item,
        hash_menu_json
    )
    
    stats = {
        'created_version': False,
        'version_id': None,
        'items_created': 0,
        'items_updated': 0
    }
    
    # Check if identical version exists
    if not force:
        existing_version = menu_version_exists(session, menu_dict)
        if existing_version:
            logger.info(
                f"Identical menu version already exists (ID: {existing_version.id}). "
                "Skipping (idempotent). Use --force to override."
            )
            stats['version_id'] = existing_version.id
            return stats
    
    # Create new MenuVersion
    version = create_menu_version(session, menu_dict, created_by_user_id)
    stats['created_version'] = True
    stats['version_id'] = version.id
    
    logger.info(f"Created new MenuVersion (ID: {version.id})")
    
    # Flatten menu structure and create/upsert items
    total_items = 0
    for section_key, items_list in menu_dict.items():
        if not isinstance(items_list, list):
            logger.warning(f"Skipping section '{section_key}' - not a list")
            continue
        
        for item_dict in items_list:
            total_items += 1
            
            # Determine station from category or section
            station = item_dict.get('category', section_key).lower()
            item_dict_with_station = {**item_dict, 'station': station}
            
            # Check if this is a new item or update
            from app.db.models import MenuItem as MenuItemModel
            external_id = item_dict.get('id')
            existing = None
            
            if external_id:
                from sqlalchemy import select
                stmt = select(MenuItemModel).where(MenuItemModel.external_id == external_id)
                existing = session.execute(stmt).scalar_one_or_none()
            
            is_new = existing is None
            
            # Upsert item
            menu_item = upsert_menu_item(
                session,
                item_dict_with_station,
                version.id,
                section_key=section_key
            )
            
            if is_new:
                stats['items_created'] += 1
            else:
                stats['items_updated'] += 1
    
    logger.info(
        f"Processed {total_items} items: "
        f"{stats['items_created']} created, "
        f"{stats['items_updated']} updated"
    )
    
    # Commit transaction
    session.commit()
    logger.info(f"MenuVersion {version.id} committed successfully")
    
    return stats


def get_menu_file_path() -> str:
    """
    Get the path to menu.json, searching from this script's location.
    
    Returns:
        Path to menu.json
    """
    # Try relative to this script first
    script_dir = Path(__file__).parent.parent.parent  # backend/
    menu_file = script_dir / "data" / "menu.json"
    
    if menu_file.exists():
        return str(menu_file)
    
    # Try current directory
    if Path("data/menu.json").exists():
        return "data/menu.json"
    
    # Try from backend
    if Path("backend/data/menu.json").exists():
        return "backend/data/menu.json"
    
    raise FileNotFoundError("Could not find data/menu.json")


def main():
    """Command-line interface for menu seeding."""
    parser = argparse.ArgumentParser(
        description="Seed menu from menu.json into database idempotently"
    )
    parser.add_argument(
        '--menu-file',
        help='Path to menu.json (default: data/menu.json)',
        default=None
    )
    parser.add_argument(
        '--user-id',
        type=int,
        help='User ID for created_by_user_id (optional)',
        default=None
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force create new version even if identical'
    )
    parser.add_argument(
        '--database-url',
        help='Database URL (default: env var APP_DATABASE_URL or sqlite:///tavern.db)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Determine menu file path
    menu_file = args.menu_file or get_menu_file_path()
    logger.info(f"Using menu file: {menu_file}")
    
    # Load menu
    try:
        menu_dict = load_menu_json(menu_file)
    except Exception as e:
        logger.error(f"Failed to load menu: {e}")
        return 1
    
    # Get database URL
    db_url = args.database_url or os.getenv('APP_DATABASE_URL', 'sqlite:///tavern.db')
    logger.info(f"Using database: {db_url}")
    
    # Create engine and session
    from app.db import init_db
    engine = create_engine(db_url)
    init_db(engine, use_alembic=False)  # Use fallback for safety in scripts
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Seed menu
        stats = seed_menu(
            session,
            menu_dict,
            force=args.force,
            created_by_user_id=args.user_id
        )
        
        # Print results
        print("\n" + "="*60)
        print("SEED RESULTS")
        print("="*60)
        print(f"Version ID:       {stats['version_id']}")
        print(f"Version Created:  {stats['created_version']}")
        print(f"Items Created:    {stats['items_created']}")
        print(f"Items Updated:    {stats['items_updated']}")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        session.rollback()
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
