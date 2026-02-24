"""FastAPI dependencies for database session injection and auth."""

import os
from datetime import datetime, timedelta
from typing import Optional, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import User
from app.storage import SQLiteStorage, SQLAlchemyStorage


def get_db_session_from_app(request: Request) -> Optional[Session]:
    """
    Extract database session from FastAPI app state.
    
    This function gets the SQLAlchemy session from the FastAPI app instance
    stored in request.app.state.storage. It handles both SQLite storage
    (which has a session) and in-memory storage (which doesn't).
    
    Args:
        request: FastAPI request object
        
    Returns:
        SQLAlchemy Session if using SQLiteStorage, None otherwise
    """
    from sqlalchemy.orm import sessionmaker
    
    storage = request.app.state.storage
    
    if isinstance(storage, SQLiteStorage):
        SessionLocal = sessionmaker(bind=storage.engine)
        return SessionLocal()
    
    return None


async def get_db_session(request: Request):
    """
    FastAPI dependency for injecting database session into route handlers.
    
    Yields a SQLAlchemy session for SQLiteStorage or SQLAlchemyStorage.
    Properly handles session cleanup.
    
    Args:
        request: FastAPI request object
        
    Yields:
        SQLAlchemy Session or None
    """
    from sqlalchemy.orm import sessionmaker
    
    storage = request.app.state.storage
    session = None
    
    try:
        if isinstance(storage, SQLiteStorage):
            SessionLocal = sessionmaker(bind=storage.engine)
            session = SessionLocal()
        elif isinstance(storage, SQLAlchemyStorage):
            SessionLocal = sessionmaker(bind=storage.engine)
            session = SessionLocal()
        yield session
    finally:
        if session is not None:
            session.close()


def get_sqlalchemy_session(request: Request) -> Session:
    """Get SQLAlchemy session from either SQLAlchemyStorage or SQLiteStorage."""
    from sqlalchemy.orm import sessionmaker

    storage = request.app.state.storage
    if isinstance(storage, (SQLAlchemyStorage, SQLiteStorage)):
        SessionLocal = sessionmaker(bind=storage.engine)
        return SessionLocal()

    raise HTTPException(status_code=501, detail="SQLAlchemy storage required")


# ---------- Auth helpers ----------

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get the current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    session = get_sqlalchemy_session(request)
    try:
        user = session.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception
        return user
    finally:
        session.close()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require an admin user."""
    roles = current_user.roles or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


def get_admin_user(allow_dev_bypass: bool = True) -> Optional[dict[str, Any]]:
    """
    Verify user is admin (placeholder with dev bypass).
    
    In dev mode (ENVIRONMENT=dev), bypasses auth check. 
    In production, should validate JWT/token.
    
    Args:
        allow_dev_bypass: Allow bypass in dev mode
        
    Returns:
        Admin user info dict
        
    Raises:
        HTTPException: If not authenticated as admin
    """
    # Dev bypass
    if allow_dev_bypass and os.getenv("ENVIRONMENT", "dev").lower() == "dev":
        return {"id": 0, "role": "dev_admin"}
    
    # TODO: In production, validate JWT token from request headers
    # For now, always require explicit auth
    raise HTTPException(status_code=403, detail="Admin authentication required")
