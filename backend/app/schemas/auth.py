from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES

# Annotated[Typ, Zusatzregeln] haengt Pruefregeln direkt an einen Typ, statt sie
# ans ganze Schema zu haengen. Hier noetig, weil NUR der Name Leerzeichen am
# Rand verlieren soll - ein model_config mit str_strip_whitespace=True (wie in
# schemas/comment.py) wuerde auch das Passwort veraendern: "geheim123 " wuerde
# dann als "geheim123" gespeichert, der Login mit dem echten Passwort
# (inklusive Leerzeichen) schluege danach fehl.
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class RegisterRequest(BaseModel):
    """Eingabedaten fuer POST /auth/register.

    Bewusst KEIN role-Feld: die Rolle wird serverseitig fest auf EMPLOYEE
    gesetzt, damit sich niemand bei der Registrierung selbst admin machen kann.

    Die Laengen-Obergrenzen entsprechen den Spaltenlaengen in models/user.py
    (String(255)/String(200)) - ohne sie wuerde ein zu langer Wert erst beim
    Speichern in PostgreSQL scheitern und als unverstaendlicher 500-Fehler
    zurueckkommen statt als klarer 422 mit Hinweis aufs Feld.
    """

    # EmailStr prueft das E-Mail-Format (braucht das Package email-validator,
    # siehe requirements.txt) - vorher wurde z.B. auch "" oder "abc" akzeptiert.
    email: Annotated[EmailStr, Field(max_length=255)]
    # min_length=8: gaengige Mindestlaenge (auch vom US-Standard NIST SP 800-63B
    # empfohlen). Gilt nur bei der Registrierung - bestehende Konten mit
    # kuerzerem Passwort koennen sich weiter einloggen.
    password: str = Field(min_length=8)
    full_name: FullName

    # @field_validator("email") registriert eine eigene Pruef-/Umwandlungs-
    # funktion fuer genau dieses Feld. Sie laeuft NACH der EmailStr-Pruefung
    # (Standard "after"-Modus), bekommt also schon eine gueltige Adresse.
    # @classmethod ist hier Pflicht: Pydantic ruft die Funktion auf der Klasse
    # auf, nicht auf einem fertigen Objekt (das gibt es waehrend der
    # Validierung ja noch nicht).
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        # E-Mail-Adressen werden in der Praxis ohne Unterscheidung von Gross-/
        # Kleinschreibung behandelt. Einheitlich klein gespeichert, damit
        # "Max@Firma.de" und "max@firma.de" nicht zwei Accounts ergeben.
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # Laenge in BYTES pruefen, nicht in Zeichen - siehe
        # BCRYPT_MAX_PASSWORD_BYTES in core/security.py.
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"Passwort darf hoechstens {BCRYPT_MAX_PASSWORD_BYTES} Bytes lang sein")
        return value


class TokenResponse(BaseModel):
    """Antwortformat fuer POST /auth/login."""

    access_token: str
    # "bearer" ist der Standard-Begriff aus dem OAuth2-Standard fuer "im
    # Authorization-Header als 'Bearer <token>' mitschicken".
    token_type: str = "bearer"
