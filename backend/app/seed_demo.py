"""Beispieldaten fuer die getrennte Demo, nie fuer Produktion. Idempotent: ein
erneuter Start legt nichts doppelt an und ueberschreibt nichts."""
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.demo_data import DEMO_PEOPLE, add_sample_tickets

DEMO_PASSWORD = "SmartDesk-Demo26!"
# Feste, im README dokumentierte Anmeldedaten der LOKALEN Demo. Die
# oeffentliche Demo nutzt stattdessen private Arbeitsbereiche ohne Passwort
# (services/demo_workspaces.py).
DEMO_EMAILS = {
    UserRole.EMPLOYEE: "employee@example.com",
    UserRole.AGENT: "agent@example.com",
    UserRole.ADMIN: "admin@example.com",
}


def seed_demo(db: Session) -> bool:
    if not get_settings().demo_mode:
        raise RuntimeError("Demo-Daten benötigen DEMO_MODE=true und eine separate Demo-Datenbank")
    # Bestehende Konten nie zu Demo-Konten mit Rechten machen oder ihr Passwort
    # zuruecksetzen - die Befuellung laeuft nur auf einer leeren Datenbank.
    legacy_placeholder = and_(User.email == "seed@smartdesk.local", User.hashed_password == "not-a-real-hash")
    if db.scalar(select(User.id).where(~legacy_placeholder).limit(1)) is not None:
        return False
    if db.scalar(select(Ticket.id).limit(1)) is not None:
        return False
    users = []
    for role, name in DEMO_PEOPLE:
        user = User(email=DEMO_EMAILS[role], full_name=name, role=role, hashed_password=hash_password(DEMO_PASSWORD))
        db.add(user)
        users.append(user)
    db.flush()
    employee, agent, admin = users
    add_sample_tickets(db, employee, agent, admin, now=datetime.now(timezone.utc))
    db.commit()
    return True


if __name__ == "__main__":
    with SessionLocal() as session:
        print("Demo angelegt." if seed_demo(session) else "Datenbank enthält bereits Daten; nichts verändert.")
