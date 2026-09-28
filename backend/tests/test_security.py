import jwt
import pytest

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_different_hash_for_same_input():
    """Zwei Hashes desselben Passworts muessen sich unterscheiden (Salt!)."""
    hash1 = hash_password("mysecretpassword")
    hash2 = hash_password("mysecretpassword")
    assert hash1 != hash2


def test_verify_password_accepts_correct_password():
    """Das richtige Passwort muss gegen seinen eigenen Hash pruefen."""
    password = "mysecretpassword"
    hashed_password = hash_password(password)
    assert verify_password(password, hashed_password) is True


def test_verify_password_rejects_wrong_password():
    """Ein falsches Passwort darf NICHT gegen einen fremden Hash passen."""
    password = "mysecretpassword"
    hashed_password = hash_password(password)
    wrong_password = "wrongpassword"
    assert verify_password(wrong_password, hashed_password) is False


def test_create_and_decode_access_token_roundtrip():
    """Ein erzeugter Token muss sich wieder korrekt decodieren lassen."""
    user_id = 1
    role = "agent"
    token = create_access_token(user_id=user_id, role=role)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role


def test_verify_password_returns_false_instead_of_crashing_for_overlong_password():
    """bcrypt ab Version 5.0 wirft bei mehr als 72 Bytes einen ValueError -
    ohne die Pruefung in verify_password endete ein sehr langes Passwort beim
    Login als 500-Fehler. "ü" belegt 2 Bytes: 40 Zeichen = 80 Bytes."""
    hashed_password = hash_password("mysecretpassword")

    assert verify_password("ü" * 40, hashed_password) is False


def test_dummy_hash_is_a_valid_bcrypt_hash():
    """Der Timing-Schutz beim Login (siehe routers/auth.py) funktioniert nur,
    wenn der Dummy-Hash ein echter bcrypt-Hash ist - sonst waere der
    Vergleich sofort fertig und die Antwortzeit wieder unterscheidbar."""
    assert verify_password("irgendwas", DUMMY_PASSWORD_HASH) is False


def test_decode_rejects_token_signed_with_another_key():
    """Ein Token, den jemand mit einem eigenen Schluessel signiert hat (z.B. mit
    erfundener Admin-Rolle), darf nicht akzeptiert werden."""
    forged_token = jwt.encode({"sub": "1", "role": "admin"}, "x" * 64, algorithm="HS256")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged_token)


def test_decode_rejects_unsigned_token():
    """Klassischer JWT-Angriff: Algorithmus "none" = gar keine Signatur. Wird
    nur abgewehrt, weil decode_access_token eine feste algorithms-Liste
    uebergibt."""
    unsigned_token = jwt.encode({"sub": "1", "role": "admin"}, key=None, algorithm="none")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(unsigned_token)
