from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Comment(Base):
    """Ein Kommentar zu genau einem Ticket, verfasst von genau einem User -
    die 1:n-Beziehung ueber ZWEI getrennte Fremdschluessel gleichzeitig (siehe
    Klassendiagramm in docs/architektur-und-konzepte.md, Abschnitt 5):
    ticket_id zeigt auf das Ticket, zu dem
    der Kommentar gehoert, author_id auf den Verfasser. Beides unabhaengige
    Beziehungen - viele Kommentare pro Ticket UND viele Kommentare pro User.

    Bewusst OHNE updated_at/eigenen Bearbeiten-Endpunkt: Kommentare sind nach
    dem Erstellen unveraenderlich (Audit-Trail-Charakter, wie in den meisten
    echten ITSM-Tools) - vgl. Alembic-Migrationen, die man auch nicht nachtraeglich
    umschreibt, sondern nur durch eine NEUE Migration ergaenzt.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # index=True: die Hauptabfrage ist "alle Kommentare zu Ticket X" (siehe
    # GET /tickets/{id}/comments) - ohne Index muesste Postgres bei
    # wachsender Tabelle jedes Mal alle Zeilen durchsuchen, um die richtigen
    # herauszufiltern.
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Text statt String(n): kein Laengenlimit noetig, wie schon bei
    # Ticket.description (siehe models/ticket.py).
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
