"""Menu management API router."""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import Base
from app.db.models import MenuVersion, MenuItem, Workstation
from app.db.menu_access import get_latest_menu, get_active_menu_items, menu_items_to_dict
from app.db.menu_utils import create_menu_version, upsert_menu_item, menu_version_exists
from app.db.dependencies import get_sqlalchemy_session, require_admin


# Response models
class MenuItemResponse(BaseModel):
    """Menu item response model."""
    id: int
    external_id: Optional[str]
    name: str
    price: float  # Returned as decimal
    category: str
    station: str
    is_active: bool
    extra_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class MenuVersionResponse(BaseModel):
    """Menu version response model."""
    id: int
    created_at: datetime
    created_by_user_id: Optional[int]
    item_count: int
    
    class Config:
        from_attributes = True


class CreateMenuRequest(BaseModel):
    """Request body for creating a new menu version."""
    menu_dict: Dict[str, Any]
    created_by_user_id: Optional[int] = None


class UpdateMenuItemRequest(BaseModel):
    """Request body for updating a menu item."""
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    station: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


# Create router
router = APIRouter(prefix="/api/menu", tags=["menu"])


def _get_available_categories(session: Session) -> List[str]:
    """
    Get list of all workstation slugs (both active and inactive).
    
    Includes inactive workstations so menu items can be reassigned to them
    if they are reactivated later. Returns slugs sorted by name for consistency.
    """
    stmt = (
        select(Workstation.slug)
        .where(Workstation.slug != "waiter")
        .order_by(Workstation.name)
    )
    categories = session.execute(stmt).scalars().all()
    return list(categories)


@router.get("")
async def get_latest_menu_endpoint(
    session: Session = Depends(get_sqlalchemy_session)
) -> Dict[str, Any]:
    """
    Get the latest menu as JSON blob with available categories.
    
    Returns the most recent MenuVersion.json_blob from database,
    or falls back to menu.json file if no versions exist.
    
    Response includes:
    - Menu structure (categories → items)
    - available_categories: List of active workstation slugs for validation
    
    - **Returns**: Full menu structure with available_categories array
    """
    try:
        menu = get_latest_menu(session)
        available_categories = _get_available_categories(session)
        
        # Add available_categories to response
        response = {
            **menu,
            "available_categories": available_categories
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load menu: {e}")


@router.get("/versions")
async def list_menu_versions(
    session: Session = Depends(get_sqlalchemy_session),
    limit: int = Query(10, ge=1, le=100)
) -> List[MenuVersionResponse]:
    """
    List all menu versions (most recent first).
    
    - **limit**: Maximum number of versions to return (default: 10, max: 100)
    - **Returns**: List of version summaries (id, created_at, created_by, item_count)
    """
    try:
        stmt = (
            select(MenuVersion)
            .order_by(MenuVersion.created_at.desc())
            .limit(limit)
        )
        versions = session.execute(stmt).scalars().all()
        
        result = []
        for v in versions:
            # Count active items
            item_stmt = (
                select(MenuItem)
                .where(MenuItem.menu_version_id == v.id)
                .where(MenuItem.is_active == True)
            )
            item_count = len(session.execute(item_stmt).scalars().all())
            
            result.append(MenuVersionResponse(
                id=v.id,
                created_at=v.created_at,
                created_by_user_id=v.created_by_user_id,
                item_count=item_count
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {e}")


@router.get("/{version_id}")
async def get_menu_version(
    version_id: int,
    session: Session = Depends(get_sqlalchemy_session)
) -> Dict[str, Any]:
    """
    Get a specific menu version by ID with available categories.
    
    Returns the menu structure from that version along with
    currently available categories (active workstations).
    
    - **version_id**: Menu version ID
    - **Returns**: Menu structure from that version with available_categories
    """
    try:
        stmt = select(MenuVersion).where(MenuVersion.id == version_id)
        version = session.execute(stmt).scalar_one_or_none()
        
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
        
        available_categories = _get_available_categories(session)
        
        # Add available_categories to response
        response = {
            **version.json_blob,
            "available_categories": available_categories
        }
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load version: {e}")


@router.post("", status_code=201)
async def create_menu_version_endpoint(
    request: CreateMenuRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin: Dict = Depends(require_admin)
) -> Dict:
    """
    Create a new menu version.
    
    Accepts a menu JSON structure, creates MenuVersion record,
    and seeds MenuItem rows. Creates new version even if identical.
    
    **Admin only**
    
    - **menu_dict**: Full menu structure (categories → items)
    - **created_by_user_id**: Optional user ID for audit trail
    - **Returns**: Created version summary
    """
    try:
        # Create version
        from scripts.seed_menu import seed_menu
        from app import nlp
        
        stats = seed_menu(
            session,
            request.menu_dict,
            force=True,  # Always create new version via POST
            created_by_user_id=request.created_by_user_id
        )
        
        session.commit()

        # Refresh NLP menu cache so new items classify immediately
        try:
            nlp.refresh_menu_items(request.menu_dict)
        except Exception as refresh_error:
            print(f"[menu_router] Warning: failed to refresh NLP menu cache: {refresh_error}")
        
        # Return stats directly
        return {
            "version_id": stats['version_id'],
            "items_created": stats['items_created'],
            "items_updated": stats['items_updated']
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create version: {str(e)}")


@router.put("/item/{item_id}")
async def update_menu_item(
    item_id: int,
    request: UpdateMenuItemRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin: Dict = Depends(require_admin)
) -> MenuItemResponse:
    """
    Update a menu item.
    
    Updates specified fields (price, name, category, etc). Other fields unchanged.
    Category is validated against available workstations if provided.
    
    **Admin only**
    
    - **item_id**: MenuItem ID
    - **name**: New name (optional)
    - **price**: New price in euros (optional)
    - **category**: New category (optional) - must match active workstation slug
    - **station**: New station (optional)
    - **extra_data**: New metadata (optional)
    - **Returns**: Updated item
    """
    try:
        stmt = select(MenuItem).where(MenuItem.id == item_id)
        item = session.execute(stmt).scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        # Validate category if provided
        if request.category is not None:
            available_categories = _get_available_categories(session)
            if request.category not in available_categories:
                # Warn but allow - category may become valid later
                print(f"[menu_router] Warning: category '{request.category}' not in available workstations: {available_categories}")
        
        # Update fields
        if request.name is not None:
            item.name = request.name
        if request.price is not None:
            item.price = int(round(request.price * 100))  # Convert to cents
        if request.category is not None:
            item.category = request.category
        if request.station is not None:
            item.station = request.station
        if request.extra_data is not None:
            item.extra_data = request.extra_data
        
        session.commit()
        
        # Return response with price converted to decimal
        return MenuItemResponse(
            id=item.id,
            external_id=item.external_id,
            name=item.name,
            price=item.price / 100.0,  # Convert cents back to decimal
            category=item.category,
            station=item.station,
            is_active=item.is_active,
            extra_data=item.extra_data
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update item: {e}")


@router.delete("/item/{item_id}")
async def delete_menu_item(
    item_id: int,
    session: Session = Depends(get_sqlalchemy_session),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Soft-delete a menu item (mark as inactive).
    
    Does not remove from database, only marks inactive.
    Inactive items won't appear in GET /api/menu.
    
    **Admin only**
    
    - **item_id**: MenuItem ID
    - **Returns**: {"status": "deleted", "item_id": id}
    """
    try:
        stmt = select(MenuItem).where(MenuItem.id == item_id)
        item = session.execute(stmt).scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        # Soft delete
        item.is_active = False
        session.commit()
        
        return {
            "status": "deleted", 
            "item_id": item_id,
            "message": f"Item {item_id} marked as inactive"
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete item: {e}")


@router.get("/active/latest")
async def get_active_menu_items_endpoint(
    session: Session = Depends(get_sqlalchemy_session)
) -> Dict:
    """
    Get all active menu items from the latest version.
    
    Returns only items that are marked as active (is_active=True).
    Returns in original menu structure format (preserving section names).
    
    - **Returns**: Menu structure with active items only
    """
    try:
        # Get the latest version's json_blob
        stmt = select(MenuVersion).order_by(MenuVersion.created_at.desc()).limit(1)
        version = session.execute(stmt).scalar_one_or_none()
        
        if not version:
            return {}
        
        # Get active item IDs
        active_items_stmt = (
            select(MenuItem.external_id)
            .where(MenuItem.menu_version_id == version.id)
            .where(MenuItem.is_active == True)
        )
        active_ids = set(session.execute(active_items_stmt).scalars().all())
        
        # Filter the json_blob to only include active items
        menu_dict = version.json_blob
        filtered_menu = {}
        
        for section_key, items_list in menu_dict.items():
            if not isinstance(items_list, list):
                continue
            
            # Filter to only active items
            filtered_items = [
                item for item in items_list
                if item.get('id') in active_ids
            ]
            
            # Only include category if it has items
            if filtered_items:
                filtered_menu[section_key] = filtered_items
        
        return filtered_menu
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load active items: {str(e)}")
