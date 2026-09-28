"""User & role management (Section 23). Distinct from auth_service, which
owns login/session state — this is the admin-facing CRUD over accounts.
Users are never hard-deleted (they're referenced by invoices/payments/
expenses/audit log as the acting user) — only deactivated."""
from __future__ import annotations

from database.models.user import User
from database.repositories.user_repository import RoleRepository, UserRepository
from services import audit_service
from services.auth_service import hash_password
from utils import validators


class UserError(Exception):
    pass


def _to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else "",
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
    }


def list_roles(session) -> list[dict]:
    return [{"id": r.id, "name": r.name} for r in RoleRepository(session).list()]


def list_users(session, query: str = "", role_id: int | None = None) -> list[dict]:
    return [_to_dict(u) for u in UserRepository(session).search(query=query, role_id=role_id)]


def get_user_dict(session, user_id: int) -> dict | None:
    user = UserRepository(session).get(user_id)
    return _to_dict(user) if user else None


def _validate_common(data: dict) -> list[str]:
    return validators.run_validators(
        validators.required(data.get("full_name"), "Full name"),
        validators.required(data.get("username"), "Username"),
        validators.valid_email(data.get("email")),
        validators.required(data.get("role_id"), "Role"),
    )


def create_user(session, actor_user_id: int | None, data: dict) -> dict:
    errors = _validate_common(data)
    password = data.get("password") or ""
    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if errors:
        raise UserError(" ".join(errors))

    repo = UserRepository(session)
    if repo.get_by_username(data["username"].strip()):
        raise UserError("This username is already taken.")

    user = User(
        username=data["username"].strip(),
        full_name=data["full_name"].strip(),
        email=(data.get("email") or "").strip() or None,
        password_hash=hash_password(password),
        role_id=data["role_id"],
        is_active=True,
    )
    repo.add(user)
    audit_service.log(
        session, actor_user_id, "create", entity_type="user", entity_id=user.id,
        description=f"Created user {user.username}",
    )
    return _to_dict(user)


def update_user(session, actor_user_id: int | None, user_id: int, data: dict) -> dict:
    errors = _validate_common(data)
    if errors:
        raise UserError(" ".join(errors))

    repo = UserRepository(session)
    user = repo.get(user_id)
    if user is None:
        raise UserError("User not found.")

    existing = repo.get_by_username(data["username"].strip())
    if existing and existing.id != user_id:
        raise UserError("This username is already taken.")

    if not data.get("is_active", True) and user_id == actor_user_id:
        raise UserError("You cannot deactivate your own account.")
    if not data.get("is_active", True):
        _guard_last_admin(session, user)

    user.username = data["username"].strip()
    user.full_name = data["full_name"].strip()
    user.email = (data.get("email") or "").strip() or None
    user.role_id = data["role_id"]
    user.is_active = data.get("is_active", user.is_active)

    new_password = data.get("password") or ""
    if new_password:
        if len(new_password) < 6:
            raise UserError("Password must be at least 6 characters.")
        user.password_hash = hash_password(new_password)

    repo.update(user)
    audit_service.log(
        session, actor_user_id, "update", entity_type="user", entity_id=user.id,
        description=f"Updated user {user.username}",
    )
    return _to_dict(user)


def _guard_last_admin(session, user: User) -> None:
    admin_role = RoleRepository(session).get_by_name("Admin")
    if admin_role and user.role_id == admin_role.id:
        remaining = UserRepository(session).count_active_admins(admin_role.id, exclude_user_id=user.id)
        if remaining == 0:
            raise UserError("Cannot deactivate the last active Admin account.")


def set_user_active(session, actor_user_id: int | None, user_id: int, is_active: bool) -> dict:
    if user_id == actor_user_id and not is_active:
        raise UserError("You cannot deactivate your own account.")

    repo = UserRepository(session)
    user = repo.get(user_id)
    if user is None:
        raise UserError("User not found.")

    if not is_active:
        _guard_last_admin(session, user)

    user.is_active = is_active
    repo.update(user)
    audit_service.log(
        session, actor_user_id, "update", entity_type="user", entity_id=user.id,
        description=f"{'Activated' if is_active else 'Deactivated'} user {user.username}",
    )
    return _to_dict(user)
