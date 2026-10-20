import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.demo_workspace import DemoWorkspace


class UserRole(str, enum.Enum):
    """Die drei Rollen von SmartDesk - mirrort reale ITSM-Tools:
    EMPLOYEE meldet Probleme, AGENT bearbeitet sie, ADMIN darf zusaetzlich final
    schliessen und Tickets neu zuweisen (Regeln kommen in Phase 4).
    """

    EMPLOYEE = "employee"
    AGENT = "agent"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True erzeugt einen DB-Constraint: zwei Zeilen duerfen nicht dieselbe
    # E-Mail haben. index=True beschleunigt Suchen/Login per E-Mail zusaetzlich.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Erst in Phase 3 (Auth) wird hier wirklich ein bcrypt-Hash reinkommen. Die Spalte
    # legen wir aber schon jetzt an, damit die Tabellenstruktur nicht nochmal per
    # Migration veraendert werden muss, nur weil ein Feld fehlte.
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Zu welchem Demo-Arbeitsbereich das Konto gehoert (siehe
    # models/demo_workspace.py). NULL = normales Konto ausserhalb der
    # oeffentlichen Demo. ondelete="CASCADE": laeuft der Arbeitsbereich ab und
    # wird geloescht, verschwinden seine Konten mit.
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("demo_workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Ohne lazy="joined" (anders als bei Ticket.requester): der Arbeitsbereich
    # wird nur bei Demo-Konten und nur bei Bedarf nachgeladen, nicht bei jeder
    # Ticketliste fuer jeden Namen mit.
    workspace: Mapped[DemoWorkspace | None] = relationship()

    @property
    def demo_expires_at(self) -> datetime | None:
        """Wann der Demo-Arbeitsbereich dieses Kontos geloescht wird - None bei
        normalen Konten. Wird ueber CurrentUserRead an das Frontend geliefert
        (Hinweisleiste "wird am ... geloescht")."""
        return self.workspace.expires_at if self.workspace else None
