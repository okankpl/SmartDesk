from app.core.security import (
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
