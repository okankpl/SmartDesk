import pytest
from sqlalchemy.dialects import postgresql

from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.errors import TicketNotFoundError
from app.services.ticket_access import get_visible_ticket_or_404, is_ticket_visible, visible_tickets_query

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

    with pytest.raises(TicketNotFoundError):
        get_visible_ticket_or_404(None, employee)


def test_get_visible_ticket_or_404_raises_404_not_403_for_foreign_ticket():
    """Bewusst derselbe 404 wie bei einem nicht existierenden Ticket, nicht
    403 - ein fremdes Ticket soll nicht mal als existent erkennbar sein."""
    ticket = make_ticket(requester_id=7)
    other_employee = make_user(UserRole.EMPLOYEE, user_id=99)

    with pytest.raises(TicketNotFoundError):
        get_visible_ticket_or_404(ticket, other_employee)


# --- visible_tickets_query: dieselbe Regel als SQL-Abfrage fuer Listen ---


def to_sql(query) -> str:
    """Uebersetzt eine SQLAlchemy-Abfrage in den SQL-Text, den PostgreSQL
    bekaeme - ganz ohne Datenbankverbindung. literal_binds setzt Werte wie die
    User-ID direkt ein (statt Platzhaltern), damit der Test sie sehen kann."""
    return str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_employee_list_query_only_selects_own_tickets():
    employee = make_user(UserRole.EMPLOYEE, user_id=7)

    sql = to_sql(visible_tickets_query(employee))

    assert "WHERE tickets.requester_id = 7" in sql


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.ADMIN])
def test_staff_list_query_selects_all_tickets(role):
    staff = make_user(role, user_id=99)

    sql = to_sql(visible_tickets_query(staff))

    assert "WHERE" not in sql
