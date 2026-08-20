from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])

# Depends(get_current_user) an jedem Endpunkt: FastAPI ruft die Dependency vor
# der jeweiligen Funktion auf, prueft den JWT und laedt den eingeloggten User.
# Schlaegt das fehl (kein/ungueltiger Token), antwortet FastAPI automatisch mit
# 401, bevor der Funktionskoerper ueberhaupt erreicht wird - Autorisierung
# (WELCHE Rolle WAS darf) ist damit noch nicht abgedeckt, nur Authentifizierung
# (WER ueberhaupt zugreifen darf). Siehe docs/architektur-und-konzepte.md.


@router.get("", response_model=list[TicketRead])
def list_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Ticket]:
    return list(db.execute(select(Ticket)).scalars().all())


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
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    db.delete(ticket)
    db.commit()
