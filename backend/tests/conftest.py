import os
from collections.abc import Iterator
from datetime import date

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres@localhost:5432/vyapaaros_test")
os.environ["ENVIRONMENT"] = "test"
os.environ["DEMO_USER_PASSWORD"] = "test-password-123"
os.environ["AI_PROVIDER"] = "mock"
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api import deps  # noqa: E402
from app.core.db import SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed import seed  # noqa: E402

TODAY = date(2026, 10, 5)


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db, TODAY)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Iterator[Session]:
    """Session whose writes are rolled back after each test (commits become savepoints)."""
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    conn.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[deps.get_today] = lambda: TODAY
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": "demo@vyapaaros.in", "password": "test-password-123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
