from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FieldChange(BaseModel):
    old: str | int | None
    new: str | int | None


class TicketEventRead(BaseModel):
    id: int
    ticket_id: int
    actor_id: int
    actor_name: str
    kind: Literal["created", "updated", "status_changed"]
    changes: dict[str, FieldChange]
    created_at: datetime
