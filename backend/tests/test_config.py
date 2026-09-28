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
