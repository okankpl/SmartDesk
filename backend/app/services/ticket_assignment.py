from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.services.errors import InvalidTransitionError, PermissionDeniedError, ValidationError


def validate_assignment(ticket: Ticket, assignee: User | None, current_user: User) -> None:
    """Prueft eine Zuweisung: aktive Tickets behalten immer einen Bearbeiter,
    zugewiesen werden duerfen nur Agents/Admins, und an andere Personen
    (oder von anderen weg) zuweisen duerfen nur Admins."""
    if ticket.status == TicketStatus.CLOSED:
        raise InvalidTransitionError("Geschlossene Tickets können nicht mehr geändert werden")
    if assignee is not None and assignee.role not in {UserRole.AGENT, UserRole.ADMIN}:
        raise ValidationError("Nur Support-Mitarbeitende oder Admins dürfen Tickets bearbeiten")
    if assignee is None and ticket.status != TicketStatus.OPEN:
        raise InvalidTransitionError("Ein Ticket in Bearbeitung benötigt einen Bearbeiter")
    if current_user.role != UserRole.ADMIN:
        if ticket.assignee_id not in {None, current_user.id}:
            raise PermissionDeniedError("Nur Admins dürfen fremde Tickets neu zuweisen")
        if assignee is not None and assignee.id != current_user.id:
            raise PermissionDeniedError("Nur Admins dürfen Tickets anderen Personen zuweisen")
