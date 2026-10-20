"""Gemeinsame Beispieldaten fuer beide Demos: die lokale Demo mit bekannten
Konten (app/seed_demo.py) und die privaten Arbeitsbereiche der oeffentlichen
Demo (services/demo_workspaces.py). An EINER Stelle, damit beide dieselben
zwoelf Supportfaelle zeigen."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.ticket_event import TicketEvent
from app.models.user import User, UserRole

# Die drei Rollen einer Demo mit ihren fiktiven Personen.
DEMO_PEOPLE = (
    (UserRole.EMPLOYEE, "Lena Fischer"),
    (UserRole.AGENT, "Alex Weber"),
    (UserRole.ADMIN, "Samira Kaya"),
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


def add_sample_tickets(
    db: Session, employee: User, agent: User, admin: User, *, now: datetime, workspace_id: int | None = None
) -> None:
    """Legt die zwoelf Beispieltickets samt Kommentaren und Historie an.

    Kein commit() - die Transaktion gehoert dem Aufrufer, genau wie bei
    record_event (services/ticket_history.py). workspace_id: None fuer die
    lokale Demo, sonst die ID des privaten Arbeitsbereichs.
    Das * in der Parameterliste erzwingt Schluesselwort-Argumente
    (now=..., workspace_id=...), damit beim Aufruf keine Werte vertauscht werden.
    """
    for index, (title, description, priority, status) in enumerate(SAMPLE_TICKETS):
        created = now - timedelta(hours=6 + index * 3)
        ticket = Ticket(
            title=title, description=description, priority=TicketPriority(priority),
            status=TicketStatus(status), requester_id=employee.id,
            assignee_id=agent.id if status != "open" else None,
            workspace_id=workspace_id,
            created_at=created, updated_at=now,
            resolved_at=now - timedelta(hours=1) if status in {"resolved", "closed"} else None,
            closed_at=now if status == "closed" else None,
        )
        db.add(ticket)
        # flush() schickt das INSERT schon jetzt an die Datenbank (ohne
        # commit), damit ticket.id fuer die folgenden Eintraege bekannt ist.
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
