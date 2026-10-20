"""Oeffentliche Demo: Arbeitsbereiche anlegen, Rollen wechseln, ablaufen lassen.

Die Isolation ZWISCHEN Arbeitsbereichen (Besucher A sieht nichts von B)
pruefen eigene Tests zur Sichtbarkeitsregel - hier geht es um das Anlegen
und Bedienen eines einzelnen Bereichs.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from limits.storage import MemoryStorage
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.demo_rate_limit import DemoSessionLimiter, get_demo_session_limiter
from app.core.security import ACCESS_TOKEN_COOKIE_NAME
from app.main import app
from app.models.comment import Comment
from app.models.demo_workspace import DemoWorkspace
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User


@pytest.fixture
def public_demo(client, monkeypatch):
    """Schaltet die oeffentliche Demo fuer einen Test ein und ersetzt die
    Redis-Begrenzung durch einen Zaehler im Speicher (wie die Login-Tests).
    Gibt eine Funktion zurueck, mit der ein Test die Begrenzung enger stellen kann."""
    settings = get_settings()
    monkeypatch.setattr(settings, "public_demo", True)

    def use_limiter():
        limiter = DemoSessionLimiter(settings, MemoryStorage())
        app.dependency_overrides[get_demo_session_limiter] = lambda: limiter

    use_limiter()
    yield use_limiter
    app.dependency_overrides.pop(get_demo_session_limiter, None)


def start(client):
    response = client.post("/demo/sessions")
    assert response.status_code == 201, response.text
    return response


def count(db, model, *conditions):
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def test_demo_endpoints_do_not_exist_without_public_demo(client):
    assert client.get("/demo/config").json()["public_demo"] is False
    assert client.post("/demo/sessions").status_code == 404
    assert client.post("/demo/sessions/role", json={"role": "admin"}).status_code == 404


def test_start_creates_a_private_workspace_and_logs_in_as_employee(client, db, public_demo):
    response = start(client)
    me = response.json()
    assert me["role"] == "employee"
    assert me["full_name"] == "Lena Fischer"
    assert me["demo_expires_at"] is not None
    assert "HttpOnly" in response.headers["set-cookie"]

    user = db.get(User, me["id"])
    workspace_id = user.workspace_id
    assert workspace_id is not None
    assert count(db, User, User.workspace_id == workspace_id) == 3
    assert count(db, Ticket, Ticket.workspace_id == workspace_id) == 12
    # Die Sitzung funktioniert sofort, ganz ohne Passwort.
    assert client.get("/auth/me").json()["demo_expires_at"] == me["demo_expires_at"]
    assert len(client.get("/tickets").json()) == 12


def test_demo_session_lasts_as_long_as_the_workspace(client, public_demo):
    """Nicht nur die normalen 60 Minuten: sonst endete eine Demo mitten im Ausprobieren."""
    me = start(client).json()
    token = client.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    payload = jwt.decode(token, options={"verify_signature": False})
    expires_at = datetime.fromisoformat(me["demo_expires_at"])
    assert abs(payload["exp"] - expires_at.timestamp()) < 2
    assert expires_at - datetime.now(timezone.utc) > timedelta(hours=get_settings().demo_workspace_ttl_hours - 1)


def test_demo_accounts_have_no_usable_password(client, db, public_demo):
    me = start(client).json()
    client.cookies.clear()
    response = client.post("/auth/login", data={"username": me["email"], "password": "irgendwas-langes"})
    assert response.status_code == 401


def test_role_switch_stays_inside_the_own_workspace(client, db, public_demo):
    employee = start(client).json()
    workspace_id = db.get(User, employee["id"]).workspace_id

    agent = client.post("/demo/sessions/role", json={"role": "agent"})
    assert agent.status_code == 200, agent.text
    assert agent.json()["full_name"] == "Alex Weber"
    assert db.get(User, agent.json()["id"]).workspace_id == workspace_id
    assert client.get("/auth/me").json()["role"] == "agent"

    admin = client.post("/demo/sessions/role", json={"role": "admin"}).json()
    assert admin["full_name"] == "Samira Kaya"
    assert db.get(User, admin["id"]).workspace_id == workspace_id
    assert client.post("/demo/sessions/role", json={"role": "superuser"}).status_code == 422


def test_normal_accounts_cannot_use_the_role_switch(client, db, public_demo):
    register = client.post("/auth/register", json={
        "email": "normal@example.com", "full_name": "Normales Konto", "password": "integration-password",
    })
    assert register.status_code == 201
    client.post("/auth/login", data={"username": "normal@example.com", "password": "integration-password"})
    assert client.post("/demo/sessions/role", json={"role": "admin"}).status_code == 403


def test_new_tickets_stay_in_the_workspace(client, db, public_demo):
    me = start(client).json()
    created = client.post("/tickets", json={"title": "Eigener Testfall", "priority": "low"})
    assert created.status_code == 201
    ticket = db.get(Ticket, created.json()["id"])
    assert ticket.workspace_id == db.get(User, me["id"]).workspace_id


def test_expired_workspace_is_unusable_and_removed_on_the_next_start(client, db, public_demo):
    me = start(client).json()
    old_workspace_id = db.get(User, me["id"]).workspace_id
    workspace = db.get(DemoWorkspace, old_workspace_id)
    workspace.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    # Noch nicht geloescht, aber schon gesperrt.
    assert client.get("/auth/me").status_code == 401

    start(client)
    db.expire_all()  # frisch aus der Datenbank lesen statt aus dem Session-Zwischenspeicher
    assert db.get(DemoWorkspace, old_workspace_id) is None
    # Das CASCADE hat alles mitgenommen: Konten, Tickets und deren Kommentare/Historie.
    assert count(db, User, User.workspace_id == old_workspace_id) == 0
    assert count(db, Ticket, Ticket.workspace_id == old_workspace_id) == 0
    orphaned = select(Ticket.id).where(Ticket.workspace_id == old_workspace_id)
    assert count(db, Comment, Comment.ticket_id.in_(orphaned)) == 0
    assert count(db, TicketEvent, TicketEvent.ticket_id.in_(orphaned)) == 0


def test_one_ip_can_only_start_a_limited_number_of_demos(client, monkeypatch, public_demo):
    monkeypatch.setattr(get_settings(), "demo_session_ip_attempts", 2)
    public_demo()  # Begrenzung mit dem engeren Wert neu aufbauen
    start(client)
    start(client)
    blocked = client.post("/demo/sessions")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_the_number_of_active_workspaces_is_capped(client, db, monkeypatch, public_demo):
    active = count(db, DemoWorkspace, DemoWorkspace.expires_at > datetime.now(timezone.utc))
    monkeypatch.setattr(get_settings(), "demo_max_active_workspaces", active + 1)
    start(client)
    full = client.post("/demo/sessions")
    assert full.status_code == 503
    assert full.headers["Retry-After"] == "300"


def test_registration_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "registration_enabled", False)
    response = client.post("/auth/register", json={
        "email": "spam@example.com", "full_name": "Spam", "password": "integration-password",
    })
    assert response.status_code == 403
