from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserRead
from app.services.user_access import get_visible_user, visible_users_query

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
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[User]:
    # Nur Personen aus dem eigenen Arbeitsbereich (services/user_access.py).
    # current_user per Depends(get_current_user): dieselbe Dependency wie im
    # require_roles des Routers - FastAPI fuehrt sie pro Request nur einmal aus.
    # Alphabetisch nach Namen (id als Tie-Breaker): ohne ORDER BY ist die
    # Reihenfolge in SQL nicht festgelegt - die Bearbeiter-Auswahl im
    # Ticketdialog haette ihre Eintraege sonst in wechselnder Reihenfolge gezeigt.
    return list(db.execute(visible_users_query(current_user).order_by(User.full_name, User.id)).scalars().all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
    # Konten fremder Arbeitsbereiche: dieselbe 404 wie fuer unbekannte IDs.
    user = get_visible_user(db, user_id, current_user)
    if user is None:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return user
