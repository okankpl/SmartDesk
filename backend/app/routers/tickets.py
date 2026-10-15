from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketRead, TicketStatusUpdate, TicketUpdate
from app.services.ticket_access import get_visible_ticket_or_404, visible_tickets_query
from app.services.ticket_lifecycle import apply_status_transition, get_allowed_next_statuses
from app.services.ticket_assignment import validate_assignment
from app.services.ticket_history import record_event
from app.services.errors import InvalidTransitionError

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _to_ticket_read(ticket: Ticket, current_user: User) -> TicketRead:
    """Baut die API-Antwort fuer EIN Ticket, inklusive allowed_transitions fuer
    GENAU current_user - deshalb kein einfaches response_model=TicketRead direkt
    auf dem ORM-Objekt (das kaeme ohne diese Zusatzinfo aus), sondern jeder
    Endpunkt unten reicht current_user explizit hier durch.
    model_validate(...): liest die uebrigen Felder direkt von den
    SQLAlchemy-Attributen (moeglich dank from_attributes=True im Schema).
    model_copy(update=...): erzeugt eine Kopie des validierten Modells mit
    genau einem zusaetzlich ueberschriebenen Feld.
    """
    return TicketRead.model_validate(ticket).model_copy(
        update={"allowed_transitions": get_allowed_next_statuses(ticket, current_user)}
    )


# Depends(get_current_user) an jedem Endpunkt: FastAPI ruft die Dependency vor
# der jeweiligen Funktion auf, prueft den JWT und laedt den eingeloggten User -
# das ist Authentifizierung (WER darf ueberhaupt rein). Autorisierung (WELCHE
# Rolle WAS darf) kommt zusaetzlich dazu: Depends(require_roles(...)) an den
# Endpunkten, die nur bestimmte Rollen ausfuehren duerfen (siehe delete_ticket,
# update_ticket), bzw. eine Sichtbarkeits-Filterung im Funktionskoerper selbst
# dort, wo es nicht um "ja/nein", sondern um "welche Teilmenge" geht (siehe
# list_tickets, get_ticket). Siehe docs/architektur-und-konzepte.md, Abschnitt 6/9.


# Reihenfolge der Ticketliste - wie eine Arbeits-Warteschlange im Support:
# dringendste Prioritaet zuerst, bei gleicher Prioritaet das aelteste Ticket
# oben (es wartet am laengsten). Ohne ORDER BY ist die Reihenfolge in SQL
# nicht festgelegt: PostgreSQL lieferte die Zeilen in Speicher-Reihenfolge,
# und ein gerade geaendertes Ticket rutschte dabei ans Ende der Liste (ein
# UPDATE legt intern eine neue Version der Zeile an).
# priority.desc(): PostgreSQL sortiert ENUM-Werte in der Reihenfolge, in der
# sie beim Anlegen des Typs aufgezaehlt wurden (low, medium, high, critical -
# siehe Migration 39a8b85460dc), nicht alphabetisch. Absteigend heisst also
# "critical" zuerst. id als letzter Tie-Breaker, wie bei den Kommentaren.
TICKET_LIST_ORDER = (Ticket.priority.desc(), Ticket.created_at, Ticket.id)


@router.get("", response_model=list[TicketRead])
def list_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[TicketRead]:
    # EMPLOYEE sieht nur selbst gemeldete Tickets (Datenschutz: fremde Anliegen
    # sind nicht automatisch fuer alle sichtbar). AGENT/ADMIN sehen alles - sie
    # muessen ja Tickets bearbeiten koennen, die sie nicht selbst gemeldet haben.
    # Die Regel steht in services/ticket_access.py, neben der fuer Einzeltickets.
    # *TICKET_LIST_ORDER "packt" das Tupel aus: order_by bekommt die drei
    # Sortierkriterien als einzelne Argumente.
    query = visible_tickets_query(current_user).order_by(*TICKET_LIST_ORDER)
    tickets = db.execute(query).scalars().all()
    return [_to_ticket_read(ticket, current_user) for ticket in tickets]


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketRead:
    # requester_id kommt jetzt aus dem eingeloggten Nutzer, nicht mehr vom Client
    # (siehe TicketCreate-Docstring) - ein separater Existenz-Check entfaellt damit,
    # current_user existiert per Definition (sonst haette get_current_user schon
    # mit 401 abgebrochen).
    ticket = Ticket(**payload.model_dump(), requester_id=current_user.id)
    db.add(ticket)
    db.flush()
    record_event(db, ticket, current_user, "created", {"status": {"old": None, "new": "open"}})
    db.commit()
    db.refresh(ticket)
    return _to_ticket_read(ticket, current_user)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> TicketRead:
    # Dieselbe Sichtbarkeitsregel wie list_tickets, hier als "gehoert das
    # Ticket ueberhaupt zu mir"-Check statt als Filter - ausgelagert nach
    # services/ticket_access.py, weil comments.py exakt dieselbe Pruefung
    # braucht (siehe Kommentar dort).
    ticket = get_visible_ticket_or_404(db.get(Ticket, ticket_id), current_user)
    return _to_ticket_read(ticket, current_user)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    # Nur AGENT/ADMIN duerfen Ticket-Inhalte per generischem PATCH aendern -
    # EMPLOYEE greift nach dem Erstellen nur noch ueber den Statuswechsel-
    # Endpunkt ein (Ablehnen einer Loesung, siehe ticket_lifecycle.py).
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
) -> TicketRead:
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update(of=Ticket))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")

    if ticket.status == TicketStatus.CLOSED:
        raise InvalidTransitionError("Geschlossene Tickets können nicht mehr geändert werden")
    # Compare while holding the row lock, before applying changes or recording history.
    if payload.expected_version is not None and payload.expected_version != ticket.version:
        raise InvalidTransitionError("Das Ticket wurde inzwischen geändert. Bitte aktuellen Stand laden.")
    if "assignee_id" in payload.model_fields_set:
        assignee = db.get(User, payload.assignee_id) if payload.assignee_id is not None else None
        if payload.assignee_id is not None and assignee is None:
            raise HTTPException(status_code=404, detail="Bearbeiter nicht gefunden")
        validate_assignment(ticket, assignee, current_user)

    # model_dump(exclude_unset=True): nimmt NUR Felder mit, die im Request tatsaechlich
    # mitgeschickt wurden (nicht einfach alle, die Pydantic mit None befuellt haette).
    # Sonst wuerde ein PATCH mit nur {"title": "..."} versehentlich auch priority und
    # assignee_id auf None zuruecksetzen.
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    changes = {
        field: {"old": getattr(ticket, field), "new": value}
        for field, value in updates.items() if getattr(ticket, field) != value
    }
    for field, value in updates.items():
        # setattr(objekt, "feldname", wert) ist das dynamische Gegenstueck zu
        # "objekt.feldname = wert" - hier noetig, weil der Feldname erst zur Laufzeit
        # aus der Schleife kommt, nicht fest im Code steht.
        setattr(ticket, field, value)

    record_event(db, ticket, current_user, "updated", changes)
    db.commit()
    db.refresh(ticket)
    return _to_ticket_read(ticket, current_user)


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketRead:
    # Sichtbarkeit ZUERST pruefen, vor den Lifecycle-Regeln. Vorher lief hier
    # nur ein "existiert das Ticket"-Check: ein Employee konnte fremde
    # Ticket-IDs durchprobieren und an den Fehlermeldungen ablesen, dass das
    # Ticket existiert UND welchen Status es hat (409 "Übergang von
    # 'in_progress' zu ... nicht erlaubt") - ein Informationsleck (IDOR).
    # Jetzt gilt dieselbe Regel wie bei GET /tickets/{id}: fremd = 404.
    # Lock only the ticket row, not the outer-joined users. Concurrent claims
    # must evaluate permissions against the state committed by the winner.
    ticket = get_visible_ticket_or_404(
        db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update(of=Ticket)), current_user,
    )
    previous_status, previous_assignee = ticket.status, ticket.assignee_id

    # Prueft die Uebergangs- und Rollenregeln und setzt bei Erfolg ticket.status
    # (+ Bearbeiter und Zeitstempel) auf dem Objekt; fachliche Fehler werden
    # vom zentralen Handler in HTTP-Antworten uebersetzt.
    apply_status_transition(ticket, payload.status, current_user)

    changes = {"status": {"old": previous_status.value, "new": ticket.status.value}}
    if previous_assignee != ticket.assignee_id:
        changes["assignee_id"] = {"old": previous_assignee, "new": ticket.assignee_id}
    record_event(db, ticket, current_user, "status_changed", changes)
    db.commit()
    db.refresh(ticket)
    return _to_ticket_read(ticket, current_user)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    # Loeschen entfernt die Nachvollziehbarkeit komplett (anders als ein
    # Status-Wechsel zu CLOSED) - deshalb bewusst nur ADMIN, nicht auch AGENT.
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    db.delete(ticket)
    db.commit()
