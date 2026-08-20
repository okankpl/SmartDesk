from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# bcrypt erwartet bytes statt str (die zugrundeliegende C-Bibliothek kennt kein
# Python-/Unicode-str). encode()/decode() übersetzen zwischen beiden Welten;
# gespeichert wird der Hash am Ende wieder als str (User.hashed_password: Mapped[str]).


def hash_password(plain_password: str) -> str:
    """Wandelt ein Klartext-Passwort in einen speicherbaren Hash um.

    Wird bei der Registrierung aufgerufen, BEVOR das Passwort in die
    Datenbank geschrieben wird - das Original wird nie gespeichert.
    """
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Prüft, ob ein eingegebenes Passwort zum gespeicherten Hash passt.

    checkpw liest den Salt aus hashed_password heraus, hasht plain_password
    damit erneut und vergleicht die beiden Hashes - kein eigener Salt nötig.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int, role: str) -> str:
    """Erzeugt einen signierten JWT für einen eingeloggten Nutzer.

    Wird beim Login aufgerufen, NACHDEM verify_password() das Passwort
    bestätigt hat. "sub" und "exp" sind JWT-Standardfelder (subject/expiry),
    die jwt.decode() automatisch auswertet.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),  # "sub" muss laut JWT-Standard ein String sein
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Prüft einen JWT und gibt sein Payload-Dictionary zurück.

    Löst jwt.PyJWTError (oder eine Unterklasse davon, z.B. bei Ablauf
    ExpiredSignatureError) aus, wenn der Token ungültig, gefälscht oder
    abgelaufen ist. Wird von der noch fehlenden get_current_user-Dependency
    abgefangen und in eine 401-Antwort übersetzt.
    """
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
