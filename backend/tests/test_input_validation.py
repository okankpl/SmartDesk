import pytest
from pydantic import ValidationError

from app.models.ticket import TicketPriority
from app.schemas.auth import RegisterRequest
from app.schemas.comment import CommentCreate
from app.schemas.ticket import TicketCreate, TicketUpdate

# Reine Schema-Tests, ohne Datenbank und ohne HTTP: Pydantic-Klassen lassen
# sich direkt aufrufen, genau wie FastAPI es mit dem Request-Body tut. Jeder
# ValidationError hier waere im laufenden Backend eine 422-Antwort.

VALID_REGISTRATION = {"email": "max@firma.de", "password": "geheim123", "full_name": "Max Melder"}


# --- Registrierung ---------------------------------------------------------


def test_register_normalizes_email_to_lowercase():
    payload = RegisterRequest(**{**VALID_REGISTRATION, "email": "Max.Melder@Firma.DE"})

    assert payload.email == "max.melder@firma.de"


@pytest.mark.parametrize("invalid_email", ["", "abc", "max@", "@firma.de", "max firma@firma.de"])
def test_register_rejects_invalid_email(invalid_email):
    with pytest.raises(ValidationError):
        RegisterRequest(**{**VALID_REGISTRATION, "email": invalid_email})


def test_register_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(**{**VALID_REGISTRATION, "password": "kurz"})


def test_register_rejects_password_over_72_bytes():
    """40 x "ü" sind nur 40 ZEICHEN, aber 80 BYTES - genau der Fall, den eine
    reine Zeichen-Pruefung (max_length) uebersehen wuerde."""
    with pytest.raises(ValidationError):
        RegisterRequest(**{**VALID_REGISTRATION, "password": "ü" * 40})


def test_register_keeps_whitespace_in_password():
    """Leerzeichen gehoeren zum Passwort - wuerden sie entfernt, schluege der
    spaetere Login mit dem tatsaechlich eingegebenen Passwort fehl."""
    payload = RegisterRequest(**{**VALID_REGISTRATION, "password": " geheim123 "})

    assert payload.password == " geheim123 "


def test_register_strips_full_name():
    payload = RegisterRequest(**{**VALID_REGISTRATION, "full_name": "  Max Melder  "})

    assert payload.full_name == "Max Melder"


@pytest.mark.parametrize("invalid_name", ["", "   ", "x" * 201])
def test_register_rejects_empty_or_overlong_name(invalid_name):
    with pytest.raises(ValidationError):
        RegisterRequest(**{**VALID_REGISTRATION, "full_name": invalid_name})


# --- Tickets ----------------------------------------------------------------


def test_ticket_create_ignores_client_supplied_status():
    """Mass-Assignment-Schutz: vorher liess sich ein Ticket per
    {"status": "closed"} direkt geschlossen anlegen, an allen
    Lifecycle-Regeln vorbei. Jetzt kennt TicketCreate das Feld nicht mehr."""
    payload = TicketCreate.model_validate({"title": "Drucker kaputt", "status": "closed"})

    assert "status" not in payload.model_dump()


@pytest.mark.parametrize("invalid_title", ["", "   ", "x" * 201])
def test_ticket_create_rejects_empty_or_overlong_title(invalid_title):
    """201 Zeichen passen nicht in String(200) - vorher ein 500-Fehler aus
    PostgreSQL, jetzt ein 422 mit Hinweis aufs Feld."""
    with pytest.raises(ValidationError):
        TicketCreate(title=invalid_title)


def test_ticket_create_rejects_overlong_description():
    with pytest.raises(ValidationError):
        TicketCreate(title="Drucker kaputt", description="x" * 10_001)


@pytest.mark.parametrize("field", ["title", "priority"])
def test_ticket_update_rejects_explicit_null(field):
    """{"title": null} hat vorher versucht, NULL in eine NOT-NULL-Spalte zu
    schreiben - Ergebnis war ein 500-Fehler."""
    with pytest.raises(ValidationError):
        TicketUpdate.model_validate({field: None})


def test_ticket_update_allows_unassigning_via_null():
    """Bei assignee_id ist null dagegen gewollt: "Zuweisung aufheben"."""
    payload = TicketUpdate.model_validate({"assignee_id": None})

    assert payload.model_dump(exclude_unset=True) == {"assignee_id": None}


def test_ticket_update_leaves_omitted_fields_unset():
    """Nur mitgeschickte Felder duerfen im PATCH landen (exclude_unset im
    Router) - die Null-Pruefung darf weggelassene Felder nicht beeinflussen."""
    payload = TicketUpdate.model_validate({"priority": "high"})

    assert payload.model_dump(exclude_unset=True) == {"priority": TicketPriority.HIGH}


# --- Kommentare -------------------------------------------------------------


def test_comment_rejects_overlong_body():
    with pytest.raises(ValidationError):
        CommentCreate(body="x" * 5001)
