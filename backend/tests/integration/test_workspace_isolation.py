"""Mandantentrennung der oeffentlichen Demo: Besucher A sieht und aendert
nichts aus dem Arbeitsbereich von Besucher B - ueber JEDEN Endpunkt, nicht nur
ueber die, die die Oberflaeche gerade benutzt.

Die Konten werden gezielt ueber headers() gewaehlt (Bearer-Token statt
Cookie), so lassen sich A und B im selben Test abwechselnd verwenden.
"""
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.comment import Comment
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def start_workspace(client, db):
    """Startet einen Arbeitsbereich wie ein Besucher ("Demo starten") und
    vergisst danach den Cookie, damit der naechste Start ein neuer Besucher ist."""
    response = client.post("/demo/sessions")
    assert response.status_code == 201, response.text
    client.cookies.clear()
    workspace_id = db.get(User, response.json()["id"]).workspace_id
    members = {user.role: user for user in db.scalars(select(User).where(User.workspace_id == workspace_id))}
    tickets = list(db.scalars(select(Ticket).where(Ticket.workspace_id == workspace_id).order_by(Ticket.id)))
    return SimpleNamespace(id=workspace_id, members=members, tickets=tickets)


@pytest.fixture
def two_workspaces(client, db, public_demo):
    return start_workspace(client, db), start_workspace(client, db)


def comment_count(db, ticket_id):
    return db.scalar(select(func.count()).select_from(Comment).where(Comment.ticket_id == ticket_id))


@pytest.mark.parametrize("role", list(UserRole))
def test_every_role_lists_only_tickets_of_the_own_workspace(client, two_workspaces, role):
    a, _ = two_workspaces

    listed = {ticket["id"] for ticket in client.get("/tickets", headers=headers(a.members[role])).json()}

    assert listed == {ticket.id for ticket in a.tickets}


# Jeder Weg, auf dem ein Ticket geladen wird. Vergisst ein Endpunkt die Regel,
# faellt das genau hier auf - nicht erst, wenn ein Besucher es ausprobiert.
FOREIGN_TICKET_REQUESTS = [
    ("GET", "", None),
    ("PATCH", "", {"title": "Von Besucher A überschrieben"}),
    ("PATCH", "/status", {"status": "in_progress"}),
    ("DELETE", "", None),
    ("GET", "/comments", None),
    ("POST", "/comments", {"body": "Unfug von Besucher A"}),
    ("GET", "/history", None),
]


@pytest.mark.parametrize(("method", "suffix", "body"), FOREIGN_TICKET_REQUESTS)
def test_tickets_of_another_workspace_do_not_exist_for_any_endpoint(client, db, two_workspaces, method, suffix, body):
    a, b = two_workspaces
    target = next(ticket for ticket in b.tickets if ticket.status == TicketStatus.OPEN)
    title_before, comments_before = target.title, comment_count(db, target.id)

    response = client.request(
        method, f"/tickets/{target.id}{suffix}", headers=headers(a.members[UserRole.ADMIN]), json=body,
    )

    # Dieselbe 404 wie fuer eine Ticketnummer, die es gar nicht gibt: fremde
    # Arbeitsbereiche sollen nicht einmal als existent erkennbar sein.
    assert response.status_code == 404, response.text
    db.expire_all()  # frisch aus der Datenbank lesen
    unchanged = db.get(Ticket, target.id)
    assert unchanged is not None
    assert (unchanged.title, unchanged.status) == (title_before, TicketStatus.OPEN)
    assert comment_count(db, target.id) == comments_before


def test_user_directory_and_lookup_stay_inside_the_own_workspace(client, two_workspaces):
    a, b = two_workspaces
    admin_a = a.members[UserRole.ADMIN]

    listed = {user["id"] for user in client.get("/users", headers=headers(admin_a)).json()}

    assert listed == {user.id for user in a.members.values()}
    assert client.get(f"/users/{b.members[UserRole.ADMIN].id}", headers=headers(admin_a)).status_code == 404


def test_tickets_cannot_be_assigned_to_people_of_another_workspace(client, db, two_workspaces):
    a, b = two_workspaces
    ticket = next(ticket for ticket in a.tickets if ticket.status == TicketStatus.OPEN)

    response = client.patch(
        f"/tickets/{ticket.id}",
        json={"assignee_id": b.members[UserRole.AGENT].id, "expected_version": ticket.version},
        headers=headers(a.members[UserRole.ADMIN]),
    )

    assert response.status_code == 404
    db.expire_all()
    assert db.get(Ticket, ticket.id).assignee_id is None


def test_normal_accounts_and_demo_workspaces_never_see_each_other(client, db, two_workspaces):
    """Normale Daten haben workspace_id = NULL. Sichert zugleich die NULL-Falle
    ab: "workspace_id = NULL" ist in SQL nie wahr - ein naiver Filter wuerde
    einem normalen Agent ALLE normalen Tickets verstecken."""
    a, _ = two_workspaces
    normal_agent = User(email="normal-agent@example.com", full_name="Normaler Agent", hashed_password="x", role=UserRole.AGENT)
    normal_employee = User(email="normal@example.com", full_name="Normale Mitarbeiterin", hashed_password="x", role=UserRole.EMPLOYEE)
    db.add_all([normal_agent, normal_employee])
    db.flush()
    normal_ticket = Ticket(title="Normales Ticket", requester_id=normal_employee.id)
    db.add(normal_ticket)
    db.commit()

    seen_by_normal_agent = {ticket["id"] for ticket in client.get("/tickets", headers=headers(normal_agent)).json()}
    assert normal_ticket.id in seen_by_normal_agent
    assert not seen_by_normal_agent & {ticket.id for ticket in a.tickets}
    assert client.get(f"/tickets/{normal_ticket.id}", headers=headers(a.members[UserRole.ADMIN])).status_code == 404

    directory = {user["id"] for user in client.get("/users", headers=headers(normal_agent)).json()}
    assert normal_agent.id in directory
    assert not directory & {user.id for user in a.members.values()}
