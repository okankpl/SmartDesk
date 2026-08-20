from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ticket import TicketPriority, TicketStatus


class TicketBase(BaseModel):
    """Felder, die sowohl beim Erstellen als auch beim Lesen eines Tickets vorkommen."""

    title: str
    description: str | None = None
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketCreate(TicketBase):
    """Eingabedaten fuer POST /tickets.

    Bewusst OHNE requester_id: seit die Ticket-Endpunkte einen JWT verlangen
    (get_current_user), waere ein vom Client mitgeschicktes requester_id ein
    Sicherheitsloch - der Client koennte damit Tickets im Namen eines anderen
    Nutzers anlegen. Der Router setzt requester_id stattdessen serverseitig
    aus dem eingeloggten Nutzer.
    """


class TicketUpdate(BaseModel):
    """Eingabedaten fuer PATCH /tickets/{id}.

    Bewusst OHNE status-Feld: Statuswechsel laufen ab Phase 4 ueber einen
    eigenen, regelgeprueften Endpunkt (PATCH /tickets/{id}/status), nicht
    ueber dieses generische "irgendwas aktualisieren".
    Alle Felder sind optional (mit Default None) - PATCH aendert nur das,
    was tatsaechlich mitgeschickt wurde.
    """

    title: str | None = None
    description: str | None = None
    priority: TicketPriority | None = None
    assignee_id: int | None = None


class TicketRead(TicketBase):
    """Antwortformat fuer Ticket-Endpunkte, inklusive serverseitig erzeugter Felder."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    requester_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
