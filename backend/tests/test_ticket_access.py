import pytest
from fastapi import HTTPException

from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.ticket_access import get_visible_ticket_or_404, is_ticket_visible

# Gleiches Muster wie test_ticket_lifecycle.py: Ticket/User als reine
# Python-Objekte, ohne sie einer DB-Session hinzuzufuegen - keine
# Testdatenbank noetig, weil ticket_access.py selbst nie auf die DB zugreift.


def make_user(role: UserRole, user_id: int = 1) -> User:
    return User(id=user_id, email=f"user{user_id}@test.local", hashed_password="x", full_name="Test", role=role)


def make_ticket(requester_id: int = 1) -> Ticket:
    return Ticket(id=1, title="Test-Ticket", requester_id=requester_id)


def test_employee_sees_own_ticket():
    ticket = make_ticket(requester_id=7)
    employee = make_user(UserRole.EMPLOYEE, user_id=7)

    assert is_ticket_visible(ticket, employee) is True


def test_employee_does_not_see_foreign_ticket():
    ticket = make_ticket(requester_id=7)
    other_employee = make_user(UserRole.EMPLOYEE, user_id=99)

    assert is_ticket_visible(ticket, other_employee) is False


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.ADMIN])
def test_agent_and_admin_see_any_ticket(role):
    """@pytest.mark.parametrize fuehrt DENSELBEN Test mehrfach aus, einmal pro
    Wert in der Liste - spart zwei fast identische Testfunktionen fuer
    AGENT und ADMIN, die sich nur in einem einzigen Wert unterscheiden
    wuerden (DRY auch im Testcode)."""
    ticket = make_ticket(requester_id=7)
    staff = make_user(role, user_id=99)

    assert is_ticket_visible(ticket, staff) is True


def test_get_visible_ticket_or_404_returns_ticket_when_visible():
    ticket = make_ticket(requester_id=7)
    employee = make_user(UserRole.EMPLOYEE, user_id=7)

    assert get_visible_ticket_or_404(ticket, employee) is ticket


def test_get_visible_ticket_or_404_raises_for_missing_ticket():
    employee = make_user(UserRole.EMPLOYEE)

    with pytest.raises(HTTPException) as exc_info:
        get_visible_ticket_or_404(None, employee)

    assert exc_info.value.status_code == 404


def test_get_visible_ticket_or_404_raises_404_not_403_for_foreign_ticket():
    """Bewusst derselbe 404 wie bei einem nicht existierenden Ticket, nicht
    403 - ein fremdes Ticket soll nicht mal als existent erkennbar sein."""
    ticket = make_ticket(requester_id=7)
    other_employee = make_user(UserRole.EMPLOYEE, user_id=99)

    with pytest.raises(HTTPException) as exc_info:
        get_visible_ticket_or_404(ticket, other_employee)

    assert exc_info.value.status_code == 404
