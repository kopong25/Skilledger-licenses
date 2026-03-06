"""
API Key authentication and authorization
"""
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
import secrets

from app.database import get_db
from app.models import APIKey, User

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """
    Generate a secure random API key
    """
    return f"sk_live_{secrets.token_urlsafe(32)}"


async def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate API key and return associated user
    
    Raises:
        HTTPException: If API key is invalid or inactive
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include 'X-API-Key' header."
        )
    
    # Look up API key
    db_api_key = db.query(APIKey).filter(
        APIKey.key == api_key,
        APIKey.is_active == True
    ).first()
    
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if key has expired
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    # Update last used
    db_api_key.last_used_at = datetime.utcnow()
    db_api_key.usage_count += 1
    db.commit()
    
    # Get associated user
    user = db.query(User).filter(User.id == db_api_key.user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has active subscription
    """
    from app.models import UserSubscription
    
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == user.id,
        UserSubscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required. Please upgrade your plan."
        )
    
    return subscription


def check_rate_limit(
    user: User,
    subscription,
    db: Session
) -> bool:
    """
    Check if user has exceeded monthly verification limit
    
    Returns:
        bool: True if within limit, raises HTTPException if exceeded
    """
    from app.models import UserSubscription, SubscriptionPlan
    
    # Get plan limits
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()
    
    # If unlimited (max_verifications is None), allow
    if plan.max_verifications_per_month is None:
        return True
    
    # Check current usage
    if subscription.verifications_this_month >= plan.max_verifications_per_month:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly verification limit reached ({plan.max_verifications_per_month}). Upgrade your plan or wait for reset."
        )
    
    return True


def increment_usage(
    subscription,
    db: Session
):
    """
    Increment monthly usage counter
    """
    subscription.verifications_this_month += 1
    db.commit()
