"""Welche Personen ein angemeldetes Konto sehen darf - das Gegenstueck zu
services/ticket_access.py fuer Konten. Genutzt von der Nutzerliste
(routers/users.py, Bearbeiter-Auswahl) und bei der Zuweisung eines Bearbeiters
(routers/tickets.py)."""
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.workspace_scope import same_workspace


def visible_users_query(current_user: User) -> Select[tuple[User]]:
    """Alle Konten aus dem eigenen Arbeitsbereich (bei normalen Konten: alle
    normalen Konten). Wer ueberhaupt Personen auflisten darf (Agent/Admin),
    regelt routers/users.py ueber require_roles."""
    return select(User).where(same_workspace(User.workspace_id, current_user.workspace_id))


def get_visible_user(db: Session, user_id: int, current_user: User) -> User | None:
    """Das Konto mit dieser ID - oder None, wenn es nicht existiert ODER zu
    einem anderen Arbeitsbereich gehoert. Beides absichtlich gleich, damit
    Konten fremder Arbeitsbereiche nicht einmal erkennbar sind (dieselbe Idee
    wie get_visible_ticket_or_404)."""
    user = db.get(User, user_id)
    if user is None or user.workspace_id != current_user.workspace_id:
        return None
    return user
