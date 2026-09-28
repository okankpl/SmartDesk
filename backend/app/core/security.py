from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# Name des Cookies, in dem der Browser (nicht Swagger/curl - die nutzen weiter
# den Authorization-Header) den JWT nach dem Login speichert. An einer Stelle
# definiert, damit auth.py (setzen/loeschen) und deps.py (lesen) nicht
# auseinanderlaufen koennen.
ACCESS_TOKEN_COOKIE_NAME = "access_token"

# bcrypt erwartet bytes statt str (die zugrundeliegende C-Bibliothek kennt kein
# Python-/Unicode-str). encode()/decode() übersetzen zwischen beiden Welten;
# gespeichert wird der Hash am Ende wieder als str (User.hashed_password: Mapped[str]).

# bcrypt verarbeitet technisch nur die ersten 72 BYTES eines Passworts. Aeltere
# bcrypt-Versionen haben den Rest still abgeschnitten, ab bcrypt 5.0 wird
# stattdessen ein ValueError geworfen - ohne eigene Pruefung fuehrte ein sehr
# langes Passwort deshalb zu einem 500-Fehler. Achtung: BYTES, nicht Zeichen -
# ein "ü" belegt in UTF-8 zwei Bytes.
BCRYPT_MAX_PASSWORD_BYTES = 72

# Ein fester, gueltiger bcrypt-Hash eines zufaelligen Werts, gegen den beim
# Login geprueft wird, wenn es die E-Mail GAR NICHT gibt - siehe login() in
# routers/auth.py (Schutz vor Timing-Angriffen). Einmal beim Modulstart
# erzeugt, nicht bei jedem Aufruf.
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"dummy-password-for-timing-equalization", bcrypt.gensalt()).decode("utf-8")


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

    Ein Passwort ueber 72 Bytes kann nie korrekt sein (die Registrierung
    laesst solche gar nicht erst zu, siehe RegisterRequest) - es liefert
    deshalb False statt eines ValueError aus bcrypt, der sonst beim Login
    als 500-Fehler beim Nutzer ankaeme.
    """
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


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
    abgelaufen ist. Wird von get_current_user (core/deps.py) abgefangen und
    in eine 401-Antwort übersetzt.

    algorithms=[ALGORITHM] ist sicherheitsrelevant: ohne feste Liste koennte
    ein Angreifer im Token-Header einen anderen Algorithmus angeben (z.B.
    "none" = gar keine Signatur) - PyJWT akzeptiert nur, was hier steht.
    """
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
