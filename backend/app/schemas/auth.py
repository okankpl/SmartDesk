from pydantic import BaseModel


class RegisterRequest(BaseModel):
    """Eingabedaten fuer POST /auth/register.

    Bewusst KEIN role-Feld: die Rolle wird serverseitig fest auf EMPLOYEE
    gesetzt, damit sich niemand bei der Registrierung selbst admin machen kann.
    """

    email: str
    password: str
    full_name: str


class TokenResponse(BaseModel):
    """Antwortformat fuer POST /auth/login."""

    access_token: str
    # "bearer" ist der Standard-Begriff aus dem OAuth2-Standard fuer "im
    # Authorization-Header als 'Bearer <token>' mitschicken".
    token_type: str = "bearer"
