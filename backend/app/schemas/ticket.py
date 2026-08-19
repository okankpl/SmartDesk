from datetime import datetime

# BaseModel ist die Basisklasse für alle Pydantic-Schemas (Validierung + Serialisierung).
# ConfigDict ist ein Hilfstyp, um Einstellungen für so ein Schema zu setzen.
from pydantic import BaseModel, ConfigDict

from app.models.ticket import TicketStatus


# TicketBase erbt von BaseModel - das macht es zu einem Pydantic-Schema, kein
# SQLAlchemy-Modell (Unterschied zu Ticket in models/ticket.py!). Schemas beschreiben
# JSON-Ein-/Ausgabe, Modelle beschreiben Datenbanktabellen.
class TicketBase(BaseModel):
    """Felder, die sowohl beim Erstellen als auch beim Lesen eines Tickets vorkommen."""

    title: str
    # "status: TicketStatus = TicketStatus.OPEN" - Type Hint UND Default-Wert kombiniert.
    # Wird beim Erstellen kein status mitgeschickt, nimmt Pydantic automatisch OPEN.
    status: TicketStatus = TicketStatus.OPEN
    priority: int = 1


# "class TicketCreate(TicketBase):" mit leerem Klassenkörper (nur Docstring) - erbt
# einfach ALLE Felder von TicketBase, ohne selbst neue hinzuzufügen. Der Grund, es
# trotzdem als eigene Klasse zu haben: später (Phase 2+) kann TicketCreate wachsen,
# ohne TicketBase/TicketRead zu verändern.
class TicketCreate(TicketBase):
    """Eingabedaten für POST /tickets. Aktuell identisch zu TicketBase."""


class TicketRead(TicketBase):
    """Antwortformat für Ticket-Endpunkte, inklusive serverseitig erzeugter Felder."""

    # from_attributes=True erlaubt es, dieses Schema direkt aus einem SQLAlchemy-Ticket-
    # Objekt zu bauen (TicketRead.model_validate(ticket_objekt)), statt zwingend ein
    # Dictionary übergeben zu müssen. FastAPI macht das intern automatisch.
    model_config = ConfigDict(from_attributes=True)

    # Zusätzliche Felder, die NUR beim Lesen existieren (die DB erzeugt sie serverseitig,
    # ein Client kann sie beim Erstellen nicht selbst mitgeben).
    id: int
    created_at: datetime
    updated_at: datetime
