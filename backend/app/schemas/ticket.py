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


class TicketStatusUpdate(BaseModel):
    """Eingabedaten fuer PATCH /tickets/{id}/status - der einzige erlaubte Weg, um
    den Status eines Tickets zu aendern. Die eigentliche Pruefung, ob der
    Uebergang erlaubt ist, passiert in app/services/ticket_lifecycle.py, nicht
    hier im Schema - Pydantic prueft nur, dass ueberhaupt ein gueltiger
    TicketStatus-Wert mitgeschickt wurde.
    """

    status: TicketStatus


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
    # KEIN Feld auf dem Ticket-Model - wird beim Serialisieren im Router aus
    # get_allowed_next_statuses(ticket, current_user) befuellt (siehe tickets.py).
    # Default [] noetig, weil TicketRead.model_validate(ticket) dieses Feld sonst
    # (da es auf dem SQLAlchemy-Model nicht existiert) nicht befuellen koennte -
    # der eigentliche Wert wird direkt danach per model_copy(update=...) gesetzt.
    allowed_transitions: list[TicketStatus] = []
