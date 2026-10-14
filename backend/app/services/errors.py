class DomainError(Exception):
    """Basisklasse fuer Verstoesse gegen eine fachliche Regel ("dieses Ticket
    gibt es fuer dich nicht", "dieser Statuswechsel ist nicht erlaubt").

    Bewusst OHNE HTTP-Bezug: die Services in diesem Paket enthalten nur
    Fachlogik und wissen nichts vom Web-Framework. Welcher HTTP-Statuscode zu
    welchem Fehler gehoert, entscheidet allein die Web-Schicht
    (core/error_handlers.py). So bleiben die Regeln auch ausserhalb eines
    HTTP-Requests nutzbar (z.B. in einem spaeteren Hintergrund-Job, in dem ein
    "409" keine Bedeutung haette), und die Tests pruefen die fachliche Aussage
    ("Uebergang ungueltig") statt einer Zahl.

    Die Fehlermeldung (das erste Argument beim Erzeugen) geht unveraendert als
    "detail" an den Client - sie darf deshalb nichts enthalten, was ein Nutzer
    nicht sehen soll.
    """


class TicketNotFoundError(DomainError):
    """Das Ticket existiert nicht - ODER der Nutzer darf es nicht sehen. Beides
    absichtlich derselbe Fehler, siehe get_visible_ticket_or_404."""


class PermissionDeniedError(DomainError):
    """Der Nutzer ist angemeldet, darf aber genau DIESE Aktion nicht ausfuehren."""


class InvalidTransitionError(DomainError):
    """Der gewuenschte Statuswechsel passt nicht zum aktuellen Zustand des
    Tickets (z.B. OPEN direkt nach CLOSED)."""
