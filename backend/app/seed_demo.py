"""Idempotent sample data for the isolated demo, never for production."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.comment import Comment
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.ticket_event import TicketEvent
from app.models.user import User, UserRole

DEMO_PASSWORD = "SmartDesk-Demo26!"
DEMO_USERS = (
    ("employee@example.com", "Lena Fischer", UserRole.EMPLOYEE),
    ("agent@example.com", "Alex Weber", UserRole.AGENT),
    ("admin@example.com", "Samira Kaya", UserRole.ADMIN),
)
SAMPLE_TICKETS = (
    ("VPN-Verbindung bricht im Homeoffice ab", "Seit dem Client-Update wird die Verbindung alle zehn Minuten getrennt. Zwei Mitarbeitende im Vertrieb sind betroffen.", "critical", "open"),
    ("Gemeinsames Laufwerk nicht erreichbar", "Das Team kann auf das Projektlaufwerk nicht mehr zugreifen. Neustart und erneute Anmeldung haben nicht geholfen.", "high", "open"),
    ("Zweiter Bildschirm wird nicht erkannt", "Der externe Monitor am USB-C-Dock bleibt schwarz. Direkt am Notebook funktioniert er.", "medium", "open"),
    ("Zugang zur Projektverwaltung beantragen", "Für das neue Kundenprojekt wird ein Zugang mit Leserechten benötigt. Freigabe durch die Teamleitung liegt vor.", "low", "open"),
    ("Videokonferenz ohne Mikrofon", "Das Headset wird erkannt, in der Konferenzsoftware kommt aber kein Ton an. Berechtigungen wurden geprüft.", "medium", "open"),
    ("Drucker im zweiten Stock offline", "Druckaufträge bleiben in der Warteschlange. Der Drucker ist per Netzwerk erreichbar.", "medium", "in_progress"),
    ("Mehrfaktor-Anmeldung nach Handywechsel", "Das alte Gerät ist nicht mehr verfügbar. Identitätsprüfung mit der Personalabteilung ist abgeschlossen.", "high", "in_progress"),
    ("E-Mail-Synchronisation verzögert", "Nachrichten erscheinen auf dem Smartphone erst nach manuellem Aktualisieren. Am Desktop funktioniert die Zustellung.", "high", "in_progress"),
    ("Kalenderfreigabe für das Team", "Die Gruppenberechtigungen wurden angepasst. Bitte prüfen, ob der Kalender nun sichtbar ist.", "low", "resolved"),
    ("Softwarelizenz für neue Mitarbeiterin", "Die Lizenz ist zugewiesen, Installation und Anmeldung wurden gemeinsam getestet.", "medium", "resolved"),
    ("Notebook für Onboarding einrichten", "Arbeitsplatz eingerichtet, Updates installiert und Übergabe bestätigt.", "medium", "closed"),
    ("Passwort für das Gast-WLAN erneuern", "Der Zugang wurde erneuert und am Empfang hinterlegt.", "low", "closed"),
)


def seed_demo(db: Session) -> bool:
    if not get_settings().demo_mode:
        raise RuntimeError("Demo-Daten benötigen DEMO_MODE=true und eine separate Demo-Datenbank")
    # Never turn existing accounts into privileged demo users or reset their passwords.
    legacy_placeholder = and_(User.email == "seed@smartdesk.local", User.hashed_password == "not-a-real-hash")
    if db.scalar(select(User.id).where(~legacy_placeholder).limit(1)) is not None:
        return False
    if db.scalar(select(Ticket.id).limit(1)) is not None:
        return False
    users = []
    for email, name, role in DEMO_USERS:
        user = User(email=email, full_name=name, role=role, hashed_password=hash_password(DEMO_PASSWORD))
        db.add(user)
        users.append(user)
    db.flush()
    employee, agent, admin = users
    now = datetime.now(timezone.utc)
    for index, (title, description, priority, status) in enumerate(SAMPLE_TICKETS):
        created = now - timedelta(hours=6 + index * 3)
        ticket = Ticket(
            title=title, description=description, priority=TicketPriority(priority),
            status=TicketStatus(status), requester_id=employee.id,
            assignee_id=agent.id if status != "open" else None,
            created_at=created, updated_at=now,
            resolved_at=now - timedelta(hours=1) if status in {"resolved", "closed"} else None,
            closed_at=now if status == "closed" else None,
        )
        db.add(ticket)
        db.flush()
        db.add(TicketEvent(
            ticket_id=ticket.id, actor_id=employee.id, kind="created",
            changes={"status": {"old": None, "new": "open"}}, created_at=created,
        ))
        transitions = []
        if status != "open":
            transitions.append(("open", "in_progress", agent, created + timedelta(hours=1)))
        if status in {"resolved", "closed"}:
            transitions.append(("in_progress", "resolved", agent, ticket.resolved_at))
        if status == "closed":
            transitions.append(("resolved", "closed", admin, now))
        for old, new, actor, occurred in transitions:
            changes = {"status": {"old": old, "new": new}}
            if old == "open":
                changes["assignee_id"] = {"old": None, "new": agent.id}
            db.add(TicketEvent(
                ticket_id=ticket.id, actor_id=actor.id, kind="status_changed",
                changes=changes, created_at=occurred,
            ))
        db.add(Comment(
            ticket_id=ticket.id, author_id=employee.id,
            body="Vielen Dank für die Unterstützung. Ich bin für Rückfragen erreichbar.",
            created_at=created + timedelta(minutes=15),
        ))
        if status != "open":
            db.add(Comment(
                ticket_id=ticket.id, author_id=agent.id,
                body="Ich habe das Anliegen übernommen und die ersten Prüfschritte dokumentiert.",
                created_at=created + timedelta(hours=1, minutes=5),
            ))
    db.commit()
    return True


if __name__ == "__main__":
    with SessionLocal() as session:
        print("Demo angelegt." if seed_demo(session) else "Datenbank enthält bereits Daten; nichts verändert.")
