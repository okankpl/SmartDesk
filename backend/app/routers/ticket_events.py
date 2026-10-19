from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User
from app.schemas.ticket_event import FieldChange, TicketEventRead
from app.services.ticket_access import get_visible_ticket_or_404

router = APIRouter(prefix="/tickets/{ticket_id}/history", tags=["history"])


def _with_assignee_labels(changes: dict, names: dict[int, str]) -> dict[str, FieldChange]:
    """Baut die Feldaenderungen eines Ereignisses fuer die Antwort und haengt
    bei assignee_id die aktuellen Namen der beteiligten Personen an.
    names.get(None) liefert None - ein "nicht zugewiesen" bleibt also ohne Namen."""
    result = {}
    for field, change in changes.items():
        if field == "assignee_id":
            result[field] = FieldChange(
                **change, old_label=names.get(change["old"]), new_label=names.get(change["new"]),
            )
        else:
            result[field] = FieldChange(**change)
    return result


@router.get("", response_model=list[TicketEventRead])
def list_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TicketEventRead]:
    # Dieselbe Sichtbarkeitsregel wie fuer das Ticket selbst (fremd = 404).
    get_visible_ticket_or_404(db.get(Ticket, ticket_id), current_user)
    # Ein JOIN laedt den Namen der handelnden Person direkt mit, statt einer
    # eigenen Abfrage pro Ereignis.
    rows = db.execute(
        select(TicketEvent, User.full_name)
        .join(User, User.id == TicketEvent.actor_id)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at, TicketEvent.id)
    ).all()

    # Bearbeiter stehen in der Historie als Nutzer-ID (die gespeicherte
    # Tatsache). Vorher zeigte die Oberflaeche deshalb "Nutzer #3" statt eines
    # Namens. Die Namen aller vorkommenden IDs werden mit EINER zusaetzlichen
    # Abfrage nachgeladen. Wie bei actor_name gilt der aktuelle Profilname.
    assignee_ids = {
        value
        for event, _ in rows
        for value in (event.changes.get("assignee_id") or {}).values()
        if isinstance(value, int)
    }
    names = (
        dict(db.execute(select(User.id, User.full_name).where(User.id.in_(assignee_ids))).all())
        if assignee_ids
        else {}
    )

    return [
        TicketEventRead(
            id=event.id, ticket_id=event.ticket_id, actor_id=event.actor_id,
            actor_name=name, kind=event.kind, changes=_with_assignee_labels(event.changes, names),
            created_at=event.created_at,
        )
        for event, name in rows
    ]
