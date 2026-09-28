import pytest

from database.repositories.user_repository import RoleRepository
from services import auth_service


def test_first_run_bootstrap_creates_admin(db_session):
    assert auth_service.is_first_run(db_session) is True

    user = auth_service.bootstrap_first_run(
        db_session, username="admin", full_name="Admin User", password="secret123", email="admin@codinghub.test"
    )

    assert user.id is not None
    assert user.role.name == "Admin"
    assert auth_service.is_first_run(db_session) is False


def test_bootstrap_twice_raises(db_session):
    auth_service.bootstrap_first_run(db_session, username="admin", full_name="Admin", password="secret123")
    with pytest.raises(auth_service.AuthError):
        auth_service.bootstrap_first_run(db_session, username="admin2", full_name="Admin2", password="secret123")


def test_login_success_sets_session_and_permissions(db_session):
    auth_service.bootstrap_first_run(db_session, username="admin", full_name="Admin", password="secret123")

    user = auth_service.login(db_session, "admin", "secret123")

    assert user.username == "admin"
    assert auth_service.current_session.is_authenticated
    assert auth_service.current_session.has_permission("users")
    assert auth_service.current_session.has_permission("backup")

    auth_service.logout()
    assert not auth_service.current_session.is_authenticated


def test_login_wrong_password_raises(db_session):
    auth_service.bootstrap_first_run(db_session, username="admin", full_name="Admin", password="secret123")
    with pytest.raises(auth_service.AuthError):
        auth_service.login(db_session, "admin", "wrongpassword")


def test_login_unknown_username_raises(db_session):
    with pytest.raises(auth_service.AuthError):
        auth_service.login(db_session, "nobody", "whatever")


def test_role_permission_defaults(db_session):
    auth_service.seed_roles_and_permissions(db_session)

    manager = RoleRepository(db_session).get_by_name("Manager")
    operator = RoleRepository(db_session).get_by_name("Operator")

    assert {p.code for p in manager.permissions} == {"view", "create", "edit", "export", "reports"}
    assert {p.code for p in operator.permissions} == {"view", "create"}
