from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.services.errors import InvalidTransitionError, PermissionDeniedError, ValidationError


def validate_assignment(ticket: Ticket, assignee: User | None, current_user: User) -> None:
    """Prueft eine Zuweisung: aktive Tickets behalten immer einen Bearbeiter,
    zugewiesen werden duerfen nur Agents/Admins, und an andere Personen
    (oder von anderen weg) zuweisen duerfen nur Admins."""
    if ticket.status == TicketStatus.CLOSED:
        raise InvalidTransitionError("Geschlossene Tickets können nicht mehr geändert werden")
    # Zweite Schutzlinie der Mandantentrennung: Bearbeiter und Ticket gehoeren
    # zum selben Arbeitsbereich. Der Router weist fremde Personen schon vorher
    # mit 404 ab (get_visible_user) - die Regel gilt hier aber unabhaengig
    # davon, wer validate_assignment aufruft.
    if assignee is not None and assignee.workspace_id != ticket.workspace_id:
        raise ValidationError("Bearbeiter und Ticket müssen zum selben Arbeitsbereich gehören")
    if assignee is not None and assignee.role not in {UserRole.AGENT, UserRole.ADMIN}:
        raise ValidationError("Nur Support-Mitarbeitende oder Admins dürfen Tickets bearbeiten")
    if assignee is None and ticket.status != TicketStatus.OPEN:
        raise InvalidTransitionError("Ein Ticket in Bearbeitung benötigt einen Bearbeiter")
    if current_user.role != UserRole.ADMIN:
        if ticket.assignee_id not in {None, current_user.id}:
            raise PermissionDeniedError("Nur Admins dürfen fremde Tickets neu zuweisen")
        if assignee is not None and assignee.id != current_user.id:
            raise PermissionDeniedError("Nur Admins dürfen Tickets anderen Personen zuweisen")
