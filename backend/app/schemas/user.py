from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserRead(BaseModel):
    """Oeffentlich sichtbare User-Felder. hashed_password taucht hier bewusst
    NICHT auf - was nicht im Schema steht, kann auch nicht versehentlich als
    JSON rausgehen, selbst wenn man das ganze SQLAlchemy-Objekt uebergibt."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime


class CurrentUserRead(UserRead):
    """Antwort von GET /auth/me und der Demo-Endpunkte: der eingeloggte Nutzer
    plus demo_expires_at - wann sein Demo-Arbeitsbereich geloescht wird (None
    bei normalen Konten). Ein eigenes Schema statt eines Feldes in UserRead,
    weil die Nutzerliste (/users) diese Information nicht braucht."""

    demo_expires_at: datetime | None = None
