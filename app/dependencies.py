import logging
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import verify_token

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()

# Simple in-process token blacklist (use Redis in production for persistence)
_token_blacklist: set[str] = set()


def blacklist_token(token: str) -> None:
    """Add a token to the in-process blacklist (logout)."""
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    return token in _token_blacklist


async def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that:
    1. Validates the Bearer JWT token
    2. Checks it is not blacklisted
    3. Fetches and returns the active User from the database
    Raises HTTP 401 on any failure.
    """
    token = auth.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception from None

    user = db.query(User).filter(User.id == user_id, User.is_active).first()
    if user is None:
        raise credentials_exception

    return user


def require_roles(*roles: str) -> Callable:
    """
    Returns a FastAPI dependency that enforces role-based access control.
    Raises HTTP 403 if the authenticated user's role is not in the allowed set.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles("admin"))])
        async def admin_endpoint(): ...
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            logger.warning(
                "RBAC denied: user=%s role=%s required=%s",
                current_user.service_number,
                current_user.role,
                roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}",
            )
        return current_user

    return role_checker
