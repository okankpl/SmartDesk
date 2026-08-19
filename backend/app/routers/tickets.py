# Vier Namen aus dem fastapi-Package in einer Zeile importiert.
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead

# APIRouter(...) erzeugt ein eigenes "Mini-FastAPI" nur für Ticket-Routen. prefix="/tickets"
# heißt: alle @router.get("")/@router.post("") unten sind eigentlich /tickets/... - wir
# müssen "/tickets" nicht bei jeder einzelnen Route wiederholen. tags=["tickets"] gruppiert
# diese Routen nur optisch in der Swagger-UI.
router = APIRouter(prefix="/tickets", tags=["tickets"])


# response_model=list[TicketRead] sagt FastAPI: "validiere/filtere die Antwort so, dass
# nur die Felder von TicketRead rausgehen" - zusätzlicher Schutz, falls das SQLAlchemy-
# Objekt intern mehr Felder hätte, als nach außen sollen.
@router.get("", response_model=list[TicketRead])
# "db: Session = Depends(get_db)" - Dependency Injection (schon in database.py erklärt):
# FastAPI ruft vorher get_db() auf und reicht das Ergebnis hier als "db" rein.
def list_tickets(db: Session = Depends(get_db)) -> list[Ticket]:
    # select(Ticket) baut ein SQL-SELECT-Statement (noch ohne es auszuführen).
    # db.execute(...) führt es aus. .scalars() sagt "gib mir die Ticket-Objekte direkt
    # zurück" (statt roher Tabellenzeilen). .all() holt ALLE Ergebnisse als eine Liste.
    # list(...) drumherum, weil .all() technisch eine SQLAlchemy-eigene Sequenz liefert,
    # keine reine Python list - für den Type Hint "-> list[Ticket]" wandeln wir das um.
    return list(db.execute(select(Ticket)).scalars().all())


# status_code=status.HTTP_201_CREATED setzt den HTTP-Status der Antwort fest auf 201
# ("Created") statt dem sonst üblichen Default 200 ("OK") - Konvention für erfolgreiches
# Anlegen einer neuen Ressource.
@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
# "payload: TicketCreate" - FastAPI liest den JSON-Body der Anfrage, validiert ihn gegen
# das TicketCreate-Schema und reicht ihn hier als fertiges Python-Objekt rein.
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    # payload.model_dump() wandelt das Pydantic-Objekt in ein Dictionary um, z.B.
    # {"title": "...", "status": "open", "priority": 1}.
    # "**payload.model_dump()" ist Dictionary-Unpacking: die Sterne "**" nehmen dieses
    # Dictionary auseinander und übergeben jeden Eintrag als eigenes Keyword-Argument -
    # gleichbedeutend mit Ticket(title="...", status="open", priority=1), nur kürzer.
    ticket = Ticket(**payload.model_dump())
    # Diese drei Zeilen sind das klassische SQLAlchemy-Muster für "neue Zeile anlegen":
    db.add(ticket)      # 1. zur Session hinzufügen (noch nicht in der DB)
    db.commit()          # 2. Transaktion abschließen -> jetzt wirklich in der DB
    db.refresh(ticket)    # 3. vom DB-Server erzeugte Werte (id, created_at, ...) nachladen
    return ticket


@router.get("/{ticket_id}", response_model=TicketRead)
# "{ticket_id}" im Pfad oben ist ein Platzhalter. "ticket_id: int" hier unten liest genau
# diesen Teil der URL aus und wandelt ihn automatisch in eine Zahl um (z.B. /tickets/5
# -> ticket_id = 5). Passt der Wert nicht zu int, antwortet FastAPI automatisch mit 422.
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    # db.get(Ticket, ticket_id) sucht direkt per Primärschlüssel (id) - effizienter als
    # ein select()-Statement mit WHERE-Bedingung für diesen einfachen Fall.
    ticket = db.get(Ticket, ticket_id)
    # "is None" statt "== None" ist die in Python übliche Schreibweise für einen Vergleich
    # mit None (Pythons Äquivalent zu null/undefined).
    if ticket is None:
        # raise wirft eine Exception. FastAPI fängt HTTPException automatisch ab und
        # wandelt sie in eine echte HTTP-Antwort mit diesem Status-Code und Text um.
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    return ticket
