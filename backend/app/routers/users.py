from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserRead

# dependencies=[...] auf dem ganzen Router: gilt fuer JEDEN Endpunkt darin,
# ohne dass man es an jede einzelne Funktion schreiben muss (und dabei einen
# vergessen kann). Vorher hatte dieser Router GAR KEINE Pruefung - jeder,
# auch ohne Login, konnte E-Mail, Name und Rolle aller Nutzer abrufen.
# AGENT/ADMIN brauchen die Liste z.B. fuer die Zuweisung von Tickets; ein
# EMPLOYEE braucht kein Nutzerverzeichnis (die eigenen Daten liefert /auth/me).
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_roles(UserRole.AGENT, UserRole.ADMIN))],
)

# Kein POST /users: neue Nutzer entstehen ausschliesslich ueber
# POST /auth/register (mit Passwort-Hashing und fest verdrahteter Rolle).


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.execute(select(User)).scalars().all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return user
