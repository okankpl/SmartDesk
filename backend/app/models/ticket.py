import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.user import User


class TicketStatus(str, enum.Enum):
    """Moegliche Zustaende eines Tickets.

    Phase 2 ergaenzt RESOLVED: der Zustand zwischen "Agent sagt fertig" und
    "final geschlossen". Damit wird aus einem einfachen Flip eine echte
    Freigabe-Regel (wer darf resolved -> closed? siehe Phase 4).
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """Ersetzt die reine Zahl aus Phase 1 - macht "Kritische Incidents" auf dem
    Dashboard spaeter aus echten Daten berechenbar statt hartkodiert."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
    __mapper_args__ = {"version_id_col": version}

    title: Mapped[str] = mapped_column(String(200))
    # Text statt String(n): kein Laengenlimit, passend fuer laengere Beschreibungen.
    # nullable=True, weil das Feld im Dashboard-Mock bisher gar nicht existierte -
    # bestehende (und neue, kurze) Tickets sollen ohne Beschreibung gueltig bleiben.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )

    # ForeignKey("users.id") verweist auf die id-Spalte der users-Tabelle. Das ist ein
    # DB-Constraint: requester_id MUSS auf eine tatsaechlich existierende Zeile in
    # users zeigen, sonst lehnt Postgres das INSERT/UPDATE ab.
    # nullable=False: jedes Ticket braucht einen Melder. Wird in Phase 3 automatisch
    # aus dem eingeloggten Nutzer gesetzt, nicht mehr vom Client mitgegeben.
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # assignee_id ist nullable: ein neues Ticket hat noch niemanden, der es bearbeitet
    # ("open" = niemand hat es geclaimt).
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Demo-Arbeitsbereich, zu dem das Ticket gehoert (NULL = normales Ticket).
    # Steht bewusst direkt am Ticket statt nur ueber den Melder ableitbar zu
    # sein: so kann die Sichtbarkeitsregel (services/ticket_access.py) die
    # Tickets eines Arbeitsbereichs ohne zusaetzlichen JOIN filtern.
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("demo_workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # lazy="joined": die Namen kommen per JOIN gleich mit der Ticketabfrage, statt
    # einer zusaetzlichen Abfrage pro Ticket beim Anzeigen der Liste (N+1-Problem).
    requester: Mapped[User] = relationship(foreign_keys=[requester_id], lazy="joined")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id], lazy="joined")

    @property
    def requester_name(self) -> str | None:
        return self.requester.full_name if self.requester else None

    @property
    def assignee_name(self) -> str | None:
        return self.assignee.full_name if self.assignee else None

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    # Werden als Seiteneffekt beim jeweiligen Status-Uebergang gesetzt (Phase 4) -
    # macht "Heute geloest" auf dem Dashboard aus echten Daten berechenbar.
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
