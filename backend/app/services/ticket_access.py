from sqlalchemy import Select, select

from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.errors import TicketNotFoundError
from app.services.workspace_scope import same_workspace


def visible_tickets_query(current_user: User) -> Select[tuple[Ticket]]:
    """Dieselbe Sichtbarkeitsregel wie is_ticket_visible unten, aber als
    Datenbank-Abfrage fuer LISTEN (GET /tickets): nur Tickets aus dem eigenen
    Arbeitsbereich, und davon bekommt EMPLOYEE per SQL-WHERE nur selbst
    gemeldete Tickets, AGENT/ADMIN alle.

    Als Abfrage statt als Python-Filter, damit fremde Tickets gar nicht erst
    aus der Datenbank geladen werden. Gibt die Abfrage nur ZURUECK, statt sie
    auszufuehren - der Aufrufer kann sie noch erweitern (z.B. sortieren, siehe
    list_tickets), und der Test kann das erzeugte SQL pruefen, ohne
    Datenbank. Select[tuple[Ticket]] ist SQLAlchemys Typ fuer "eine
    SELECT-Abfrage, deren Zeilen je ein Ticket enthalten".
    same_workspace (services/workspace_scope.py) formuliert die Bedingung
    auch fuer normale Konten (workspace_id = NULL) korrekt.
    """
    query = select(Ticket).where(same_workspace(Ticket.workspace_id, current_user.workspace_id))
    if current_user.role == UserRole.EMPLOYEE:
        query = query.where(Ticket.requester_id == current_user.id)
    return query


def is_ticket_visible(ticket: Ticket, current_user: User) -> bool:
    """Darf current_user dieses Ticket sehen? Nur aus dem eigenen
    Arbeitsbereich - und dort EMPLOYEE nur eigene (selbst gemeldete) Tickets,
    AGENT/ADMIN alle.

    Eine einzige Quelle fuer diese Regel (fuer Listen in Form von
    visible_tickets_query oben), genutzt fuer jeden Endpunkt, der ein
    einzelnes Ticket laedt: Detail, Status, Bearbeiten, Loeschen - und alles,
    was an einem Ticket "haengt" (Kommentare, Historie). Ohne diese gemeinsame
    Funktion stuende dieselbe Pruefung an mehreren Stellen im Code - und
    koennte sich unbemerkt auseinanderentwickeln, genau wie es beim
    full_name/fullName-Feldnamen schon einmal passiert ist.
    """
    # Erste Grenze fuer ALLE Rollen: der Arbeitsbereich. Auch ein Demo-Admin
    # sieht nur seinen eigenen. In Python ist None == None True - normale
    # Tickets und normale Konten (beide ohne Arbeitsbereich) passen also
    # zusammen, anders als bei "= NULL" in SQL (siehe same_workspace).
    if ticket.workspace_id != current_user.workspace_id:
        return False
    if current_user.role == UserRole.EMPLOYEE:
        return ticket.requester_id == current_user.id
    return True


def get_visible_ticket_or_404(ticket: Ticket | None, current_user: User) -> Ticket:
    """Kombiniert "existiert das Ticket?" und "darf current_user es sehen?" zu
    demselben Fehler, TicketNotFoundError - die Web-Schicht macht daraus eine
    404-Antwort (siehe core/error_handlers.py; der Funktionsname folgt dem
    verbreiteten "get_or_404"-Muster).

    Bewusst "nicht gefunden" statt "keine Berechtigung" (403): ein fremdes
    Ticket - eines anderen Employees oder aus einem anderen Arbeitsbereich -
    soll nicht mal als existent erkennbar sein (Object-Level Authorization /
    IDOR-Vermeidung, siehe Architektur-Doku Abschnitt 6).
    """
    if ticket is None or not is_ticket_visible(ticket, current_user):
        raise TicketNotFoundError("Ticket nicht gefunden")
    return ticket
