from unittest.mock import Mock

from fastapi import HTTPException
from fastapi.testclient import TestClient
from limits.errors import StorageError
from limits.storage import MemoryStorage
import pytest

from app.core.config import get_settings
from app.core.database import get_db
from app.core.login_rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.main import app


def make_limiter(**settings):
    config = get_settings().model_copy(update={
        "login_rate_limit_ip_attempts": 10,
        "login_rate_limit_ip_window_seconds": 60,
        "login_rate_limit_account_attempts": 2,
        "login_rate_limit_account_window_seconds": 300,
        **settings,
    })
    return LoginRateLimiter(config, MemoryStorage())


def test_normalized_account_budget_is_shared_between_different_ips():
    limiter = make_limiter()
    limiter.enforce(" USER@Example.com ", "192.0.2.1")
    limiter.enforce("user@example.com", "192.0.2.2")
    with pytest.raises(HTTPException) as error:
        limiter.enforce("User@example.com", "192.0.2.3")
    assert error.value.status_code == 429
    assert 1 <= int(error.value.headers["Retry-After"]) <= 300
    assert error.value.headers["Cache-Control"] == "no-store"


def test_ip_budget_is_shared_between_different_account_names():
    limiter = make_limiter(login_rate_limit_ip_attempts=2)
    limiter.enforce("one@example.com", "192.0.2.1")
    limiter.enforce("two@example.com", "192.0.2.1")
    with pytest.raises(HTTPException) as error:
        limiter.enforce("three@example.com", "192.0.2.1")
    assert error.value.status_code == 429
    assert 1 <= int(error.value.headers["Retry-After"]) <= 60
    limiter.enforce("three@example.com", "192.0.2.2")


def test_counter_keys_are_fixed_length_hmacs_and_scope_specific():
    limiter = make_limiter()
    email = "person@example.com"
    assert len(limiter.identifier("account", email)) == 64
    assert email not in limiter.identifier("account", email)
    assert limiter.identifier("account", email) != limiter.identifier("ip", email)


def test_expired_window_allows_requests_again(monkeypatch):
    import time

    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)
    limiter = make_limiter(login_rate_limit_account_attempts=1, login_rate_limit_account_window_seconds=5)
    limiter.enforce("user@example.com", "192.0.2.1")
    now += 6
    limiter.enforce("user@example.com", "192.0.2.1")


def test_redis_failure_returns_safe_503_not_an_unlimited_fallback(monkeypatch):
    limiter = make_limiter()

    def unavailable(*args, **kwargs):
        raise StorageError(ConnectionError("private redis credentials must not leak"))

    monkeypatch.setattr(limiter.storage, "acquire_entry", unavailable)
    with pytest.raises(HTTPException) as error:
        limiter.enforce("user@example.com", "192.0.2.1")
    assert error.value.status_code == 503
    assert error.value.headers["Retry-After"] == "30"
    assert "credentials" not in error.value.detail


def test_http_limits_ignore_forwarded_headers_and_skip_db_and_hash_after_rejection(monkeypatch):
    from app.routers import auth

    limiter = make_limiter(login_rate_limit_ip_attempts=1)
    database = Mock()
    database.execute.return_value.scalar_one_or_none.return_value = None
    password_check = Mock(return_value=False)
    monkeypatch.setattr(auth, "verify_password", password_check)
    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    try:
        with TestClient(app, client=("192.0.2.1", 12345)) as client:
            first = client.post("/auth/login", data={"username": "one@example.com", "password": "wrong"})
            assert first.status_code == 401
            database.reset_mock()
            password_check.reset_mock()
            second = client.post("/auth/login", data={"username": "other@example.com", "password": "wrong"}, headers={
                "X-Forwarded-For": "192.0.2.2", "X-Real-IP": "192.0.2.3", "Forwarded": "for=192.0.2.4",
                "Origin": "http://localhost:4200",
            })
            assert second.status_code == 429
            assert "set-cookie" not in second.headers
            assert int(second.headers["Retry-After"]) >= 1
            assert second.headers["access-control-expose-headers"] == "Retry-After"
            database.execute.assert_not_called()
            password_check.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_login_rate_limiter, None)


def test_login_unavailable_has_no_token_cookie_or_database_query(monkeypatch):
    limiter = make_limiter()
    database = Mock()

    def unavailable(*args, **kwargs):
        raise StorageError(ConnectionError("unavailable"))

    monkeypatch.setattr(limiter.storage, "acquire_entry", unavailable)
    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    try:
        with TestClient(app) as client:
            response = client.post("/auth/login", data={"username": "user@example.com", "password": "password"})
            assert response.status_code == 503
            assert "set-cookie" not in response.headers
            assert "access_token" not in response.json()
            database.execute.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_login_rate_limiter, None)
