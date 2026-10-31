"""Cryptographic password hashing (PBKDF2-HMAC-SHA256), password policy, and RFC 7519 JWT utilities."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import secrets
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException, status

from app.core.config import settings

# In-memory revoked token JTI store for clean logout handling
_REVOKED_JTIS: Set[str] = set()

SPECIAL_CHARS_PATTERN = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]")


def validate_password_strength(password: str) -> None:
    """Validate password policy per architecture guide:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not any(ch.isupper() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter.",
        )
    if not any(ch.islower() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter.",
        )
    if not SPECIAL_CHARS_PATTERN.search(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character (e.g. !@#$%^&*).",
        )


def hash_password(password: str) -> str:
    """Hash a plaintext password using OWASP-recommended PBKDF2-HMAC-SHA256."""
    iterations = 310_000
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Constant-time verification of a password against its stored hash."""
    try:
        algorithm, iterations_str, salt, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(derived.hex(), digest_hex)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("ascii"))


def create_jwt_token(
    subject: int | str,
    email: str,
    role: str,
    customer_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """Create a signed RFC 7519 HS256 JWT token."""
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        elif token_type == "reset":
            expires_delta = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    exp = now + expires_delta
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "customer_id": customer_id,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(12),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Verify signature, expiration, token type, and revocation status of a JWT."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if int(payload.get("exp", 0)) < now_ts:
            raise ValueError("Token has expired")
        if expected_type and payload.get("type") != expected_type:
            raise ValueError("Unexpected token type")
        jti = payload.get("jti")
        if jti and jti in _REVOKED_JTIS:
            raise ValueError("Token has been revoked")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def revoke_jwt_token(token: str) -> None:
    """Revoke a JWT token JTI on logout."""
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
            jti = payload.get("jti")
            if jti:
                _REVOKED_JTIS.add(jti)
    except Exception:
        pass


