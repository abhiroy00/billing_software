import pytest

from database.repositories.user_repository import RoleRepository
from services import auth_service, user_service


def _bootstrap_admin(session, username="admin"):
    return auth_service.bootstrap_first_run(session, username=username, full_name="Admin User", password="admin123")


def _valid_data(session, **overrides) -> dict:
    manager_role = next(r for r in user_service.list_roles(session) if r["name"] == "Manager")
    data = {
        "full_name": "Priya Sharma",
        "username": "priya",
        "email": "priya@example.com",
        "role_id": manager_role["id"],
        "password": "secret123",
    }
    data.update(overrides)
    return data


def test_create_user_success(db_session):
    _bootstrap_admin(db_session)
    user = user_service.create_user(db_session, None, _valid_data(db_session))

    assert user["username"] == "priya"
    assert user["role_name"] == "Manager"
    assert user["is_active"] is True


def test_create_user_duplicate_username_rejected(db_session):
    _bootstrap_admin(db_session)
    user_service.create_user(db_session, None, _valid_data(db_session))

    with pytest.raises(user_service.UserError, match="already taken"):
        user_service.create_user(db_session, None, _valid_data(db_session, email="other@example.com"))


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"full_name": ""}, "Full name"),
        ({"username": ""}, "Username"),
        ({"password": ""}, "Password"),
        ({"password": "123"}, "at least 6"),
        ({"email": "not-an-email"}, "valid email"),
    ],
)
def test_create_user_validation_errors(db_session, overrides, expected_snippet):
    _bootstrap_admin(db_session)
    with pytest.raises(user_service.UserError, match=expected_snippet):
        user_service.create_user(db_session, None, _valid_data(db_session, **overrides))


def test_update_user_changes_role_and_resets_password(db_session):
    _bootstrap_admin(db_session)
    created = user_service.create_user(db_session, None, _valid_data(db_session))

    operator_role = next(r for r in user_service.list_roles(db_session) if r["name"] == "Operator")
    updated = user_service.update_user(
        db_session, None, created["id"],
        {**_valid_data(db_session), "role_id": operator_role["id"], "password": "newpassword123"},
    )
    assert updated["role_name"] == "Operator"


def test_update_user_duplicate_username_rejected(db_session):
    _bootstrap_admin(db_session)
    user_service.create_user(db_session, None, _valid_data(db_session, username="priya"))
    second = user_service.create_user(db_session, None, _valid_data(db_session, username="rahul", email="rahul@example.com"))

    with pytest.raises(user_service.UserError, match="already taken"):
        user_service.update_user(db_session, None, second["id"], _valid_data(db_session, username="priya"))


def test_cannot_deactivate_own_account(db_session):
    admin = _bootstrap_admin(db_session)
    with pytest.raises(user_service.UserError, match="cannot deactivate your own account"):
        user_service.set_user_active(db_session, admin.id, admin.id, False)


def test_cannot_deactivate_last_active_admin(db_session):
    admin = _bootstrap_admin(db_session)
    # actor_user_id differs from target so the "own account" guard doesn't trip;
    # the last-admin guard should still block it.
    with pytest.raises(user_service.UserError, match="last active Admin"):
        user_service.set_user_active(db_session, None, admin.id, False)


def test_can_deactivate_admin_when_another_admin_remains(db_session):
    admin = _bootstrap_admin(db_session)
    admin_role = RoleRepository(db_session).get_by_name("Admin")
    second_admin = user_service.create_user(
        db_session, None, _valid_data(db_session, username="second_admin", email="second@example.com", role_id=admin_role.id)
    )

    result = user_service.set_user_active(db_session, None, admin.id, False)
    assert result["is_active"] is False
    # second admin remains active, so deactivating the original admin is fine.
    assert user_service.get_user_dict(db_session, second_admin["id"])["is_active"] is True


def test_list_users_search_and_role_filter(db_session):
    _bootstrap_admin(db_session)
    user_service.create_user(db_session, None, _valid_data(db_session))

    all_users = user_service.list_users(db_session)
    assert len(all_users) == 2

    searched = user_service.list_users(db_session, query="priya")
    assert len(searched) == 1
    assert searched[0]["username"] == "priya"

    manager_role = next(r for r in user_service.list_roles(db_session) if r["name"] == "Manager")
    managers_only = user_service.list_users(db_session, role_id=manager_role["id"])
    assert len(managers_only) == 1
    assert managers_only[0]["username"] == "priya"
