import pytest
from fastapi import HTTPException

from app.core.deps import require_roles
from app.models.user import User, UserRole

# require_roles(...) gibt eine Funktion zurueck (check_role), die selbst wieder
# Depends(get_current_user) im Signatur-Default hat. Beim direkten Aufruf in
# einem Test (statt ueber FastAPIs Dependency-Injection) wird current_user
# einfach als normales Keyword-Argument uebergeben - der Depends(...)-Default
# wird dabei schlicht durch unseren Wert ueberschrieben, es passiert kein
# echter DB-Zugriff. Kein Server, keine DB noetig.


def make_user(role: UserRole) -> User:
    return User(id=1, email="user@test.local", hashed_password="x", full_name="Test", role=role)


def test_require_roles_allows_matching_role():
    check_role = require_roles(UserRole.ADMIN)
    admin = make_user(UserRole.ADMIN)

    assert check_role(current_user=admin) is admin


def test_require_roles_rejects_other_role():
    check_role = require_roles(UserRole.ADMIN)
    agent = make_user(UserRole.AGENT)

    with pytest.raises(HTTPException) as exc_info:
        check_role(current_user=agent)

    assert exc_info.value.status_code == 403


def test_require_roles_accepts_any_of_multiple_allowed_roles():
    check_role = require_roles(UserRole.AGENT, UserRole.ADMIN)
    agent = make_user(UserRole.AGENT)
    admin = make_user(UserRole.ADMIN)

    assert check_role(current_user=agent) is agent
    assert check_role(current_user=admin) is admin


def test_require_roles_rejects_employee_when_not_listed():
    check_role = require_roles(UserRole.AGENT, UserRole.ADMIN)
    employee = make_user(UserRole.EMPLOYEE)

    with pytest.raises(HTTPException) as exc_info:
        check_role(current_user=employee)

    assert exc_info.value.status_code == 403
