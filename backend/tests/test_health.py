import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from app.main import health, readiness

# Statt einer echten Datenbank-Session bekommt readiness() kleine Ersatz-
# Objekte ("Test-Doubles") mit derselben execute()-Methode - readiness ruft
# nur genau diese eine Methode auf, mehr muessen die Doubles nicht koennen.


class ReachableDatabase:
    def execute(self, statement):
        return None


class UnreachableDatabase:
    def execute(self, statement):
        # Genau dieser Fehler kommt von SQLAlchemy, wenn z.B. das Passwort in
        # DATABASE_URL nicht stimmt oder der Postgres-Container gestoppt ist.
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_liveness_does_not_need_the_database():
    assert health() == {"status": "ok"}


def test_readiness_reports_ok_when_database_answers():
    assert readiness(db=ReachableDatabase()) == {"status": "ok", "database": "ok"}


def test_readiness_returns_503_when_database_is_unreachable():
    with pytest.raises(HTTPException) as exc_info:
        readiness(db=UnreachableDatabase())

    assert exc_info.value.status_code == 503
