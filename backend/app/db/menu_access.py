"""Menu access helper for reading latest menu from DB or file fallback."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import MenuVersion, MenuItem


def get_latest_menu(session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get the latest menu from database or fall back to menu.json file.
    
    This provides flexible menu access: prefer DB version if available,
    else fall back to static menu.json for compatibility.
    
    Args:
        session: SQLAlchemy session (if None, returns file-based menu)
        
    Returns:
        Menu dictionary (JSON blob from MenuVersion or static file)
    """
    # Try to load from database if session provided
    if session:
        try:
            stmt = select(MenuVersion).order_by(MenuVersion.created_at.desc()).limit(1)
            latest_version = session.execute(stmt).scalar_one_or_none()
            
            if latest_version:
                return latest_version.json_blob
        except Exception:
            # Fall through to file-based backup
            pass
    
    # Fall back to menu.json file
    return load_menu_json_file()


def load_menu_json_file() -> Dict[str, Any]:
    """
    Load menu from menu.json file.
    
    Searches relative to this module's location.
    
    Returns:
        Menu dictionary
        
    Raises:
        FileNotFoundError: If menu.json not found
    """
    # Try multiple locations
    locations = [
        Path(__file__).parent.parent.parent / "data" / "menu.json",  # backend/data/menu.json
        Path("data/menu.json"),  # Current directory
        Path("backend/data/menu.json"),  # From root
    ]
    
    for menu_file in locations:
        if menu_file.exists():
            with open(menu_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    raise FileNotFoundError(
        f"menu.json not found in any expected location: {[str(p) for p in locations]}"
    )


def get_active_menu_items(session: Session, version_id: Optional[int] = None) -> list:
    """
    Get active menu items for a version.
    
    Args:
        session: SQLAlchemy session
        version_id: Specific version ID, or None for latest
        
    Returns:
        List of active MenuItem objects
    """
    if version_id is None:
        # Get latest version
        stmt = select(MenuVersion).order_by(MenuVersion.created_at.desc()).limit(1)
        latest = session.execute(stmt).scalar_one_or_none()
        if not latest:
            return []
        version_id = latest.id
    
    # Get active items for this version
    stmt = (
        select(MenuItem)
        .where(MenuItem.menu_version_id == version_id)
        .where(MenuItem.is_active == True)
        .order_by(MenuItem.id)
    )
    return session.execute(stmt).scalars().all()


def menu_items_to_dict(items: list) -> Dict[str, Any]:
    """
    Convert MenuItem objects back to menu structure (nested by category).
    
    Args:
        items: List of MenuItem objects
        
    Returns:
        Menu dictionary grouped by category
    """
    menu = {}
    
    for item in items:
        # Use station as category if not present
        category = item.category or item.station
        
        if category not in menu:
            menu[category] = []
        
        menu[category].append({
            "id": item.external_id,
            "name": item.name,
            "price": item.price / 100.0,  # Convert cents back to decimal
            "category": item.category,
            "station": item.station,
            "hidden": not item.is_active,
            "extra_data": item.extra_data,
        })
    
    return menu
