"""Menu utilities for seeding and upserting menu items and versions."""

import json
import hashlib
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import MenuVersion, MenuItem


def hash_menu_json(menu_dict: Dict[str, Any]) -> str:
    """
    Generate a deterministic hash of menu JSON for idempotency detection.
    
    Args:
        menu_dict: The menu dictionary to hash
        
    Returns:
        SHA256 hash of the JSON (sorted keys for consistency)
    """
    # Use separators and sort_keys to ensure consistent JSON representation
    json_str = json.dumps(menu_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def menu_version_exists(session: Session, menu_dict: Dict[str, Any]) -> Optional[MenuVersion]:
    """
    Check if a MenuVersion with identical JSON already exists.
    
    Args:
        session: SQLAlchemy session
        menu_dict: The menu dictionary to check
        
    Returns:
        MenuVersion object if it exists and is identical, else None
    """
    stmt = select(MenuVersion).order_by(MenuVersion.created_at.desc()).limit(1)
    latest = session.execute(stmt).scalar_one_or_none()
    
    if latest and latest.json_blob == menu_dict:
        return latest
    
    return None


def normalize_item_name(name: str) -> str:
    """
    Normalize an item name for matching/deduplication.
    
    Converts to lowercase and removes special characters for matching.
    
    Args:
        name: Item name to normalize
        
    Returns:
        Normalized name
    """
    return name.lower().strip()


def upsert_menu_item(
    session: Session,
    item_dict: Dict[str, Any],
    menu_version_id: int,
    section_key: Optional[str] = None
) -> MenuItem:
    """
    Upsert a menu item (create if not exists, update if exists by external_id).
    
    Matches by external_id if present; otherwise uses normalized name.
    Uses the most recent menu version to find existing items.
    
    Args:
        session: SQLAlchemy session
        item_dict: Item dictionary with keys: id (external), name, price, category, [station]
        menu_version_id: ID of the MenuVersion this item belongs to
        section_key: Optional section key for station mapping if not in item_dict
        
    Returns:
        Created or updated MenuItem object
    """
    external_id = item_dict.get("id")
    name = item_dict.get("name", "")
    price_decimal = item_dict.get("price", 0)
    category = item_dict.get("category", "kitchen")
    station = item_dict.get("station") or section_key or category or "kitchen"
    is_active = not bool(item_dict.get("hidden"))
    extra_data = item_dict.get("extra_data") or item_dict.get("metadata")
    
    # Convert price from decimal to cents (int)
    price_cents = int(round(price_decimal * 100))
    
    # Try to find existing item by external_id first
    existing = None
    if external_id:
        # Find in ANY menu version (not just current)
        stmt = select(MenuItem).where(MenuItem.external_id == external_id)
        existing = session.execute(stmt).scalar_one_or_none()
    
    # If not found by external_id, try by normalized name in current version
    if not existing:
        normalized = normalize_item_name(name)
        stmt = (
            select(MenuItem)
            .where(MenuItem.menu_version_id == menu_version_id)
            .where(MenuItem.name.ilike(name))
        )
        existing = session.execute(stmt).scalar_one_or_none()
    
    if existing:
        # Update existing
        existing.menu_version_id = menu_version_id
        existing.name = name
        existing.price = price_cents
        existing.category = category
        existing.station = station
        existing.is_active = is_active
        existing.extra_data = extra_data
        return existing
    else:
        # Create new
        new_item = MenuItem(
            menu_version_id=menu_version_id,
            external_id=external_id,
            name=name,
            price=price_cents,
            category=category,
            station=station,
            is_active=is_active,
            extra_data=extra_data
        )
        session.add(new_item)
        return new_item


def create_menu_version(
    session: Session,
    menu_dict: Dict[str, Any],
    created_by_user_id: Optional[int] = None
) -> MenuVersion:
    """
    Create a new MenuVersion with the given menu dictionary.
    
    Args:
        session: SQLAlchemy session
        menu_dict: The full menu structure
        created_by_user_id: Optional user ID for who created this version
        
    Returns:
        Created MenuVersion object
    """
    version = MenuVersion(
        json_blob=menu_dict,
        created_by_user_id=created_by_user_id
    )
    session.add(version)
    # Flush to get the ID assigned
    session.flush()
    return version
