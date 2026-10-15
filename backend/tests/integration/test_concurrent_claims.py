from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.ticket_event import TicketEvent
from app.models.user import User, UserRole


@pytest.mark.parametrize("operation", ["claim", "edit"])
def test_competing_changes_commit_one_winner_and_one_event(test_engine, operation):
    """Force both requests to wait on the same PostgreSQL row before releasing it."""
    suffix = uuid4().hex
    with Session(test_engine) as setup:
        users = [User(email=f"{suffix}-{i}@example.com", full_name=f"Agent {i}", role=UserRole.AGENT, hashed_password="unused") for i in range(2)]
        setup.add_all(users)
        setup.flush()
        ids = [user.id for user in users]
        ticket = Ticket(title="Concurrent claim", status=TicketStatus.OPEN, priority=TicketPriority.HIGH, requester_id=ids[0])
        setup.add(ticket)
        setup.commit()
        ticket_id = ticket.id

    def independent_session():
        with Session(test_engine) as session:
            yield session

    start = Barrier(3)

    def claim(user_id):
        with TestClient(app) as client:
            start.wait(timeout=10)
            return client.patch(
                f"/tickets/{ticket_id}" + ("/status" if operation == "claim" else ""),
                json={"status": "in_progress"} if operation == "claim" else {"title": f"Edited by {user_id}", "expected_version": 1},
                headers={"Authorization": f"Bearer {create_access_token(user_id, 'agent')}"},
            )

    app.dependency_overrides[get_db] = independent_session
    try:
        with test_engine.connect() as lock_connection:
            transaction = lock_connection.begin()
            lock_connection.execute(select(Ticket.id).where(Ticket.id == ticket_id).with_for_update())
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(claim, user_id) for user_id in ids]
                try:
                    start.wait(timeout=10)
                    deadline = time.monotonic() + 10
                    waiting = 0
                    while time.monotonic() < deadline:
                        with test_engine.connect() as observer:
                            waiting = observer.scalar(text(
                                "SELECT count(*) FROM pg_stat_activity "
                                "WHERE datname = current_database() AND wait_event_type = 'Lock' "
                                "AND query LIKE 'SELECT tickets.%'"
                            ))
                        if waiting >= 2:
                            break
                        time.sleep(0.02)
                    assert waiting >= 2, "Both claims must wait for the locked ticket row"
                finally:
                    transaction.rollback()
                responses = [future.result(timeout=10) for future in futures]
        assert sorted(response.status_code for response in responses) == [200, 409]
        winner = next(response.json() for response in responses if response.status_code == 200)
        with Session(test_engine) as check:
            stored = check.get(Ticket, ticket_id)
            assert stored.assignee_id == winner["assignee_id"]
            assert stored.title == winner["title"]
            assert stored.version == 2
            assert check.scalar(select(func.count()).select_from(TicketEvent).where(TicketEvent.ticket_id == ticket_id)) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        with test_engine.begin() as cleanup:
            cleanup.execute(delete(Ticket).where(Ticket.id == ticket_id))
            cleanup.execute(delete(User).where(User.id.in_(ids)))
