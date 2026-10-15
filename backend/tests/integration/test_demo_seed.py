from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.models.user import User
from app.seed_demo import seed_demo


def test_demo_seed_is_guarded_idempotent_and_does_not_overwrite(db, monkeypatch):
    import pytest

    original_users = db.scalar(select(func.count()).select_from(User))
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    with pytest.raises(RuntimeError):
        seed_demo(db)
    assert db.scalar(select(func.count()).select_from(User)) == original_users
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    assert seed_demo(db) is True
    assert db.scalar(select(func.count()).select_from(User)) == original_users + 3
    assert db.scalar(select(func.count()).select_from(Ticket)) == 12
    assert db.scalar(select(func.count()).select_from(TicketEvent)) > 12
    assert seed_demo(db) is False
    assert db.scalar(select(func.count()).select_from(Ticket)) == 12
