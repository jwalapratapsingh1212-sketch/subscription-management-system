"""Pytest configuration and isolated database/TestClient fixtures."""
import os
from pathlib import Path
import socket
import sys

# Ensure backend is importable
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Use a dedicated test SQLite database file
TEST_DB_PATH = (Path(__file__).resolve().parent / "test_subscription_system.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["FALLBACK_SQLITE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SKIP_AUTO_SEED"] = "false"

# On Windows inside restricted sandboxes where loopback TCP socketpair is blocked,
# provide an overlapped pipe socketpair for asyncio's ProactorEventLoop self-wakeup.
if sys.platform == "win32":
    import _winapi
    import asyncio.windows_utils

    class _OverlappedPipeSocket(asyncio.windows_utils.PipeHandle):
        def setblocking(self, flag: bool) -> None:
            pass

        def send(self, data: bytes) -> int:
            _winapi.WriteFile(self.handle, data, True)
            return len(data)

    def _sandbox_safe_socketpair(*args, **kwargs):
        r, w = asyncio.windows_utils.pipe(overlapped=(True, True))
        return _OverlappedPipeSocket(r), _OverlappedPipeSocket(w)

    socket.socketpair = _sandbox_safe_socketpair

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.seeder import seed_demo_data
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initialize clean schema and seed baseline demo data once per test session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
    yield
    engine.dispose()
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except OSError:
        pass


@pytest.fixture()
def db_session():
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

