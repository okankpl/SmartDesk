from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.demo_rate_limit import DemoSessionLimiter, get_demo_session_limiter
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.core.session_cookie import set_session_cookie
from app.models.user import User, UserRole
from app.schemas.demo import DemoConfig, DemoRoleSwitch
from app.schemas.user import CurrentUserRead
from app.services.demo_workspaces import (
    count_active_workspaces,
    create_demo_workspace,
    delete_expired_workspaces,
    find_workspace_member,
)

router = APIRouter(prefix="/demo", tags=["demo"])


def require_public_demo() -> None:
    """Dependency: die Demo-Endpunkte gibt es nur bei PUBLIC_DEMO=true. Sonst
    antworten sie mit 404, als gaebe es sie nicht."""
    if not get_settings().public_demo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nicht gefunden")


def _issue_session(response: Response, user: User, expires_at: datetime) -> None:
    """Meldet user an: der Token gilt genau bis zum Ende des Arbeitsbereichs,
    damit niemand mitten im Ausprobieren nach einer Stunde abgemeldet wird."""
    token = create_access_token(user.id, user.role, expires_at=expires_at)
    remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
    set_session_cookie(response, token, max_age_seconds=max(1, int(remaining)))


@router.get("/config", response_model=DemoConfig)
def demo_config() -> DemoConfig:
    """Oeffentlich und ohne Anmeldung lesbar - die Anmeldeseite braucht die
    Angaben, bevor es eine Sitzung gibt."""
    settings = get_settings()
    return DemoConfig(
        public_demo=settings.public_demo,
        registration_enabled=settings.registration_enabled,
        workspace_ttl_hours=settings.demo_workspace_ttl_hours,
    )


@router.post(
    "/sessions",
    response_model=CurrentUserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_public_demo)],
    responses={
        429: {"description": "Von dieser IP wurden zu viele Demos gestartet; Retry-After nennt die Wartezeit."},
        503: {"description": "Demo ausgelastet oder Begrenzung nicht erreichbar."},
    },
)
def start_demo_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    limiter: DemoSessionLimiter = Depends(get_demo_session_limiter),
) -> User:
    """Legt einen neuen privaten Arbeitsbereich an und meldet als Mitarbeitende an.

    Reihenfolge: erst die IP-Begrenzung (billig, ohne Datenbank), dann
    abgelaufene Bereiche loeschen, dann die Obergrenze pruefen, zuletzt anlegen.
    Die Obergrenze ist eine weiche Grenze: zwei gleichzeitige Anfragen koennen
    sie knapp ueberschreiten - fuer den Schutzzweck (keine tausenden Bereiche)
    reicht das, eine Sperre waere hier unnoetiger Aufwand.
    """
    limiter.enforce(request.client.host if request.client else "unknown")
    settings = get_settings()
    now = datetime.now(timezone.utc)
    delete_expired_workspaces(db, now)
    if count_active_workspaces(db, now) >= settings.demo_max_active_workspaces:
        db.commit()  # das Aufraeumen trotzdem speichern
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Demo ist gerade ausgelastet. Bitte in einigen Minuten erneut versuchen.",
            headers={"Retry-After": "300"},
        )
    workspace = create_demo_workspace(db, now=now, lifetime=timedelta(hours=settings.demo_workspace_ttl_hours))
    db.commit()
    employee = find_workspace_member(db, workspace.id, UserRole.EMPLOYEE)
    _issue_session(response, employee, workspace.expires_at)
    return employee


@router.post("/sessions/role", response_model=CurrentUserRead, dependencies=[Depends(require_public_demo)])
def switch_demo_role(
    payload: DemoRoleSwitch,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Wechselt innerhalb des EIGENEN Arbeitsbereichs zum Konto mit der
    gewuenschten Rolle - ohne Passwort, denn alle drei Konten gehoeren
    derselben Person, die die Demo gestartet hat. Normale Konten
    (workspace_id = NULL) koennen so nie zu einem anderen Konto wechseln."""
    if current_user.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ein Rollenwechsel ist nur in einem Demo-Arbeitsbereich möglich.",
        )
    target = find_workspace_member(db, current_user.workspace_id, payload.role)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diese Rolle gibt es im Arbeitsbereich nicht.")
    _issue_session(response, target, current_user.workspace.expires_at)
    return target
