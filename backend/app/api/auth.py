"""
Authentication endpoints - Register, Login, API Key management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets
import hashlib

from app.database import get_db
from app.models import User, APIKey
from app.auth.api_key import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    organization: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    api_key: str
    user_id: int
    email: str
    full_name: str
    organization: str
    message: str


# ---------- Helpers ----------

def hash_password(password: str) -> str:
    """Simple SHA-256 password hash. Replace with bcrypt in production."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_api_key() -> str:
    return f"sk_live_{secrets.token_urlsafe(32)}"


# ---------- Endpoints ----------

@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new account and receive your API key.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please login instead."
        )

    # Create user
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        organization=data.organization,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate API key
    raw_key = generate_api_key()
    api_key = APIKey(
        key=raw_key,
        user_id=user.id,
        name="Default Key",
        is_active=True,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365),
        usage_count=0,
    )
    db.add(api_key)
    db.commit()

    return AuthResponse(
        api_key=raw_key,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization=user.organization or "",
        message="Account created successfully. Save your API key — it won't be shown again."
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login and retrieve your active API key.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user or user.hashed_password != hash_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )

    # Get most recent active API key
    api_key = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True,
    ).order_by(APIKey.created_at.desc()).first()

    # If no key exists (or all expired), create a new one
    if not api_key or (api_key.expires_at and api_key.expires_at < datetime.utcnow()):
        raw_key = generate_api_key()
        api_key = APIKey(
            key=raw_key,
            user_id=user.id,
            name="Default Key",
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            usage_count=0,
        )
        db.add(api_key)
        db.commit()
    else:
        raw_key = api_key.key

    return AuthResponse(
        api_key=raw_key,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization=user.organization or "",
        message="Login successful."
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current user info (requires X-API-Key header).
    """
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization": user.organization,
    }