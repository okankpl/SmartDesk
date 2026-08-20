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
    existing_user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email bereits registriert")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        # Fest verdrahtet, NICHT aus payload - siehe Docstring/RegisterRequest.
        role=UserRole.EMPLOYEE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """Prueft Email (im 'username'-Feld) + Passwort, gibt bei Erfolg einen JWT zurueck."""
    user = db.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()

    # Bewusst DIESELBE Fehlermeldung fuer "User existiert nicht" UND "Passwort falsch" -
    # sonst koennte ein Angreifer per unterschiedlicher Fehlermeldung rausfinden,
    # welche Emails ueberhaupt registriert sind.
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungueltige Anmeldedaten")

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)
