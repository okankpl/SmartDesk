from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])

# Noch KEIN POST /users hier: Nutzer ohne echtes Passwort-Hashing anzulegen waere ein
# unsicherer Workaround, der in Phase 3 (Auth) sofort wieder ersetzt wuerde. Bis dahin
# werden Test-User direkt per SQL angelegt (siehe Migration/README) - dieser Router ist
# nur zum Lesen da, um die Ticket<->User-Verknuepfung ueberhaupt pruefen zu koennen.


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.execute(select(User)).scalars().all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return user
