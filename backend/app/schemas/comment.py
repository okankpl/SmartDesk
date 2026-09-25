from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Eingabedaten fuer POST /tickets/{ticket_id}/comments.

    Bewusst NUR body: author_id kommt aus dem eingeloggten Nutzer
    (current_user), ticket_id aus der URL - beides NICHT vom Client, derselbe
    Mass-Assignment-Schutz wie requester_id bei TicketCreate. Ein Client
    koennte sonst Kommentare unter fremdem Namen oder an fremde Tickets
    haengen.
    """

    # str_strip_whitespace: entfernt Leerzeichen am Anfang/Ende VOR der
    # Validierung - sonst wuerde ein Kommentar aus nur "   " die
    # Laengenpruefung unten bestehen (Laenge 3), obwohl er inhaltlich leer ist.
    model_config = ConfigDict(str_strip_whitespace=True)

    # min_length=1 lehnt leere Kommentare direkt bei der Validierung ab (422),
    # bevor der Router ueberhaupt laeuft - dieselbe Idee wie "Fail Fast" im
    # Rest des Projekts. Field(...) ist Pydantics Weg, einem Feld zusaetzliche
    # Regeln mitzugeben, die ueber den reinen Typ (str) hinausgehen.
    body: str = Field(min_length=1)


class CommentRead(BaseModel):
    """Antwortformat fuer Kommentar-Endpunkte."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime
