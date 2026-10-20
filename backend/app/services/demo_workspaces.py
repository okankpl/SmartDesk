"""Private, zeitlich begrenzte Arbeitsbereiche fuer die oeffentliche Demo.

Jede Person, die auf "Demo starten" klickt, bekommt hier einen eigenen
Arbeitsbereich: drei Konten (Mitarbeitende, Support, Admin) und die zwoelf
Beispieltickets. Was jemand darin aendert oder schreibt, betrifft nur diesen
Bereich. WER WAS SIEHT, entscheiden die Sichtbarkeitsregeln
(services/ticket_access.py, routers/users.py) - dieses Modul legt Bereiche
nur an, findet ihre Konten und raeumt abgelaufene auf.

Wie alle Services hier: kein commit(), die Transaktion gehoert dem Aufrufer.
"""
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.demo_workspace import DemoWorkspace
from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.demo_data import DEMO_PEOPLE, add_sample_tickets

# Bewusst KEIN gueltiger bcrypt-Hash: verify_password() liefert dafuer immer
# False (siehe core/security.py). Demo-Konten haben also gar kein Passwort -
# hinein kommt man nur ueber "Demo starten" und den Rollenwechsel.
NO_PASSWORD = "!demo-workspace-account-without-password"


def delete_expired_workspaces(db: Session, now: datetime) -> int:
    """Loescht alle abgelaufenen Arbeitsbereiche und gibt ihre Anzahl zurueck.

    Bewusst in fester Reihenfolge statt mit einem einzigen DELETE auf
    demo_workspaces: dabei liess PostgreSQL die Kaskaden in ungeeigneter
    Reihenfolge laufen und wollte ein Konto loeschen, auf das noch ein
    Kommentar verwies (Fremdschluessel-Fehler, gefunden durch
    test_expired_workspace_is_unusable_and_removed_on_the_next_start). Also:
    1. Tickets - ihre Kommentare und Historie folgen per ON DELETE CASCADE,
    2. danach verweist nichts mehr auf die Konten, sie koennen weg,
    3. zuletzt der Arbeitsbereich selbst.
    Bleibt dabei doch ein Verweis uebrig (ein Konto hat in einem FREMDEN
    Bereich kommentiert), bricht der Fremdschluessel das Loeschen ab - das
    waere ein Fehler in der Mandantentrennung und soll auffallen.

    Laeuft beim Anlegen jedes neuen Bereichs (siehe routers/demo.py) - so wird
    regelmaessig aufgeraeumt, ohne einen eigenen Hintergrundjob zu betreiben.
    Abgelaufene, noch nicht geloeschte Bereiche sind trotzdem sofort
    unbrauchbar: get_current_user lehnt ihre Konten ab.
    """
    expired_ids = list(db.scalars(select(DemoWorkspace.id).where(DemoWorkspace.expires_at <= now)))
    if not expired_ids:
        return 0
    db.execute(delete(Ticket).where(Ticket.workspace_id.in_(expired_ids)))
    db.execute(delete(User).where(User.workspace_id.in_(expired_ids)))
    db.execute(delete(DemoWorkspace).where(DemoWorkspace.id.in_(expired_ids)))
    return len(expired_ids)


def count_active_workspaces(db: Session, now: datetime) -> int:
    return db.scalar(select(func.count()).select_from(DemoWorkspace).where(DemoWorkspace.expires_at > now))


def create_demo_workspace(db: Session, *, now: datetime, lifetime: timedelta) -> DemoWorkspace:
    """Legt einen neuen Arbeitsbereich mit drei Konten und Beispieldaten an."""
    workspace = DemoWorkspace(expires_at=now + lifetime)
    db.add(workspace)
    db.flush()  # vergibt workspace.id, die Konten und Tickets brauchen sie
    members = {}
    for role, name in DEMO_PEOPLE:
        member = User(
            # E-Mail muss in der ganzen Datenbank eindeutig sein; die ID des
            # Arbeitsbereichs macht sie das. ".invalid" ist eine reservierte
            # Endung, an die nie eine echte E-Mail zugestellt werden kann.
            email=f"{role.value}.{workspace.id}@demo.smartdesk.invalid",
            full_name=name,
            role=role,
            hashed_password=NO_PASSWORD,
            workspace_id=workspace.id,
        )
        db.add(member)
        members[role] = member
    db.flush()
    add_sample_tickets(
        db, members[UserRole.EMPLOYEE], members[UserRole.AGENT], members[UserRole.ADMIN],
        now=now, workspace_id=workspace.id,
    )
    return workspace


def find_workspace_member(db: Session, workspace_id: int, role: UserRole) -> User | None:
    """Das Konto mit dieser Rolle im angegebenen Arbeitsbereich (fuer den
    Rollenwechsel). Fremde Arbeitsbereiche sind nie erreichbar, weil der
    Aufrufer immer den Bereich des angemeldeten Kontos uebergibt."""
    return db.scalar(select(User).where(User.workspace_id == workspace_id, User.role == role))
