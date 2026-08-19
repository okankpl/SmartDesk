# enum ist Teil der Python-Standardbibliothek - für "einer von mehreren festen Werten".
import enum
from datetime import datetime

# "import X as Y" importiert X, aber unter dem lokalen Namen Y. Grund hier: SQLAlchemy hat
# eine eigene Klasse namens "Enum", die wir umbenennen, damit sie nicht mit Pythons
# eingebautem "enum"-Modul (oben) verwechselt/überschrieben wird.
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


# "class TicketStatus(str, enum.Enum):" - Mehrfachvererbung (zwei Elternklassen in einer
# Klammer, durch Komma getrennt). TicketStatus.OPEN verhält sich dadurch GLEICHZEITIG
# wie ein Enum-Wert UND wie ein normaler Python-String "open" - praktisch für JSON.
class TicketStatus(str, enum.Enum):
    """Mögliche Zustände eines Tickets.

    Phase 1 bildet bewusst nur die drei Zustände ab, die es aktuell auch im
    Angular-Frontend gibt. Der vierte Zustand ("resolved") kommt in Phase 2
    über eine echte Migration dazu.
    """

    # Jede Zeile ist ein Enum-Mitglied: NAME = WERT. TicketStatus.OPEN ist der Name (in
    # Großbuchstaben, Konvention für Konstanten), "open" ist der eigentliche String-Wert.
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


# class Ticket(Base): - erbt von unserer Base-Klasse aus database.py. Dadurch weiß
# SQLAlchemy: "diese Klasse beschreibt keine normale Python-Klasse, sondern eine Tabelle".
class Ticket(Base):
    # Doppelter Unterstrich vorne UND hinten ("Dunder", von "double underscore") markiert
    # in Python spezielle, von einem Framework ausgewertete Attribute/Methoden.
    # SQLAlchemy liest __tablename__ aus, um den Tabellennamen in Postgres festzulegen.
    __tablename__ = "tickets"

    # "id: Mapped[int]" ist ein Type Hint mit einem GENERISCHEN Typ (vergleichbar mit
    # Array<number> in TypeScript): Mapped[int] heißt "diese Spalte wird als Python int
    # gelesen/geschrieben". mapped_column(...) beschreibt dann die Spalte selbst.
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[TicketStatus] = mapped_column(
        # values_callable erwartet eine Funktion. lambda enum_cls: [...] ist eine
        # anonyme Kurzform für "def f(enum_cls): return [...]" - eine namenlose
        # Ein-Zeilen-Funktion, die man direkt als Argument übergeben kann.
        # [e.value for e in enum_cls] ist eine List Comprehension: "erzeuge eine Liste,
        # indem du für jedes Element e in enum_cls dessen .value nimmst" - kompakte
        # Schreibweise für eine for-Schleife, die Ergebnisse in einer neuen Liste sammelt.
        # Sorgt dafür, dass die Datenbank die Enum-WERTE ("open", "in_progress", ...)
        # speichert statt der Python-NAMEN ("OPEN", "IN_PROGRESS", ...).
        SAEnum(TicketStatus, name="ticket_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # func.now() ist SQLAlchemys Weg, "NOW()" (eine SQL-Funktion) in die Migration/das
    # CREATE TABLE zu schreiben - die Datenbank selbst setzt den Zeitstempel, nicht Python.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        # onupdate=func.now() heißt: bei jedem UPDATE dieser Zeile setzt die Datenbank
        # automatisch den aktuellen Zeitstempel neu, ohne dass wir das im Code tun müssen.
        server_default=func.now(), onupdate=func.now()
    )
