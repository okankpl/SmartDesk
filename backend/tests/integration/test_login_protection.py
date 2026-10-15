from concurrent.futures import ThreadPoolExecutor
import os
import time
from uuid import uuid4

from fastapi import HTTPException
from limits.storage import RedisStorage
import pytest

from app.core.config import get_settings
from app.core.login_rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.main import app


@pytest.fixture
def redis_limiters():
    uri = os.environ.get("TEST_REDIS_URL")
    if not uri:
        pytest.skip("Redis integration tests require an explicitly configured TEST_REDIS_URL")
    # Never flush a server: only use expiring keys in this test's unique namespace.
    prefix = f"smartdesk:test:login:{uuid4().hex}"
    settings = get_settings().model_copy(update={
        "login_rate_limit_ip_attempts": 100,
        "login_rate_limit_ip_window_seconds": 10,
        "login_rate_limit_account_attempts": 3,
        "login_rate_limit_account_window_seconds": 10,
    })
    return [LoginRateLimiter(settings, RedisStorage(uri, key_prefix=prefix, wrap_exceptions=True)) for _ in range(2)]


def test_redis_coordinates_parallel_attempts_across_backend_instances(redis_limiters):
    def attempt(index):
        try:
            redis_limiters[index % 2].enforce("USER@example.com", f"192.0.2.{index + 1}")
            return 200
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=12) as workers:
        results = list(workers.map(attempt, range(12)))
    assert results.count(200) == 3
    assert results.count(429) == 9


def test_real_redis_releases_expired_budget(redis_limiters):
    original = redis_limiters[0]
    settings = get_settings().model_copy(update={
        "login_rate_limit_account_attempts": 1,
        "login_rate_limit_account_window_seconds": 1,
    })
    limiter = LoginRateLimiter(settings, original.storage)
    limiter.enforce("expiry@example.com", "192.0.2.1")
    with pytest.raises(HTTPException) as error:
        limiter.enforce("expiry@example.com", "192.0.2.1")
    assert error.value.status_code == 429
    time.sleep(1.05)
    limiter.enforce("expiry@example.com", "192.0.2.1")


def test_existing_and_unknown_accounts_have_identical_throttle_responses(client, redis_limiters):
    from tests.integration.test_workflows import register

    register(client)
    app.dependency_overrides[get_login_rate_limiter] = lambda: redis_limiters[0]
    responses = []
    for email in ["employee@example.com", "not-registered@example.com"]:
        for _ in range(3):
            response = client.post("/auth/login", data={"username": email, "password": "wrong"})
            assert response.status_code == 401
            assert response.json() == {"detail": "Ungültige Anmeldedaten"}
        response = client.post("/auth/login", data={"username": email, "password": "integration-password"})
        assert response.status_code == 429
        assert "set-cookie" not in response.headers
        responses.append(response.json())
    assert responses[0] == responses[1]


def test_successful_logins_also_consume_the_request_budget(client, redis_limiters):
    from tests.integration.test_workflows import register

    register(client)
    app.dependency_overrides[get_login_rate_limiter] = lambda: redis_limiters[0]
    for _ in range(3):
        response = client.post("/auth/login", data={"username": "employee@example.com", "password": "integration-password"})
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
    assert client.post("/auth/login", data={"username": "employee@example.com", "password": "integration-password"}).status_code == 429
    # Existing sessions and logout are not subject to the login budget.
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204


def test_unreachable_real_redis_fails_closed():
    storage = RedisStorage("redis://127.0.0.1:1/0", wrap_exceptions=True,
                           socket_timeout=0.1, socket_connect_timeout=0.1)
    limiter = LoginRateLimiter(get_settings(), storage)
    assert limiter.check_storage() is False
    with pytest.raises(HTTPException) as error:
        limiter.enforce("user@example.com", "192.0.2.1")
    assert error.value.status_code == 503
    assert "127.0.0.1" not in error.value.detail
