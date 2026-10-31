"""Reusable role-based access control (RBAC) and customer ownership dependencies."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_jwt_token
from app.models import Customer, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate and return the current active user from the Bearer JWT."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_jwt_token(credentials.credentials, expected_type="access")
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory enforcing that current_user has one of the allowed roles."""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _checker


require_admin = require_roles("admin")
require_staff_or_admin = require_roles("admin", "staff")
require_any_authenticated = require_roles("admin", "staff", "customer")


def get_customer_for_user(db: Session, user: User) -> Optional[Customer]:
    """Return the Customer record linked to a customer user."""
    return db.query(Customer).filter(Customer.user_id == user.id).first()


def enforce_customer_ownership(db: Session, current_user: User, resource_customer_id: int) -> None:
    """Ensure a customer user can only access records belonging to their own customer_id."""
    if current_user.role in ("admin", "staff"):
        return
    customer = get_customer_for_user(db, current_user)
    if not customer or customer.id != resource_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to access another customer's records.",
        )

