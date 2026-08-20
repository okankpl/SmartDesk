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


# --- Spickzettel: die zwei PyJWT-Funktionen, die du brauchst ---
#
# jwt.encode(payload: dict, key: str, algorithm: str) -> str
#   Baut aus einem Dictionary einen signierten JWT-String.
#
# jwt.decode(token: str, key: str, algorithms: list[str]) -> dict
#   Prueft Signatur UND Ablaufzeit ("exp") automatisch, gibt bei Erfolg das
#   urspruengliche Payload-Dictionary zurueck. Wirft bei ungueltiger
#   Signatur oder abgelaufenem Token eine jwt.PyJWTError-Ausnahme (die
#   fangen wir spaeter in einer eigenen Dependency ab, noch nicht hier).


def create_access_token(user_id: int, role: str) -> str:
    """Erzeugt einen signierten JWT fuer einen eingeloggten Nutzer.

    Wird beim Login aufgerufen, NACHDEM verify_password() das Passwort
    bestaetigt hat.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        # "sub" (subject) ist ein JWT-Standardfeld fuer "wer ist das". Muss laut
        # Spezifikation ein String sein, deshalb explizit umgewandelt.
        "sub": str(user_id),
        "role": role,
        # "exp" ist ebenfalls ein Standardfeld - jwt.decode() prueft das automatisch
        # und wirft jwt.ExpiredSignatureError, wenn der Zeitpunkt in der Vergangenheit liegt.
        "exp": expires_at,
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Prueft einen JWT und gibt sein Payload-Dictionary zurueck.

    Loest jwt.PyJWTError (oder eine Unterklasse davon) aus, wenn der Token
    ungueltig, gefaelscht oder abgelaufen ist.
    """
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
