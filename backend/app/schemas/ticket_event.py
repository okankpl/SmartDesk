from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FieldChange(BaseModel):
    """Vorher-/Nachher-Wert eines Feldes, so wie er in ticket_events steht.

    old_label/new_label sind reine Anzeigenamen, die erst beim LESEN ergaenzt
    werden - aktuell nur fuer assignee_id (der Name statt der Nutzer-ID).
    Gespeichert bleiben ausschliesslich die Fakten old/new, siehe
    docs/entscheidungen-workflow-und-historie.md ("Anwendungshistorie").
    """

    old: str | int | None
    new: str | int | None
    old_label: str | None = None
    new_label: str | None = None


class TicketEventRead(BaseModel):
    id: int
    ticket_id: int
    actor_id: int
    actor_name: str
    kind: Literal["created", "updated", "status_changed"]
    changes: dict[str, FieldChange]
    created_at: datetime
