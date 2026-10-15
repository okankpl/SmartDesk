from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User
from app.schemas.ticket_event import TicketEventRead
from app.services.ticket_access import get_visible_ticket_or_404

router = APIRouter(prefix="/tickets/{ticket_id}/history", tags=["history"])


@router.get("", response_model=list[TicketEventRead])
def list_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TicketEventRead]:
    get_visible_ticket_or_404(db.get(Ticket, ticket_id), current_user)
    rows = db.execute(
        select(TicketEvent, User.full_name)
        .join(User, User.id == TicketEvent.actor_id)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at, TicketEvent.id)
    ).all()
    return [
        TicketEventRead(
            id=event.id, ticket_id=event.ticket_id, actor_id=event.actor_id,
            actor_name=name, kind=event.kind, changes=event.changes, created_at=event.created_at,
        )
        for event, name in rows
    ]
