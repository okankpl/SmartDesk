from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """Legt einen neuen Nutzer an. Rolle ist IMMER EMPLOYEE, siehe RegisterRequest."""
    # TODO 1: pruefen, ob schon ein User mit payload.email existiert.
    #   db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    #   gibt entweder den User oder None zurueck.
    #   Existiert er schon: raise HTTPException(status_code=409, detail="...")

    # TODO 2: payload.password mit hash_password() hashen

    # TODO 3: User(...) erzeugen - email, hashed_password, full_name aus payload,
    #   role=UserRole.EMPLOYEE FEST gesetzt (nicht aus payload!)

    # TODO 4: db.add(...), db.commit(), db.refresh(...), User zurueckgeben
    raise NotImplementedError


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """Prueft Email (im 'username'-Feld) + Passwort, gibt bei Erfolg einen JWT zurueck."""
    # TODO 1: User anhand form_data.username suchen (gleiche select()-Zeile wie oben,
    #   nur mit form_data.username statt payload.email)

    # TODO 2: Falls kein User gefunden ODER verify_password(form_data.password,
    #   user.hashed_password) False ergibt:
    #   raise HTTPException(status_code=401, detail="Ungueltige Anmeldedaten")
    #   Bewusst DIESELBE Fehlermeldung fuer beide Faelle - sonst koennte ein Angreifer
    #   per unterschiedlicher Fehlermeldung rausfinden, welche Emails ueberhaupt
    #   registriert sind.

    # TODO 3: token = create_access_token(user_id=user.id, role=user.role)

    # TODO 4: TokenResponse(access_token=token) zurueckgeben
    raise NotImplementedError
