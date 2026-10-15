from app.models.user import UserRole
from test_workflows import create_ticket, headers, login, register, staff


def test_content_edit_is_partial_versioned_and_recorded(client, db):
    register(client)
    login(client)
    ticket = create_ticket(client)
    agent = staff(db)
    path = f"/tickets/{ticket['id']}"
    response = client.patch(path, headers=headers(agent), json={
        "title": "  VPN am Standort  ", "description": "Weitere Details", "priority": "critical",
        "expected_version": ticket["version"],
    })
    assert response.status_code == 200, response.text
    edited = response.json()
    assert edited["title"] == "VPN am Standort"
    assert edited["description"] == "Weitere Details"
    assert edited["priority"] == "critical"
    assert edited["version"] == ticket["version"] + 1
    assert edited["status"] == ticket["status"]
    assert edited["requester_id"] == ticket["requester_id"]
    assert edited["assignee_id"] is None
    events = client.get(f"{path}/history").json()
    assert len(events) == 2
    assert events[-1]["actor_name"] == agent.full_name
    assert events[-1]["changes"] == {
        "title": {"old": ticket["title"], "new": "VPN am Standort"},
        "description": {"old": None, "new": "Weitere Details"},
        "priority": {"old": "high", "new": "critical"},
    }
    cleared = client.patch(path, headers=headers(agent), json={
        "description": None, "expected_version": edited["version"],
    })
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["title"] == edited["title"]


def test_stale_content_edit_does_not_overwrite_or_add_history(client, db):
    register(client)
    login(client)
    ticket = create_ticket(client)
    agent = staff(db)
    path = f"/tickets/{ticket['id']}"
    first = client.patch(path, headers=headers(agent), json={
        "title": "Aktueller Titel", "expected_version": ticket["version"],
    })
    assert first.status_code == 200
    stale = client.patch(path, headers=headers(agent), json={
        "title": "Veralteter Entwurf", "expected_version": ticket["version"],
    })
    assert stale.status_code == 409
    assert client.get(path).json()["title"] == "Aktueller Titel"
    assert len(client.get(f"{path}/history").json()) == 2


def test_status_and_assignment_changes_invalidate_older_editor_versions(client, db):
    register(client)
    login(client)
    ticket = create_ticket(client)
    agent = staff(db)
    admin = staff(db, UserRole.ADMIN, "admin@example.com")
    path = f"/tickets/{ticket['id']}"
    assigned = client.patch(path, headers=headers(admin), json={
        "assignee_id": agent.id, "expected_version": ticket["version"],
    })
    assert assigned.status_code == 200
    assert assigned.json()["version"] == ticket["version"] + 1
    claimed = client.patch(f"{path}/status", headers=headers(agent), json={"status": "in_progress"})
    assert claimed.status_code == 200
    assert claimed.json()["version"] == assigned.json()["version"] + 1
    stale = client.patch(path, headers=headers(agent), json={
        "priority": "low", "expected_version": assigned.json()["version"],
    })
    assert stale.status_code == 409
    assert client.get(path).json()["priority"] == "high"


def test_employee_and_closed_tickets_cannot_be_edited(client, db):
    register(client)
    login(client)
    ticket = create_ticket(client)
    path = f"/tickets/{ticket['id']}"
    assert client.patch(path, json={"title": "Not allowed", "expected_version": ticket["version"]}).status_code == 403
    admin = staff(db, UserRole.ADMIN, "admin@example.com")
    for status in ["in_progress", "resolved", "closed"]:
        assert client.patch(f"{path}/status", json={"status": status}, headers=headers(admin)).status_code == 200
    current = client.get(path).json()
    assert client.patch(path, json={"title": "Not allowed", "expected_version": current["version"]}, headers=headers(admin)).status_code == 409


def test_no_op_patch_keeps_version_and_history(client, db):
    register(client)
    login(client)
    ticket = create_ticket(client)
    agent = staff(db)
    path = f"/tickets/{ticket['id']}"
    response = client.patch(path, headers=headers(agent), json={
        "title": ticket["title"], "expected_version": ticket["version"],
    })
    assert response.status_code == 200
    assert response.json()["version"] == ticket["version"]
    assert len(client.get(f"{path}/history").json()) == 1
