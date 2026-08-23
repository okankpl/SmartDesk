import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# tokenUrl zeigt nur auf die URL, die die Swagger-UI fuer ihr "Authorize"-Formular
# anzeigt - den eigentlichen Token liest OAuth2PasswordBearer bei jeder Anfrage
# selbst aus dem Authorization-Header ("Bearer <token>") und reicht ihn als
# String an die Funktion weiter, die davon abhaengt (hier: get_current_user).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Ermittelt den eingeloggten Nutzer aus dem mitgeschickten JWT.

    Wird als Depends(get_current_user) in jeden Endpunkt eingehaengt, der eine
    Anmeldung voraussetzt - FastAPI loest die Kette (oauth2_scheme -> hier ->
    Endpunkt) automatisch vor jedem Request auf. Drei Faelle fuehren zu 401:
    Token fehlt/ist ungueltig/abgelaufen, die "sub"-Claim fehlt, oder der User
    aus der Claim existiert nicht mehr (z.B. geloescht, obwohl der Token noch
    laeuft).
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungueltige oder abgelaufene Anmeldedaten",
        # WWW-Authenticate ist der HTTP-Standard-Header, mit dem ein Server bei
        # 401 mitteilt, welches Auth-Schema erwartet wird - hier "Bearer".
        headers={"WWW-Authenticate": "Bearer"},
    )

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
