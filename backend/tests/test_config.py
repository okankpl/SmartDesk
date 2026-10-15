import pytest
from pydantic import ValidationError

from app.core.config import SECRET_KEY_PLACEHOLDER, Settings

DATABASE_URL = "postgresql+psycopg://test:test@localhost:5432/test"


def test_settings_accept_strong_secret_key():
    settings = Settings(database_url=DATABASE_URL, secret_key="a" * 64)

    assert settings.secret_key == "a" * 64


@pytest.mark.parametrize("weak_key", [SECRET_KEY_PLACEHOLDER, "zu-kurz", "x" * 31])
def test_settings_reject_placeholder_or_short_secret_key(weak_key):
    """Der Platzhalter steht oeffentlich in .env.example - wer ihn kennt, kann
    sich selbst gueltige Admin-Tokens signieren. Das Backend soll mit so
    einem Schluessel gar nicht erst starten ("Fail Fast")."""
    with pytest.raises(ValidationError):
        Settings(database_url=DATABASE_URL, secret_key=weak_key)


@pytest.mark.parametrize("uri", ["memory://", "http://example.com", "redis://", ""])
def test_login_limits_require_shared_redis_storage(uri):
    with pytest.raises(ValidationError):
        Settings(database_url=DATABASE_URL, secret_key="a" * 64, login_rate_limit_storage_uri=uri)


@pytest.mark.parametrize("field,value", [
    ("login_rate_limit_ip_attempts", 0),
    ("login_rate_limit_account_attempts", -1),
    ("login_rate_limit_ip_window_seconds", 0),
    ("login_rate_limit_account_window_seconds", 86401),
])
def test_login_limits_reject_invalid_budgets(field, value):
    with pytest.raises(ValidationError):
        Settings(database_url=DATABASE_URL, secret_key="a" * 64, **{field: value})
