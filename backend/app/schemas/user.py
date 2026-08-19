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
