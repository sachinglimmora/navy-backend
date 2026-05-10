from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    AccessTokenResponse,
    UserProfile,
)
from app.services.auth_service import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.dependencies import get_current_user, blacklist_token, security_scheme
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=dict)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with service_number + password.
    Returns access_token, refresh_token, and full user profile.
    """
    user = (
        db.query(User)
        .filter(User.service_number == body.service_number, User.is_active == True)
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service number or password",
        )

    # Update last_login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "service_number": user.service_number,
                "name": user.name,
                "rank": user.rank,
                "unit": user.unit,
                "role": user.role,
                "classification_clearance": user.classification_clearance,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
            },
        },
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(body: RefreshRequest):
    """
    Exchange a valid refresh token for a new access token.
    """
    payload = verify_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_data = {"sub": payload.get("sub"), "role": payload.get("role")}
    new_access_token = create_access_token(token_data)

    return {
        "success": True,
        "message": "Token refreshed",
        "data": {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
    }


@router.post("/logout", response_model=dict)
async def logout(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Invalidate the current access token by adding it to the blacklist.
    """
    blacklist_token(auth.credentials)
    return {
        "success": True,
        "message": "Logged out successfully",
        "data": None,
    }


@router.get("/me", response_model=dict)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "success": True,
        "message": "User profile retrieved",
        "data": {
            "id": str(current_user.id),
            "service_number": current_user.service_number,
            "name": current_user.name,
            "rank": current_user.rank,
            "unit": current_user.unit,
            "role": current_user.role,
            "cohort_id": str(current_user.cohort_id) if current_user.cohort_id else None,
            "classification_clearance": current_user.classification_clearance,
            "is_active": current_user.is_active,
            "last_login": (
                current_user.last_login.isoformat() if current_user.last_login else None
            ),
            "created_at": current_user.created_at.isoformat(),
        },
    }