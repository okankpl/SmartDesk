import json

import pytest
from sqlalchemy.orm.exc import StaleDataError

from app.core.error_handlers import DOMAIN_ERROR_STATUS_CODES, domain_error_handler, stale_data_handler
from app.services.errors import DomainError, InvalidTransitionError, PermissionDeniedError, TicketNotFoundError


def test_every_domain_error_has_a_status_code():
    """Bekommt services/errors.py eine neue Fehlerklasse, aber keinen Eintrag
    in DOMAIN_ERROR_STATUS_CODES, wuerde der Handler mit einem KeyError
    abbrechen - beim Nutzer kaeme ein 500 an statt der gemeinten Antwort.
    __subclasses__() liefert alle Klassen, die direkt von DomainError erben."""
    assert set(DomainError.__subclasses__()) == set(DOMAIN_ERROR_STATUS_CODES)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (TicketNotFoundError("Ticket nicht gefunden"), 404),
        (PermissionDeniedError("Für diesen Statuswechsel fehlt dir die Berechtigung"), 403),
        (InvalidTransitionError("Übergang von 'open' zu 'closed' ist nicht erlaubt"), 409),
    ],
)
def test_domain_error_becomes_json_response_with_matching_status(error, expected_status):
    # request=None: der Handler liest den Request nicht, er braucht nur den Fehler.
    response = domain_error_handler(None, error)

    assert response.status_code == expected_status
    # Dasselbe Format wie bei FastAPIs HTTPException - Clients merken keinen Unterschied.
    assert json.loads(response.body) == {"detail": str(error)}


def test_app_registers_the_domain_error_handler():
    """Die Zuordnung oben nuetzt nichts, wenn main.py den Handler nicht
    einhaengt - dann kaeme jeder fachliche Fehler als 500 beim Nutzer an."""
    from app.main import app

    assert app.exception_handlers[DomainError] is domain_error_handler


def test_stale_orm_changes_return_a_safe_conflict_response():
    from app.main import app

    response = stale_data_handler(None, StaleDataError("Internal database details"))
    assert response.status_code == 409
    assert "inzwischen geändert" in json.loads(response.body)["detail"]
    assert "Internal database details" not in response.body.decode()
    assert app.exception_handlers[StaleDataError] is stale_data_handler
