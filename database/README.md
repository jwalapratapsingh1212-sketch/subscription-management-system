# Database

The application uses SQLAlchemy models with PostgreSQL as the primary database. The shared database module also supports SQLite for local execution and isolated tests.

## Connection configuration

Settings are loaded from environment variables and the backend `.env` file. Key settings:

- `DATABASE_URL`: primary database URL.
- `FALLBACK_SQLITE_URL`: local SQLite URL.
- `AUTO_FALLBACK_TO_SQLITE`: enables fallback when the PostgreSQL connection cannot be established.

The configured default PostgreSQL URL is a development convenience only. Set credentials explicitly for your environment and never reuse sample passwords in production.

## Data access

The SQLAlchemy engine, declarative `Base`, `SessionLocal`, and FastAPI `get_db` dependency are defined in [backend/app/core/database.py](../backend/app/core/database.py). Models are registered through the backend models package.

The custom `DecimalMoney` type is intended to preserve two-decimal monetary values and avoid ordinary binary floating-point calculations for billing amounts.

## Schema lifecycle

The application startup currently calls `Base.metadata.create_all(bind=engine)`. This creates missing tables but does not manage schema evolution. Use versioned migrations for changes to existing environments.

If an Alembic configuration and migration environment are present in the repository, use the project's configured migration commands; do not assume a migration directory or command that is not checked in.

## Test database

Pytest configures a dedicated SQLite file at `tests/test_subscription_system.db`, initializes the schema, and seeds baseline demo data. The fixture removes the database file at session teardown when possible.

## Data safety

- Back up the database before schema changes.
- Do not commit local database files, real customer records, or production exports.
- Use least-privilege database accounts.
- Validate foreign keys, unique constraints, and tenant scoping.
- Test restore procedures, not only backup creation.
