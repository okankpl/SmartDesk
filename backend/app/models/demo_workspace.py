from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class DemoWorkspace(Base):
    """Ein privater, zeitlich begrenzter Arbeitsbereich der oeffentlichen Demo.

    Jede Person, die auf "Demo starten" klickt, bekommt einen eigenen
    Arbeitsbereich mit drei Konten (Mitarbeitende, Support, Admin) und
    Beispieltickets. Nutzer und Tickets verweisen per workspace_id hierher;
    normale Konten und Tickets ausserhalb der Demo haben workspace_id = NULL.

    Laeuft der Arbeitsbereich ab, loescht services/demo_workspaces.py ihn
    samt Tickets, Kommentaren, Historie und Konten - in fester Reihenfolge,
    siehe delete_expired_workspaces.
    """

    __tablename__ = "demo_workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # index=True: "welche Arbeitsbereiche sind abgelaufen?" ist die Abfrage
    # beim Aufraeumen, "wie viele sind noch aktiv?" die beim Anlegen.
    expires_at: Mapped[datetime] = mapped_column(index=True)
