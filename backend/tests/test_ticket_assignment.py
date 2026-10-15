import pytest

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.services.errors import InvalidTransitionError, PermissionDeniedError, ValidationError
from app.services.ticket_assignment import validate_assignment


def user(user_id, role):
    return User(id=user_id, role=role)


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.ADMIN])
def test_admin_can_assign_support_staff(role):
    validate_assignment(Ticket(status=TicketStatus.OPEN), user(2, role), user(1, UserRole.ADMIN))


def test_employee_cannot_be_an_assignee():
    with pytest.raises(ValidationError):
        validate_assignment(Ticket(status=TicketStatus.OPEN), user(2, UserRole.EMPLOYEE), user(1, UserRole.ADMIN))


def test_agent_cannot_delegate_to_someone_else():
    with pytest.raises(PermissionDeniedError):
        validate_assignment(Ticket(status=TicketStatus.OPEN), user(2, UserRole.AGENT), user(1, UserRole.AGENT))


def test_active_ticket_cannot_lose_its_assignee():
    with pytest.raises(InvalidTransitionError):
        validate_assignment(Ticket(status=TicketStatus.IN_PROGRESS, assignee_id=2), None, user(1, UserRole.ADMIN))


def test_closed_ticket_cannot_be_reassigned():
    with pytest.raises(InvalidTransitionError):
        validate_assignment(Ticket(status=TicketStatus.CLOSED, assignee_id=2), user(3, UserRole.AGENT), user(1, UserRole.ADMIN))
