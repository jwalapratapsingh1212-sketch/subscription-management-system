"""HTTP endpoints for authentication, password recovery, and admin staff management."""
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.schemas import (
    AuthTokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    StaffCreateRequest,
    UserRegisterRequest,
    UserResponse,
    UserStatusUpdateRequest,
)
from app.auth.service import (
    authenticate_user,
    build_token_response,
    build_user_response,
    complete_password_reset,
    create_staff_account,
    initiate_password_reset,
    list_all_users,
    register_customer_user,
    update_user_status,
)
from app.core.audit import log_audit_event
from app.core.database import get_db
from app.core.permissions import bearer_scheme, get_current_user, require_admin
from app.core.security import decode_jwt_token, revoke_jwt_token
from app.models import User

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Self-service registration creating a Customer user and linked Customer profile."""
    return register_customer_user(db, payload)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email & password and issue JWT tokens."""
    return authenticate_user(db, payload)


@router.post("/logout")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke current access token and record logout event."""
    if credentials and credentials.credentials:
        revoke_jwt_token(credentials.credentials)
    log_audit_event(
        db,
        action="auth.logout",
        entity_type="user",
        entity_id=current_user.id,
        actor=current_user,
    )
    db.commit()
    return {"message": "Successfully logged out."}


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a fresh access token pair."""
    decoded = decode_jwt_token(payload.refresh_token, expected_type="refresh")
    user_id = int(decoded["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found.")
    return build_token_response(db, user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generate a self-service password reset token."""
    return initiate_password_reset(db, payload.email)


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password using a valid reset token."""
    return complete_password_reset(db, payload)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return current authenticated user profile and customer association."""
    return build_user_response(db, current_user)


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to provision Internal Staff or Administrator accounts."""
    return create_staff_account(db, payload, admin_user)


@router.get("/users", response_model=List[UserResponse])
def get_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to list all user accounts."""
    return list_all_users(db)


@router.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    payload: UserStatusUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to activate/deactivate or update a user's role."""
    return update_user_status(db, user_id, payload, admin_user)

