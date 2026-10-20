from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.login_rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.core.session_cookie import set_session_cookie
from app.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import CurrentUserRead, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """Legt einen neuen Nutzer an. Rolle ist IMMER EMPLOYEE, siehe RegisterRequest.

    Der 409 bei bereits vergebener E-Mail verraet, dass es diese E-Mail gibt -
    ein bewusst in Kauf genommener Kompromiss (siehe Architektur-Doku,
    Abschnitt 9): ihn zu vermeiden, braeuchte eine Bestaetigungs-E-Mail statt
    einer direkten Antwort.
    """
    # Auf dem oeffentlichen Demo-Server ausgeschaltet (REGISTRATION_ENABLED=false):
    # Besucher nutzen dort ihren privaten Demo-Arbeitsbereich, dauerhafte
    # fremde Konten sollen gar nicht erst entstehen.
    if not get_settings().registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Die Registrierung ist in dieser Umgebung deaktiviert.",
        )
    # payload.email ist schon kleingeschrieben (siehe RegisterRequest). func.lower
    # auf der DB-Seite erfasst zusaetzlich aeltere Eintraege, die noch mit
    # Grossbuchstaben gespeichert wurden - sonst liessen sich "Max@firma.de" und
    # "max@firma.de" als zwei getrennte Accounts registrieren.
    existing_user = db.execute(
        select(User).where(func.lower(User.email) == payload.email)
    ).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-Mail bereits registriert")

    user = User(
        email=payload.email,  # bereits normalisiert (kleingeschrieben, ohne Leerzeichen)
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        # Fest verdrahtet, NICHT aus payload - siehe Docstring/RegisterRequest.
        role=UserRole.EMPLOYEE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="E-Mail bereits registriert") from exc
        raise
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse, responses={
    429: {"description": "Login-Budget ausgeschöpft; Retry-After nennt die Sekunden bis zum nächsten Versuch."},
    503: {"description": "Login-Schutz vorübergehend nicht erreichbar; es findet keine Anmeldung statt."},
})
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    rate_limiter: LoginRateLimiter = Depends(get_login_rate_limiter),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Prueft Email (im 'username'-Feld) + Passwort, gibt bei Erfolg einen JWT zurueck.

    Der Token geht auf ZWEI Wegen raus: im JSON-Body (fuer Swagger UI/curl,
    die den Authorization-Header nutzen) UND als HttpOnly-Cookie (fuer das
    Angular-Frontend). Das Frontend soll den Token aus dem JSON-Body bewusst
    NIE selbst speichern - siehe docs/architektur-und-konzepte.md, Abschnitt 6.
    """
    # .strip().lower(): gleiche Normalisierung wie bei der Registrierung, damit
    # "Max@Firma.de " denselben Account findet wie "max@firma.de".
    email = form_data.username.strip().lower()
    # request.client setzt der Server (hinter Caddy: Uvicorns Proxy-Auswertung),
    # nicht ein Header, den die Anwendung selbst ausliest - siehe Architektur-Doku,
    # "Proxy-Vertrauen".
    rate_limiter.enforce(email, request.client.host if request.client else "unknown")
    user = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()

    # Bewusst DIESELBE Fehlermeldung fuer "User existiert nicht" UND "Passwort falsch" -
    # sonst koennte ein Angreifer per unterschiedlicher Fehlermeldung rausfinden,
    # welche Emails ueberhaupt registriert sind.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültige Anmeldedaten",
        headers={"Cache-Control": "no-store"},
    )

    if user is None:
        # Gleiche Meldung allein reicht nicht: bcrypt ist absichtlich langsam
        # (Zehntelsekunden). Ohne diese Zeile kaeme die Antwort bei einer
        # UNBEKANNTEN E-Mail messbar schneller als bei einer bekannten mit
        # falschem Passwort - ein Angreifer koennte registrierte E-Mails also
        # einfach per Stoppuhr erkennen ("Timing-Angriff"). Ein Vergleich gegen
        # einen Dummy-Hash kostet genauso viel Zeit wie ein echter Vergleich.
        verify_password(form_data.password, DUMMY_PASSWORD_HASH)
        raise invalid_credentials

    if not verify_password(form_data.password, user.hashed_password):
        raise invalid_credentials

    token = create_access_token(user_id=user.id, role=user.role)
    # Cookie-Flags (HttpOnly, SameSite, Secure) stehen zentral in core/session_cookie.py.
    set_session_cookie(response, token, max_age_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Loescht den Auth-Cookie. Der JWT selbst bleibt bis zum Ablauf technisch
    gueltig (siehe "Kein Token-Widerruf" in den Bewussten Einschraenkungen) -
    das Frontend hat nach dem Aufruf aber keinen Zugriff mehr darauf, weil der
    Cookie weg ist.
    """
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")


@router.get("/me", response_model=CurrentUserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Liefert den eingeloggten Nutzer. Wird vom Frontend beim Start der App
    aufgerufen, um nach einem Seiten-Reload zu pruefen, ob der HttpOnly-Cookie
    noch gueltig ist - das Frontend kann den Cookie ja nicht selbst auslesen.
    CurrentUserRead enthaelt zusaetzlich demo_expires_at (nur bei Konten eines
    Demo-Arbeitsbereichs gesetzt), fuer die Hinweisleiste im Frontend.
    """
    return current_user
