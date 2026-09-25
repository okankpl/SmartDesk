from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.comment import Comment
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead
from app.services.ticket_access import get_visible_ticket_or_404

# Eigene Router-Datei statt Endpunkte direkt in tickets.py - eine Datei pro
# Ressource (wie auth.py/tickets.py/users.py), auch wenn die URL unter
# /tickets/... haengt. Der Pfad-Parameter {ticket_id} steht direkt im
# Prefix: FastAPI reicht ihn an jede Funktion unten als normalen Parameter
# durch, genau wie bei einer Route, die ihn selbst im Pfad deklariert.
# Das ist eine "Nested Resource" (verschachtelte Ressource): ein Kommentar
# ergibt ohne sein Ticket fachlich keinen Sinn, also spiegelt die URL diese
# Hierarchie wider - gleiches Muster wie /tickets/{id}/status.
router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])

# Bewusst nur GET und POST, kein PATCH/DELETE: Kommentare sind nach dem
# Erstellen unveraenderlich (siehe Docstring von models/comment.py).


@router.get("", response_model=list[CommentRead])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Comment]:
    # Wer das Ticket nicht sehen darf, darf auch dessen Kommentare nicht sehen -
    # dieselbe Regel wie bei get_ticket, bewusst aus EINER Quelle
    # (services/ticket_access.py) statt hier nochmal nachgebaut.
    get_visible_ticket_or_404(db.get(Ticket, ticket_id), current_user)

    # order_by(created_at): aelteste zuerst, damit sich die Kommentarliste wie
    # ein Gespraechsverlauf von oben nach unten liest.
    # Comment.id als zweites Sortierkriterium ("Tie-Breaker"): Haben zwei
    # Kommentare exakt denselben Zeitstempel (z.B. SQLite speichert nur ganze
    # Sekunden), waere ihre Reihenfolge sonst NICHT garantiert - die Datenbank
    # darf gleichrangige Zeilen in beliebiger Reihenfolge liefern. Die id
    # steigt mit jedem INSERT, spiegelt also die Erstellungsreihenfolge wider.
    query = (
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at, Comment.id)
    )
    return list(db.execute(query).scalars().all())


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Comment:
    # Kommentieren darf, wer das Ticket sehen darf - ein Employee also nur
    # bei eigenen Tickets, Agent/Admin bei allen. Keine eigene Rollen-
    # Beschraenkung darueber hinaus: Melder und Bearbeiter sollen beide
    # miteinander kommunizieren koennen, das ist gerade der Sinn der Funktion.
    get_visible_ticket_or_404(db.get(Ticket, ticket_id), current_user)

    comment = Comment(
        ticket_id=ticket_id,
        # Aus dem Token, NICHT aus payload - siehe CommentCreate-Docstring.
        author_id=current_user.id,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
