import pytest
from fastapi import HTTPException

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.services.ticket_lifecycle import apply_status_transition, get_allowed_next_statuses

# Ticket/User sind SQLAlchemy-Models, lassen sich aber wie ganz normale Python-
# Objekte instanziieren, solange man sie nie einer DB-Session hinzufuegt - genau
# das machen wir hier. Kein Test-DB-Setup noetig, dieselbe Idee wie bei den reinen
# Funktionen in test_security.py.


def make_user(role: UserRole, user_id: int = 1) -> User:
    return User(id=user_id, email=f"user{user_id}@test.local", hashed_password="x", full_name="Test", role=role)


def make_ticket(status: TicketStatus, requester_id: int = 1) -> Ticket:
    return Ticket(id=1, title="Test-Ticket", status=status, requester_id=requester_id)


def test_agent_can_claim_open_ticket():
    ticket = make_ticket(TicketStatus.OPEN)
    agent = make_user(UserRole.AGENT)

    apply_status_transition(ticket, TicketStatus.IN_PROGRESS, agent)

    assert ticket.status == TicketStatus.IN_PROGRESS


def test_employee_cannot_claim_open_ticket():
    """Nur AGENT/ADMIN duerfen OPEN -> IN_PROGRESS ausloesen, nicht EMPLOYEE."""
    ticket = make_ticket(TicketStatus.OPEN)
    employee = make_user(UserRole.EMPLOYEE)

    with pytest.raises(HTTPException) as exc_info:
        apply_status_transition(ticket, TicketStatus.IN_PROGRESS, employee)

    assert exc_info.value.status_code == 403
    assert ticket.status == TicketStatus.OPEN  # unveraendert geblieben


def test_agent_resolving_ticket_sets_resolved_at():
    ticket = make_ticket(TicketStatus.IN_PROGRESS)
    agent = make_user(UserRole.AGENT)

    apply_status_transition(ticket, TicketStatus.RESOLVED, agent)

    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.resolved_at is not None


def test_only_admin_can_close_resolved_ticket():
    ticket = make_ticket(TicketStatus.RESOLVED)
    agent = make_user(UserRole.AGENT)

    with pytest.raises(HTTPException) as exc_info:
        apply_status_transition(ticket, TicketStatus.CLOSED, agent)

    assert exc_info.value.status_code == 403


def test_admin_closing_ticket_sets_closed_at():
    ticket = make_ticket(TicketStatus.RESOLVED)
    admin = make_user(UserRole.ADMIN)

    apply_status_transition(ticket, TicketStatus.CLOSED, admin)

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.closed_at is not None


def test_requester_can_reject_resolved_ticket():
    requester = make_user(UserRole.EMPLOYEE, user_id=7)
    ticket = make_ticket(TicketStatus.RESOLVED, requester_id=7)

    apply_status_transition(ticket, TicketStatus.IN_PROGRESS, requester)

    assert ticket.status == TicketStatus.IN_PROGRESS


def test_other_employee_cannot_reject_foreign_ticket():
    """Objekt-Ebene-Pruefung: die Rolle EMPLOYEE darf ablehnen, aber nur beim
    eigenen Ticket - nicht bei einem, das ein anderer Mitarbeiter gemeldet hat."""
    ticket = make_ticket(TicketStatus.RESOLVED, requester_id=7)
    other_employee = make_user(UserRole.EMPLOYEE, user_id=99)

    with pytest.raises(HTTPException) as exc_info:
        apply_status_transition(ticket, TicketStatus.IN_PROGRESS, other_employee)

    assert exc_info.value.status_code == 403


def test_nonexistent_transition_raises_conflict():
    """OPEN -> CLOSED existiert nicht in ALLOWED_TRANSITIONS (kein Ueberspringen
    der Pipeline) - auch fuer einen Admin nicht."""
    ticket = make_ticket(TicketStatus.OPEN)
    admin = make_user(UserRole.ADMIN)

    with pytest.raises(HTTPException) as exc_info:
        apply_status_transition(ticket, TicketStatus.CLOSED, admin)

    assert exc_info.value.status_code == 409


def test_closed_ticket_has_no_further_transitions():
    ticket = make_ticket(TicketStatus.CLOSED)
    admin = make_user(UserRole.ADMIN)

    with pytest.raises(HTTPException) as exc_info:
        apply_status_transition(ticket, TicketStatus.IN_PROGRESS, admin)

    assert exc_info.value.status_code == 409


# --- get_allowed_next_statuses: dieselben Regeln, jetzt als Liste statt als
# Exception - die Buttons im Frontend haengen direkt an diesen Ergebnissen. ---


def test_agent_sees_claim_option_on_open_ticket():
    ticket = make_ticket(TicketStatus.OPEN)
    agent = make_user(UserRole.AGENT)

    assert get_allowed_next_statuses(ticket, agent) == [TicketStatus.IN_PROGRESS]


def test_employee_sees_no_options_on_open_ticket():
    """Ein Employee darf bei OPEN gar nichts ausloesen - leere Liste, kein Fehler."""
    ticket = make_ticket(TicketStatus.OPEN)
    employee = make_user(UserRole.EMPLOYEE)

    assert get_allowed_next_statuses(ticket, employee) == []


def test_admin_sees_both_options_on_resolved_ticket():
    """RESOLVED hat zwei moegliche Ziele (CLOSED, IN_PROGRESS) - fuer einen Admin
    sind beide erlaubt, die Reihenfolge folgt der Definition in ALLOWED_TRANSITIONS."""
    ticket = make_ticket(TicketStatus.RESOLVED)
    admin = make_user(UserRole.ADMIN)

    assert get_allowed_next_statuses(ticket, admin) == [TicketStatus.CLOSED, TicketStatus.IN_PROGRESS]


def test_requester_sees_only_reject_option_on_own_resolved_ticket():
    """Employee darf bei RESOLVED grundsaetzlich ablehnen (IN_PROGRESS), aber
    nicht schliessen (CLOSED, nur Admin) - und nur beim eigenen Ticket."""
    requester = make_user(UserRole.EMPLOYEE, user_id=7)
    ticket = make_ticket(TicketStatus.RESOLVED, requester_id=7)

    assert get_allowed_next_statuses(ticket, requester) == [TicketStatus.IN_PROGRESS]


def test_other_employee_sees_no_options_on_foreign_resolved_ticket():
    ticket = make_ticket(TicketStatus.RESOLVED, requester_id=7)
    other_employee = make_user(UserRole.EMPLOYEE, user_id=99)

    assert get_allowed_next_statuses(ticket, other_employee) == []


def test_closed_ticket_has_no_options_for_anyone():
    ticket = make_ticket(TicketStatus.CLOSED)
    admin = make_user(UserRole.ADMIN)

    assert get_allowed_next_statuses(ticket, admin) == []
