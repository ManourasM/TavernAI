"""Auth endpoints for signup and login."""

import os
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.dependencies import (
    get_sqlalchemy_session,
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str
    password: str
    roles: Optional[list[str]] = None


class SignupResponse(BaseModel):
    id: int
    username: str
    roles: list[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/signup", response_model=SignupResponse, summary="Create a user (dev/bootstrap)")
async def signup_user(request: SignupRequest, req: Request):
    """
    Create a user for dev/bootstrap.

    Allowed when ENVIRONMENT=dev or when no users exist yet.
    """
    session = get_sqlalchemy_session(req)
    try:
        allow_dev = os.getenv("ENVIRONMENT", "dev").lower() == "dev"
        existing_users = session.query(User).count()
        if not allow_dev and existing_users > 0:
            raise HTTPException(status_code=403, detail="Signup disabled")

        if not request.username or not request.password:
            raise HTTPException(status_code=400, detail="username and password are required")

        if session.query(User).filter(User.username == request.username).first():
            raise HTTPException(status_code=409, detail="username already exists")

        roles = request.roles or []
        user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            roles=roles
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        return SignupResponse(id=user.id, username=user.username, roles=user.roles or [])
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
async def login_user(request: LoginRequest, req: Request):
    """Authenticate a user and return a JWT access token."""
    session = get_sqlalchemy_session(req)
    try:
        user = session.query(User).filter(User.username == request.username).first()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"sub": str(user.id), "roles": user.roles or []},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return TokenResponse(access_token=access_token, token_type="bearer")
    finally:
        session.close()
