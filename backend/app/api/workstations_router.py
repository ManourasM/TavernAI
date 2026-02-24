"""Admin workstation management API."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Workstation
from app.db.dependencies import get_sqlalchemy_session, require_admin


router = APIRouter(prefix="/api/workstations", tags=["workstations"])


class WorkstationResponse(BaseModel):
    """Workstation response model."""
    id: int
    name: str
    slug: str
    color: str
    created_at: datetime
    active: bool
    
    class Config:
        from_attributes = True


class CreateWorkstationRequest(BaseModel):
    """Request body for creating a workstation."""
    name: str
    slug: str
    color: str = "#667eea"  # Default to primary color


class UpdateWorkstationRequest(BaseModel):
    """Request body for updating a workstation."""
    name: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None
    active: Optional[bool] = None


@router.get("", response_model=List[WorkstationResponse], summary="List workstations")
async def list_workstations(
    session: Session = Depends(get_sqlalchemy_session)
) -> List[WorkstationResponse]:
    """
    Get all workstations (active and inactive).
    
    Returns all workstations ordered by creation date.
    
    - **Returns**: List of workstations
    """
    try:
        stmt = select(Workstation).order_by(Workstation.created_at)
        workstations = session.execute(stmt).scalars().all()
        return [
            WorkstationResponse(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                color=ws.color,
                created_at=ws.created_at,
                active=ws.active
            )
            for ws in workstations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workstations: {e}")


@router.get("/active", response_model=List[Dict[str, str]], summary="Get active categories")
async def get_active_categories(
    session: Session = Depends(get_sqlalchemy_session)
) -> List[Dict[str, str]]:
    """
    Get list of active workstation categories (slugs).
    
    Returns only workstations with active=True.
    Useful for menu item category validation.
    
    - **Returns**: List of {"slug": "...", "name": "..."} for active workstations
    """
    try:
        stmt = (
            select(Workstation)
            .where(Workstation.active == True)
            .order_by(Workstation.name)
        )
        workstations = session.execute(stmt).scalars().all()
        return [
            {"slug": ws.slug, "name": ws.name}
            for ws in workstations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active categories: {e}")


@router.post("", response_model=WorkstationResponse, status_code=201, summary="Create workstation (admin-only)")
async def create_workstation(
    request: CreateWorkstationRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin = Depends(require_admin)
) -> WorkstationResponse:
    """
    Create a new workstation.
    
    Creates a workstation that can be used as a menu item category.
    
    **Admin only**
    
    - **name**: Human-readable name (e.g., "Grill Station")
    - **slug**: URL-safe identifier (e.g., "grill")
    - **Returns**: Created workstation
    """
    try:
        # Validate input
        if not request.name or not request.slug:
            raise HTTPException(status_code=400, detail="name and slug are required")
        
        # Normalize slug to lowercase
        slug = request.slug.lower().strip()
        if not slug.replace('_', '').replace('-', '').isalnum():
            raise HTTPException(status_code=400, detail="slug must contain only alphanumeric, dash, or underscore")
        
        # Check for duplicate slug
        stmt = select(Workstation).where(Workstation.slug == slug)
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail=f"Workstation with slug '{slug}' already exists")
        
        # Create workstation
        workstation = Workstation(
            name=request.name.strip(),
            slug=slug,
            color=request.color,
            active=True
        )
        session.add(workstation)
        session.commit()
        session.refresh(workstation)
        
        return WorkstationResponse(
            id=workstation.id,
            name=workstation.name,
            slug=workstation.slug,
            color=workstation.color,
            created_at=workstation.created_at,
            active=workstation.active
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create workstation: {e}")


@router.put("/{workstation_id}", response_model=WorkstationResponse, summary="Update workstation (admin-only)")
async def update_workstation(
    workstation_id: int,
    request: UpdateWorkstationRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin = Depends(require_admin)
) -> WorkstationResponse:
    """
    Update a workstation.
    
    Updates specified fields (name, slug, active). Other fields unchanged.
    
    **Admin only**
    
    - **workstation_id**: Workstation ID
    - **name**: New name (optional)
    - **slug**: New slug (optional)
    - **active**: New active status (optional)
    - **Returns**: Updated workstation
    """
    try:
        stmt = select(Workstation).where(Workstation.id == workstation_id)
        workstation = session.execute(stmt).scalar_one_or_none()
        
        if not workstation:
            raise HTTPException(status_code=404, detail=f"Workstation {workstation_id} not found")
        
        # Update fields
        if request.name is not None:
            if not request.name.strip():
                raise HTTPException(status_code=400, detail="name cannot be empty")
            workstation.name = request.name.strip()
        
        if request.slug is not None:
            slug = request.slug.lower().strip()
            if not slug.replace('_', '').replace('-', '').isalnum():
                raise HTTPException(status_code=400, detail="slug must contain only alphanumeric, dash, or underscore")
            
            # Check for duplicate slug (excluding self)
            stmt = (
                select(Workstation)
                .where(Workstation.slug == slug)
                .where(Workstation.id != workstation_id)
            )
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=409, detail=f"Workstation with slug '{slug}' already exists")
            
            workstation.slug = slug
        
        if request.color is not None:
            workstation.color = request.color
        
        if request.active is not None:
            workstation.active = request.active
        
        session.commit()
        session.refresh(workstation)
        
        return WorkstationResponse(
            id=workstation.id,
            name=workstation.name,
            slug=workstation.slug,
            color=workstation.color,
            created_at=workstation.created_at,
            active=workstation.active
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update workstation: {e}")


@router.delete("/{workstation_id}", summary="Delete workstation (admin-only)")
async def delete_workstation(
    workstation_id: int,
    session: Session = Depends(get_sqlalchemy_session),
    admin = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Soft-delete a workstation (mark as inactive).
    
    Does not remove from database, only marks inactive (active=false).
    Inactive workstations won't appear in GET /api/workstations/active.
    
    **Admin only**
    
    - **workstation_id**: Workstation ID
    - **Returns**: {"status": "deleted", "workstation_id": id}
    """
    try:
        stmt = select(Workstation).where(Workstation.id == workstation_id)
        workstation = session.execute(stmt).scalar_one_or_none()
        
        if not workstation:
            raise HTTPException(status_code=404, detail=f"Workstation {workstation_id} not found")
        
        # Soft delete by setting active=false
        workstation.active = False
        session.commit()
        
        return {
            "status": "deleted",
            "workstation_id": workstation_id,
            "message": f"Workstation '{workstation.name}' marked as inactive"
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete workstation: {e}")
