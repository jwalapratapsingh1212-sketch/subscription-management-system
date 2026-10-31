# Tests

The test suite uses pytest and FastAPI's TestClient. Test configuration is centralized in [conftest.py](conftest.py).

## Run tests

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m pytest tests -q
```

To see individual test names and verbose output:

```powershell
python -m pytest tests -v
```

## Test database and fixtures

The test configuration:

1. Adds the backend directory to Python's import path.
2. Points `DATABASE_URL` and `FALLBACK_SQLITE_URL` to a dedicated SQLite database file under `tests/`.
3. Imports the FastAPI application and SQLAlchemy metadata.
4. Drops and recreates the test schema at the start of the pytest session.
5. Seeds baseline demo records.
6. Provides a database session fixture and a FastAPI TestClient fixture.
7. Removes the test database file during session teardown when possible.

The helper `get_auth_headers` logs in with a test account and returns a Bearer authorization header.

## Test organization

Keep tests grouped by the domain or behavior they verify (authentication, customers, products, plans, quotations, subscriptions, invoices, payments, reports, and security). Name tests by observable behavior rather than implementation details.

## Important cautions

- The session-scoped setup recreates the configured test database. Do not point test environment variables at a database containing real data.
- Tests use seeded demo data; test credentials are fixtures, not production accounts.
- A passing unit/API suite does not prove production readiness. Add integration tests for real PostgreSQL behavior, concurrency/idempotency, migration upgrades, and tenant isolation.
- This README describes the fixture setup; it does not claim that the full test suite has been executed successfully.
