from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.comment import Comment
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User, UserRole


def register(client, email="employee@example.com"):
    response = client.post("/auth/register", json={
        "email": email, "full_name": "Lena Fischer", "password": "integration-password", "role": "admin",
    })
    assert response.status_code == 201, response.text
    assert "hashed_password" not in response.json()
    assert response.json()["role"] == "employee"
    return response.json()


def staff(db, role=UserRole.AGENT, email="agent@example.com"):
    user = User(email=email, full_name="Support Agent", hashed_password="not-used", role=role)
    db.add(user)
    db.commit()
    return user


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def login(client):
    response = client.post("/auth/login", data={"username": "EMPLOYEE@example.com", "password": "integration-password"})
    assert response.status_code == 200, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    return response


def create_ticket(client):
    response = client.post("/tickets", json={"title": "VPN nicht erreichbar", "priority": "high", "status": "closed", "requester_id": 999})
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "open"
    return response.json()


def test_cookie_login_me_logout_and_duplicate_email(client):
    account = register(client)
    duplicate = client.post("/auth/register", json={"email": "EMPLOYEE@example.com", "full_name": "Other", "password": "integration-password"})
    assert duplicate.status_code == 409
    assert client.get("/tickets").status_code == 401
    login(client)
    assert client.get("/auth/me").json()["id"] == account["id"]
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/tickets").status_code == 401


def test_complete_lifecycle_and_atomic_history(client, db):
    employee = register(client)
    login(client)
    ticket = create_ticket(client)
    ticket_id = ticket["id"]
    assert ticket["requester_id"] == employee["id"]
    agent = staff(db)
    admin = staff(db, UserRole.ADMIN, "admin@example.com")
    path = f"/tickets/{ticket_id}/status"
    claim = client.patch(path, json={"status": "in_progress"}, headers=headers(agent))
    assert claim.status_code == 200, claim.text
    assert claim.json()["assignee_id"] == agent.id
    assert claim.json()["assignee_name"] == "Support Agent"
    assert client.patch(path, json={"status": "resolved"}, headers=headers(agent)).status_code == 200
    rejected = client.patch(path, json={"status": "in_progress"})
    assert rejected.status_code == 200
    assert rejected.json()["resolved_at"] is None
    resolved = client.patch(path, json={"status": "resolved"}, headers=headers(agent))
    assert resolved.json()["resolved_at"].endswith(("Z", "+00:00"))
    assert client.patch(path, json={"status": "closed"}, headers=headers(agent)).status_code == 403
    assert client.patch(path, json={"status": "closed"}, headers=headers(admin)).status_code == 200
    events = client.get(f"/tickets/{ticket_id}/history").json()
    assert len(events) == 6  # The denied close must not produce an event.
    assert events[1]["changes"]["assignee_id"]["new"] == agent.id
    assert events[0]["actor_name"] == "Lena Fischer"
    assert client.patch(f"/tickets/{ticket_id}", json={"title": "Edited"}, headers=headers(admin)).status_code == 409


def test_employee_cannot_access_foreign_tickets_comments_or_history(client, db):
    register(client)
    login(client)
    own = create_ticket(client)
    another = User(email="other@example.com", full_name="Other", role=UserRole.EMPLOYEE, hashed_password="unused")
    db.add(another)
    db.commit()
    auth = headers(another)
    assert client.get("/tickets", headers=auth).json() == []
    for suffix in ["", "/comments", "/history"]:
        assert client.get(f"/tickets/{own['id']}{suffix}", headers=auth).status_code == 404
    assert client.post(f"/tickets/{own['id']}/comments", json={"body": "Intrusion"}, headers=auth).status_code == 404
    assert client.patch(f"/tickets/{own['id']}/status", json={"status": "in_progress"}, headers=auth).status_code == 404
    assert client.get("/users", headers=auth).status_code == 403


def test_assignment_validation_and_foreign_agent_permissions(client, db):
    account = register(client)
    login(client)
    ticket = create_ticket(client)
    admin = staff(db, UserRole.ADMIN, "admin@example.com")
    agent = staff(db)
    other = staff(db, UserRole.AGENT, "other-agent@example.com")
    path = f"/tickets/{ticket['id']}"
    assert client.patch(path, json={"assignee_id": account["id"]}, headers=headers(admin)).status_code == 422
    assert client.patch(path, json={"assignee_id": 999999}, headers=headers(admin)).status_code == 404
    assert client.patch(path, json={"assignee_id": agent.id}, headers=headers(admin)).status_code == 200
    assert client.patch(f"{path}/status", json={"status": "in_progress"}, headers=headers(other)).status_code == 403
    assert client.patch(f"{path}/status", json={"status": "in_progress"}, headers=headers(agent)).status_code == 200
    assert client.patch(f"{path}/status", json={"status": "resolved"}, headers=headers(other)).status_code == 403
    assert client.get(path, headers=headers(other)).json()["allowed_transitions"] == []
    assert client.patch(path, json={"assignee_id": None}, headers=headers(admin)).status_code == 409
    assert client.patch(path, json={"assignee_id": other.id}, headers=headers(admin)).status_code == 200


def test_comment_author_validation_order_and_cascade_delete(client, db):
    account = register(client)
    login(client)
    ticket = create_ticket(client)
    path = f"/tickets/{ticket['id']}"
    comment = client.post(f"{path}/comments", json={"body": "  Ein Hinweis  ", "author_id": 999})
    assert comment.status_code == 201
    assert comment.json()["author_id"] == account["id"]
    assert comment.json()["author_name"] == "Lena Fischer"
    assert comment.json()["body"] == "Ein Hinweis"
    assert client.post(f"{path}/comments", json={"body": "   "}).status_code == 422
    assert len(client.get(f"{path}/comments").json()) == 1
    assert client.delete(path).status_code == 403
    admin = staff(db, UserRole.ADMIN, "admin@example.com")
    assert client.delete(path, headers=headers(admin)).status_code == 204
    assert db.scalar(select(func.count()).select_from(Comment).where(Comment.ticket_id == ticket["id"])) == 0
    assert db.scalar(select(func.count()).select_from(TicketEvent).where(TicketEvent.ticket_id == ticket["id"])) == 0
    assert db.get(Ticket, ticket["id"]) is None


def test_invalid_input_is_422_and_ticket_order_is_stable(client):
    register(client)
    login(client)
    assert client.post("/tickets", json={"title": " "}).status_code == 422
    first = create_ticket(client)
    urgent = client.post("/tickets", json={"title": "Outage", "priority": "critical"}).json()
    tickets = client.get("/tickets").json()
    assert [item["id"] for item in tickets] == [urgent["id"], first["id"]]
    assert client.get("/health/ready").status_code == 200
