"""SQLAlchemy engine, session factory, and Decimal-safe database dependency."""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import Numeric, TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)


class DecimalMoney(TypeDecorator):
    """Database-agnostic NUMERIC(12, 2) type that always returns exact Python Decimal(0.01).

    On PostgreSQL this compiles directly to NUMERIC(precision, scale).
    On SQLite (when used for local isolated testing) it stores exact decimal strings/numerics
    and guarantees Python Decimal quantization without floating-point drift.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int = 12, scale: int = 2, **kwargs):
        super().__init__(precision=precision, scale=scale, asdecimal=True, **kwargs)
        self.scale = scale
        self._quantizer = Decimal("1." + ("0" * scale)) if scale > 0 else Decimal("1")

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        d = Decimal(str(value)).quantize(self._quantizer, rounding=ROUND_HALF_UP)
        if dialect.name == "sqlite":
            return float(d)
        return d

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, float):
            return Decimal(f"{value:.{self.scale}f}").quantize(self._quantizer, rounding=ROUND_HALF_UP)
        return Decimal(str(value)).quantize(self._quantizer, rounding=ROUND_HALF_UP)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""
    pass


def _build_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql") and settings.AUTO_FALLBACK_TO_SQLITE:
        try:
            pg_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 2},
            )
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL database.")
            return pg_engine
        except Exception as exc:
            logger.warning(
                "PostgreSQL server unreachable (%s). Falling back to %s for local execution.",
                exc,
                settings.FALLBACK_SQLITE_URL,
            )
            db_url = settings.FALLBACK_SQLITE_URL

    if db_url.startswith("sqlite"):
        sqlite_engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(sqlite_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return sqlite_engine

    return create_engine(db_url, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
