from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from app.services.errors import DomainError, InvalidTransitionError, PermissionDeniedError, TicketNotFoundError, ValidationError

# Die EINE Stelle, an der fachliche Fehler (services/errors.py) zu
# HTTP-Statuscodes werden. Die Services selbst kennen keine Statuscodes -
# siehe Docstring von DomainError, warum diese Trennung gewollt ist.
DOMAIN_ERROR_STATUS_CODES: dict[type[DomainError], int] = {
    TicketNotFoundError: status.HTTP_404_NOT_FOUND,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Wandelt einen fachlichen Fehler in eine JSON-Antwort um.

    Dasselbe Antwortformat ({"detail": "..."}) wie bei FastAPIs eigener
    HTTPException - fuer das Frontend und alle anderen Clients sieht ein
    fachlicher Fehler damit genauso aus wie vorher.
    type(exc) ist die konkrete Fehlerklasse (z.B. TicketNotFoundError), nicht
    die Basisklasse - genau danach wird in der Tabelle oben nachgeschlagen.
    """
    return JSONResponse(status_code=DOMAIN_ERROR_STATUS_CODES[type(exc)], content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    """Haengt domain_error_handler fuer ALLE fachlichen Fehler in die App ein.

    Ein Eintrag fuer die Basisklasse reicht: FastAPI (genauer das darunter
    liegende Starlette) sucht bei einer Exception einen Handler fuer deren
    Klasse und, falls es keinen gibt, nacheinander fuer deren Elternklassen.
    """
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(StaleDataError, stale_data_handler)


def stale_data_handler(request: Request, exc: StaleDataError) -> JSONResponse:
    """Versionskonflikt, den SQLAlchemy selbst beim UPDATE erkennt (version_id_col,
    siehe models/ticket.py): als verstaendlicher 409 statt als 500 - bewusst ohne
    die technischen Details aus der Exception."""
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={
        "detail": "Das Ticket wurde inzwischen geändert oder gelöscht. Bitte aktuellen Stand laden.",
    })
