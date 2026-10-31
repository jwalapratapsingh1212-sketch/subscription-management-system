"""Business logic for authentication, customer self-registration, and admin staff provisioning."""
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.schemas import (
    AuthTokenResponse,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    StaffCreateRequest,
    UserRegisterRequest,
    UserResponse,
    UserStatusUpdateRequest,
)
from app.core.audit import log_audit_event
from app.core.config import settings
from app.core.permissions import get_customer_for_user
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models import Customer, User


def build_user_response(db: Session, user: User) -> UserResponse:
    customer = get_customer_for_user(db, user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        customer_id=customer.id if customer else None,
        created_at=user.created_at,
    )


def build_token_response(db: Session, user: User) -> AuthTokenResponse:
    user_resp = build_user_response(db, user)
    access_token = create_jwt_token(
        subject=user.id,
        email=user.email,
        role=user.role,
        customer_id=user_resp.customer_id,
        token_type="access",
    )
    refresh_token = create_jwt_token(
        subject=user.id,
        email=user.email,
        role=user.role,
        customer_id=user_resp.customer_id,
        token_type="refresh",
    )
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp,
    )


def register_customer_user(db: Session, payload: UserRegisterRequest) -> AuthTokenResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered.",
        )

    validate_password_strength(payload.password)

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role="customer",
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Link or create Customer record for this user
    existing_customer = (
        db.query(Customer)
        .filter(Customer.email == normalized_email, Customer.user_id.is_(None))
        .first()
    )
    if existing_customer:
        existing_customer.user_id = user.id
        if payload.phone:
            existing_customer.phone = payload.phone
        if payload.billing_address:
            existing_customer.billing_address = payload.billing_address
    else:
        customer = Customer(
            user_id=user.id,
            name=payload.full_name.strip(),
            company_name=payload.company_name,
            email=normalized_email,
            phone=payload.phone,
            billing_address=payload.billing_address or "",
            city=payload.city,
            state=payload.state,
            country=payload.country or "US",
            postal_code=payload.postal_code,
            is_active=True,
        )
        db.add(customer)

    db.flush()
    log_audit_event(
        db,
        action="auth.register_customer",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        metadata={"email": user.email, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return build_token_response(db, user)


def authenticate_user(db: Session, payload: LoginRequest) -> AuthTokenResponse:
    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated.",
        )

    log_audit_event(
        db,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        metadata={"email": user.email, "role": user.role},
    )
    db.commit()
    return build_token_response(db, user)


def create_staff_account(
    db: Session, payload: StaffCreateRequest, admin_user: User
) -> UserResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    validate_password_strength(payload.password)

    staff_user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(staff_user)
    db.flush()
    log_audit_event(
        db,
        action="auth.create_staff",
        entity_type="user",
        entity_id=staff_user.id,
        actor=admin_user,
        metadata={"created_email": staff_user.email, "assigned_role": staff_user.role},
    )
    db.commit()
    db.refresh(staff_user)
    return build_user_response(db, staff_user)


def initiate_password_reset(db: Session, email: str) -> ForgotPasswordResponse:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        # Return consistent message while avoiding user enumeration timing leaks
        return ForgotPasswordResponse(
            message="If that email address is registered, a password reset token has been generated.",
            reset_token=None,
            expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )

    token = create_jwt_token(
        subject=user.id,
        email=user.email,
        role=user.role,
        token_type="reset",
    )
    user.reset_token = token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    log_audit_event(
        db,
        action="auth.forgot_password",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        metadata={"email": user.email},
    )
    db.commit()
    return ForgotPasswordResponse(
        message="Password reset token generated. Use this token at /auth/reset-password.",
        reset_token=token,
        expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    )


def complete_password_reset(db: Session, payload: ResetPasswordRequest) -> dict:
    validate_password_strength(payload.new_password)
    decoded = decode_jwt_token(payload.reset_token, expected_type="reset")
    user_id = int(decoded["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.reset_token != payload.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already-used password reset token.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    log_audit_event(
        db,
        action="auth.reset_password",
        entity_type="user",
        entity_id=user.id,
        actor=user,
    )
    db.commit()
    return {"message": "Password has been reset successfully. You may now log in."}


def list_all_users(db: Session) -> List[UserResponse]:
    users = db.query(User).order_by(User.id.asc()).all()
    return [build_user_response(db, u) for u in users]


def update_user_status(
    db: Session, user_id: int, payload: UserStatusUpdateRequest, admin_user: User
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.is_active is not None:
        if user.id == admin_user.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate their own active account.",
            )
        user.is_active = payload.is_active
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role

    log_audit_event(
        db,
        action="auth.update_user",
        entity_type="user",
        entity_id=user.id,
        actor=admin_user,
        metadata={"is_active": user.is_active, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return build_user_response(db, user)

