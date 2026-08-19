import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


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
