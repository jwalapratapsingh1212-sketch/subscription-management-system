"""Immutable audit logging helper for administrative and financial operations."""
import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Any,
    actor: Optional[User] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Create an AuditLog entry inside the active database transaction."""
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@automated",
        actor_role=actor.role if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    db.add(entry)
    return entry

