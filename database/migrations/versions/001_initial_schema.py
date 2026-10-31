"""Initial normalized PostgreSQL schema migration for Subscription Management System.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply initial normalized schema via SQLAlchemy metadata or explicit DDL."""
    from app.core.database import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Reversible downgrade dropping all domain tables in reverse dependency order."""
    from app.core.database import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

