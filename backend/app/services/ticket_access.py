from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.errors import TicketNotFoundError


def is_ticket_visible(ticket: Ticket, current_user: User) -> bool:
    """Darf current_user dieses Ticket sehen? EMPLOYEE nur eigene (selbst
    gemeldete) Tickets, AGENT/ADMIN alle.

    Eine einzige Quelle fuer diese Regel, genutzt fuer das Ticket selbst
    (get_ticket in tickets.py) UND fuer alles, was an einem Ticket "haengt"
    (aktuell: Kommentare in comments.py). Ohne diese gemeinsame Funktion
    stuende dieselbe Pruefung an mehreren Stellen im Code - und koennte sich
    unbemerkt auseinanderentwickeln, genau wie es beim full_name/fullName-
    Feldnamen schon einmal passiert ist.
    """
    if current_user.role == UserRole.EMPLOYEE:
        return ticket.requester_id == current_user.id
    return True


def get_visible_ticket_or_404(ticket: Ticket | None, current_user: User) -> Ticket:
    """Kombiniert "existiert das Ticket?" und "darf current_user es sehen?" zu
    demselben Fehler, TicketNotFoundError - die Web-Schicht macht daraus eine
    404-Antwort (siehe core/error_handlers.py; der Funktionsname folgt dem
    verbreiteten "get_or_404"-Muster).

    Bewusst "nicht gefunden" statt "keine Berechtigung" (403): ein fremdes
    Ticket soll fuer einen Employee nicht mal als existent erkennbar sein
    (Object-Level Authorization / IDOR-Vermeidung, siehe Architektur-Doku
    Abschnitt 6).
    """
    if ticket is None or not is_ticket_visible(ticket, current_user):
        raise TicketNotFoundError("Ticket nicht gefunden")
    return ticket
