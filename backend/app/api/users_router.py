"""Admin user management API."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.dependencies import get_sqlalchemy_session, require_admin, hash_password


router = APIRouter(prefix="/api/users", tags=["users"])


BASE_ROLES = {"admin", "waiter"}


class UserResponse(BaseModel):
    id: int
    username: str
    roles: list[str]
    created_at: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    roles: list[str] = []


class UpdateUserRequest(BaseModel):
    roles: Optional[list[str]] = None
    password: Optional[str] = None


def _validate_roles(roles: list[str]) -> list[str]:
    if not isinstance(roles, list):
        raise HTTPException(status_code=400, detail="roles must be a list")
    invalid = [
        role
        for role in roles
        if role not in BASE_ROLES and not (isinstance(role, str) and role.startswith("station_"))
    ]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid roles: {', '.join(invalid)}")
    return roles


@router.get("", response_model=list[UserResponse], summary="List users (admin-only)")
async def list_users(
    session: Session = Depends(get_sqlalchemy_session),
    admin: User = Depends(require_admin)
):
    try:
        users = session.query(User).order_by(User.created_at.desc()).all()
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                roles=user.roles or [],
                created_at=user.created_at.isoformat()
            )
            for user in users
        ]
    finally:
        session.close()


@router.post("", response_model=UserResponse, summary="Create user (admin-only)")
async def create_user(
    request: CreateUserRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin: User = Depends(require_admin)
):
    try:
        if not request.username or not request.password:
            raise HTTPException(status_code=400, detail="username and password are required")

        existing = session.query(User).filter(User.username == request.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")

        roles = _validate_roles(request.roles or [])

        user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            roles=roles
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            roles=user.roles or [],
            created_at=user.created_at.isoformat()
        )
    finally:
        session.close()


@router.put("/{user_id}", response_model=UserResponse, summary="Update user (admin-only)")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    session: Session = Depends(get_sqlalchemy_session),
    admin: User = Depends(require_admin)
):
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        if request.roles is not None:
            user.roles = _validate_roles(request.roles)

        if request.password is not None:
            if not request.password:
                raise HTTPException(status_code=400, detail="password cannot be empty")
            user.password_hash = hash_password(request.password)

        session.commit()
        session.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            roles=user.roles or [],
            created_at=user.created_at.isoformat()
        )
    finally:
        session.close()


@router.delete("/{user_id}", summary="Delete user (admin-only)")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_sqlalchemy_session),
    admin: User = Depends(require_admin)
):
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        if "admin" in (user.roles or []):
            raise HTTPException(status_code=403, detail="Cannot delete admin user")

        session.delete(user)
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()
