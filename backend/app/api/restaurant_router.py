"""Restaurant profile management API router."""

import os
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import RestaurantProfile
from app.db.dependencies import get_sqlalchemy_session, require_admin


# Response models
class RestaurantProfileResponse(BaseModel):
    """Restaurant profile response model."""
    id: int
    restaurant_id: str
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    extra_details: Optional[Dict[str, Any]] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UpdateRestaurantProfileRequest(BaseModel):
    """Request body for updating restaurant profile."""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    extra_details: Optional[Dict[str, Any]] = None


# Create router
router = APIRouter(prefix="/api/restaurant", tags=["restaurant"])


def _get_or_create_default_profile(session: Session, restaurant_id: str) -> RestaurantProfile:
    """
    Get existing profile or create default one.
    
    Args:
        session: SQLAlchemy session
        restaurant_id: Restaurant ID from env
        
    Returns:
        RestaurantProfile instance
    """
    stmt = select(RestaurantProfile).where(RestaurantProfile.restaurant_id == restaurant_id)
    profile = session.execute(stmt).scalars().first()
    
    if profile is None:
        # Create default profile with env values or defaults
        profile = RestaurantProfile(
            restaurant_id=restaurant_id,
            name=os.getenv("RESTAURANT_NAME", "My Taverna"),
            phone=os.getenv("RESTAURANT_PHONE"),
            address=os.getenv("RESTAURANT_ADDRESS"),
            extra_details={}
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
    
    return profile


@router.get("", response_model=RestaurantProfileResponse)
async def get_restaurant_profile(
    session: Session = Depends(get_sqlalchemy_session)
) -> RestaurantProfileResponse:
    """
    Get restaurant profile for current RESTAURANT_ID.
    
    Returns the single restaurant profile, or creates a default one if none exists.
    The default values are sourced from environment variables:
    - RESTAURANT_NAME (default: "My Taverna")
    - RESTAURANT_PHONE (optional)
    - RESTAURANT_ADDRESS (optional)
    
    **Returns**: RestaurantProfile with name, phone, address, and metadata
    """
    restaurant_id = os.getenv("RESTAURANT_ID", "default")
    profile = _get_or_create_default_profile(session, restaurant_id)
    return RestaurantProfileResponse.model_validate(profile)


@router.put("", response_model=RestaurantProfileResponse)
async def update_restaurant_profile(
    request: UpdateRestaurantProfileRequest,
    session: Session = Depends(get_sqlalchemy_session),
    current_user = Depends(require_admin)
) -> RestaurantProfileResponse:
    """
    Update restaurant profile (admin-only).
    
    Updates restaurant name, phone, address, and other details.
    All fields are optional; only provided fields are updated.
    
    **Requires**: Admin role (checked via require_admin)
    
    **Args**:
    - name: Restaurant name
    - phone: Contact phone number
    - address: Full address
    - extra_details: JSON object with additional metadata
    
    **Returns**: Updated RestaurantProfile
    """
    restaurant_id = os.getenv("RESTAURANT_ID", "default")
    profile = _get_or_create_default_profile(session, restaurant_id)
    
    # Update only provided fields
    if request.name is not None:
        profile.name = request.name
    if request.phone is not None:
        profile.phone = request.phone
    if request.address is not None:
        profile.address = request.address
    if request.extra_details is not None:
        profile.extra_details = request.extra_details
    
    session.commit()
    session.refresh(profile)
    return RestaurantProfileResponse.model_validate(profile)
