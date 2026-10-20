import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from limits.storage import MemoryStorage

from app.core.config import get_settings
from app.core.database import get_db
from app.core.demo_rate_limit import DemoSessionLimiter, get_demo_session_limiter
from app.core.login_rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Integration tests require TEST_DATABASE_URL and migrated PostgreSQL")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to PostgreSQL with a database name ending in _test")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    # Each endpoint may commit. SAVEPOINT keeps those commits inside a test's
    # outer transaction so rollback removes all test data, including events.
    with test_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    limiter = LoginRateLimiter(get_settings(), MemoryStorage())
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    try:
        with TestClient(app) as api:
            yield api
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_login_rate_limiter, None)


@pytest.fixture
def public_demo(client, monkeypatch):
    """Schaltet die oeffentliche Demo fuer einen Test ein und ersetzt die
    Redis-Begrenzung durch einen Zaehler im Speicher (wie die Login-Tests).
    Gibt eine Funktion zurueck, mit der ein Test die Begrenzung enger stellen kann."""
    settings = get_settings()
    monkeypatch.setattr(settings, "public_demo", True)

    def use_limiter():
        limiter = DemoSessionLimiter(settings, MemoryStorage())
        app.dependency_overrides[get_demo_session_limiter] = lambda: limiter

    use_limiter()
    yield use_limiter
    app.dependency_overrides.pop(get_demo_session_limiter, None)
