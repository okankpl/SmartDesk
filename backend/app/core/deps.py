import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_COOKIE_NAME, decode_access_token
from app.models.user import User, UserRole

# tokenUrl zeigt nur auf die URL, die die Swagger-UI fuer ihr "Authorize"-Formular
# anzeigt - den eigentlichen Token liest OAuth2PasswordBearer bei jeder Anfrage
# selbst aus dem Authorization-Header ("Bearer <token>") und reicht ihn als
# String an die Funktion weiter, die davon abhaengt (hier: get_current_user).
# auto_error=False: wirft selbst KEINEN 401, wenn der Header fehlt - stattdessen
# gibt es einfach None zurueck, damit unten der Cookie als zweite Quelle
# geprueft werden kann (Swagger/curl nutzen den Header, das Angular-Frontend
# den Cookie - siehe docs/architektur-und-konzepte.md, Abschnitt 6).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    bearer_token: str | None = Depends(oauth2_scheme),
    # Cookie(...) ist das Gegenstueck zu Depends()/Query()/Body(): FastAPI liest
    # den Wert automatisch aus dem Cookie-Header der Anfrage. alias, weil der
    # Python-Parametername anders heissen darf als der tatsaechliche Cookie-Name.
    cookie_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    """Ermittelt den eingeloggten Nutzer aus dem mitgeschickten JWT.

    Der Token kann aus zwei Quellen kommen (erste gefundene gewinnt): dem
    Authorization-Header (Swagger UI, curl, Postman) oder dem HttpOnly-Cookie
    (das Angular-Frontend - dort ist der Token per Design nie in JavaScript
    lesbar, siehe Lernnotizen "Token-Speicherung").

    Wird als Depends(get_current_user) in jeden Endpunkt eingehaengt, der eine
    Anmeldung voraussetzt - FastAPI loest die Kette automatisch vor jedem
    Request auf. Vier Faelle fuehren zu 401: kein Token in beiden Quellen,
    Token ungueltig/abgelaufen, die "sub"-Claim fehlt, oder der User aus der
    Claim existiert nicht mehr (z.B. geloescht, obwohl der Token noch laeuft).
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungueltige oder abgelaufene Anmeldedaten",
        # WWW-Authenticate ist der HTTP-Standard-Header, mit dem ein Server bei
        # 401 mitteilt, welches Auth-Schema erwartet wird - hier "Bearer".
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = bearer_token or cookie_token
    if token is None:
        raise unauthorized

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise unauthorized

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthorized

    user = db.get(User, int(user_id))
    if user is None:
        raise unauthorized

    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency-Fabrik: baut eine Dependency, die zusaetzlich zu
    get_current_user prueft, ob die Rolle des Nutzers in allowed_roles
    enthalten ist - sonst 403.

    "Fabrik" heisst hier: require_roles(...) selbst ist keine Dependency,
    sondern eine Funktion, die eine passgenaue Dependency-Funktion ZURUECKGIBT.
    Nutzung: current_user: User = Depends(require_roles(UserRole.ADMIN)).
    Noetig, weil Depends() selbst keine Argumente an die Zielfunktion
    durchreicht - der Trick ist, allowed_roles per Closure "einzubacken",
    bevor FastAPI die zurueckgegebene Funktion als Dependency aufruft.
    """

    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Für diese Aktion fehlt dir die Berechtigung",
            )
        return current_user

    return check_role
