from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User


def record_event(db: Session, ticket: Ticket, actor: User, kind: str, changes: dict) -> None:
    # Kein eigenes commit(): die Transaktion gehoert dem Aufrufer. So kann ein
    # Ereignis eine fehlgeschlagene Aenderung nie ueberleben - beide werden
    # gemeinsam gespeichert oder gemeinsam verworfen.
    if changes:
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=actor.id, kind=kind, changes=changes))
