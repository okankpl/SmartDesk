from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.models.ticket import TicketPriority, TicketStatus

# Wiederverwendbare Feldtypen mit Pruefregeln (Annotated, siehe schemas/auth.py).
# max_length=200 beim Titel entspricht String(200) in models/ticket.py - ohne
# diese Grenze scheiterte ein zu langer Titel erst in PostgreSQL und kam als
# 500-Fehler statt als verstaendlicher 422 zurueck. strip_whitespace +
# min_length=1: ein Titel aus reinen Leerzeichen gilt als leer.
TicketTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
# Die Datenbank-Spalte (Text) haette kein Limit - die Obergrenze verhindert,
# dass jemand z.B. mehrere Megabyte Text pro Ticket ablegt und damit
# Speicher/Datenbank belastet. 10.000 Zeichen reichen fuer jede realistische
# Fehlerbeschreibung.
TicketDescription = Annotated[str, StringConstraints(max_length=10_000)]


class TicketBase(BaseModel):
    """Felder, die sowohl beim Erstellen als auch beim Lesen eines Tickets vorkommen.

    Bewusst OHNE status: der Status gehoert NICHT zu dem, was ein Client beim
    Erstellen mitbestimmen darf (siehe TicketCreate) - er steht deshalb nur in
    TicketRead.
    """

    title: TicketTitle
    description: TicketDescription | None = None
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketCreate(TicketBase):
    """Eingabedaten fuer POST /tickets.

    Bewusst OHNE requester_id: seit die Ticket-Endpunkte einen JWT verlangen
    (get_current_user), waere ein vom Client mitgeschicktes requester_id ein
    Sicherheitsloch - der Client koennte damit Tickets im Namen eines anderen
    Nutzers anlegen. Der Router setzt requester_id stattdessen serverseitig
    aus dem eingeloggten Nutzer.

    Ebenfalls OHNE status: frueher erbte TicketCreate das Feld von TicketBase,
    ein Client konnte also {"title": "...", "status": "closed"} schicken und
    ein Ticket direkt als geschlossen anlegen - an allen Regeln in
    ticket_lifecycle.py vorbei (Mass Assignment). Jetzt startet jedes Ticket
    ueber den Datenbank-Default als "open"; ein mitgeschicktes status-Feld
    ignoriert Pydantic, weil es im Schema nicht vorkommt.
    """


class TicketUpdate(BaseModel):
    """Eingabedaten fuer PATCH /tickets/{id}.

    Bewusst OHNE status-Feld: Statuswechsel laufen ab Phase 4 ueber einen
    eigenen, regelgeprueften Endpunkt (PATCH /tickets/{id}/status), nicht
    ueber dieses generische "irgendwas aktualisieren".
    Alle Felder sind optional (mit Default None) - PATCH aendert nur das,
    was tatsaechlich mitgeschickt wurde.
    """

    title: TicketTitle | None = None
    description: TicketDescription | None = None
    priority: TicketPriority | None = None
    # null ist hier ausdruecklich erlaubt: {"assignee_id": null} heisst
    # "Zuweisung aufheben".
    assignee_id: int | None = None

    # Unterschied "Feld weggelassen" vs. "Feld explizit null": weglassen heisst
    # "nicht aendern" (Default None, Validatoren laufen fuer Defaults nicht),
    # {"title": null} dagegen wuerde den Titel auf NULL setzen - die Spalte
    # erlaubt das nicht, das Ergebnis war ein 500-Fehler aus der Datenbank.
    # Dieser Validator laeuft nur fuer tatsaechlich mitgeschickte Werte und
    # macht daraus einen klaren 422.
    @field_validator("title", "priority")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("darf nicht null sein - Feld weglassen, um es unveraendert zu lassen")
        return value


class TicketStatusUpdate(BaseModel):
    """Eingabedaten fuer PATCH /tickets/{id}/status - der einzige erlaubte Weg, um
    den Status eines Tickets zu aendern. Die eigentliche Pruefung, ob der
    Uebergang erlaubt ist, passiert in app/services/ticket_lifecycle.py, nicht
    hier im Schema - Pydantic prueft nur, dass ueberhaupt ein gueltiger
    TicketStatus-Wert mitgeschickt wurde.
    """

    status: TicketStatus


class TicketRead(BaseModel):
    """Antwortformat fuer Ticket-Endpunkte, inklusive serverseitig erzeugter Felder.

    Erbt bewusst NICHT von TicketBase: dessen Pruefregeln (min_length,
    max_length) gelten fuer EINGABEN. Auf Ausgaben angewendet, wuerde ein
    aelterer Datensatz, der vor Einfuehrung der Regeln gespeichert wurde (z.B.
    ein leerer Titel), beim reinen LESEN einen 500-Fehler ausloesen - die
    komplette Ticketliste waere dann nicht mehr abrufbar.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TicketStatus
    priority: TicketPriority
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
