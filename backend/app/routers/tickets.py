from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketRead, TicketStatusUpdate, TicketUpdate
from app.services.ticket_lifecycle import apply_status_transition

router = APIRouter(prefix="/tickets", tags=["tickets"])

# Depends(get_current_user) an jedem Endpunkt: FastAPI ruft die Dependency vor
# der jeweiligen Funktion auf, prueft den JWT und laedt den eingeloggten User -
# das ist Authentifizierung (WER darf ueberhaupt rein). Autorisierung (WELCHE
# Rolle WAS darf) kommt zusaetzlich dazu: Depends(require_roles(...)) an den
# Endpunkten, die nur bestimmte Rollen ausfuehren duerfen (siehe delete_ticket,
# update_ticket), bzw. eine Sichtbarkeits-Filterung im Funktionskoerper selbst
# dort, wo es nicht um "ja/nein", sondern um "welche Teilmenge" geht (siehe
# list_tickets, get_ticket). Siehe docs/architektur-und-konzepte.md, Abschnitt 6/9.


@router.get("", response_model=list[TicketRead])
def list_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Ticket]:
    query = select(Ticket)
    # EMPLOYEE sieht nur selbst gemeldete Tickets (Datenschutz: fremde Anliegen
    # sind nicht automatisch fuer alle sichtbar). AGENT/ADMIN sehen alles - sie
    # muessen ja Tickets bearbeiten koennen, die sie nicht selbst gemeldet haben.
    if current_user.role == UserRole.EMPLOYEE:
        query = query.where(Ticket.requester_id == current_user.id)
    return list(db.execute(query).scalars().all())


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    # requester_id kommt jetzt aus dem eingeloggten Nutzer, nicht mehr vom Client
    # (siehe TicketCreate-Docstring) - ein separater Existenz-Check entfaellt damit,
    # current_user existiert per Definition (sonst haette get_current_user schon
    # mit 401 abgebrochen).
    ticket = Ticket(**payload.model_dump(), requester_id=current_user.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    # Dieselbe Sichtbarkeitsregel wie list_tickets, hier als "gehoert das
    # Ticket ueberhaupt zu mir"-Check statt als Filter. Bewusst derselbe 404
    # wie "existiert nicht" statt 403 "verboten": ein fremdes Ticket soll fuer
    # einen Employee nicht mal als existent erkennbar sein (Object-Level
    # Authorization / IDOR-Vermeidung, siehe Lernnotizen "Mass Assignment").
    if ticket is None or (current_user.role == UserRole.EMPLOYEE and ticket.requester_id != current_user.id):
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    # Nur AGENT/ADMIN duerfen Ticket-Inhalte per generischem PATCH aendern -
    # EMPLOYEE greift nach dem Erstellen nur noch ueber den Statuswechsel-
    # Endpunkt ein (Ablehnen einer Loesung, siehe ticket_lifecycle.py).
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")

    if payload.assignee_id is not None and db.get(User, payload.assignee_id) is None:
        raise HTTPException(status_code=404, detail="assignee_id verweist auf keinen existierenden User")

    # model_dump(exclude_unset=True): nimmt NUR Felder mit, die im Request tatsaechlich
    # mitgeschickt wurden (nicht einfach alle, die Pydantic mit None befuellt haette).
    # Sonst wuerde ein PATCH mit nur {"title": "..."} versehentlich auch priority und
    # assignee_id auf None zuruecksetzen.
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        # setattr(objekt, "feldname", wert) ist das dynamische Gegenstueck zu
        # "objekt.feldname = wert" - hier noetig, weil der Feldname erst zur Laufzeit
        # aus der Schleife kommt, nicht fest im Code steht.
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")

    # Prueft die Uebergangs- und Rollenregeln und setzt bei Erfolg ticket.status
    # (+ resolved_at/closed_at) direkt auf dem Objekt - wirft sonst eine
    # passende HTTPException (409/403), siehe ticket_lifecycle.py.
    apply_status_transition(ticket, payload.status, current_user)

    db.commit()
    db.refresh(ticket)
    return ticket


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
