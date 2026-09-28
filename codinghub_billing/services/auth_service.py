"""Authentication, password hashing, session state, and first-run RBAC
bootstrap (Section 8/9/23/37). GUI code must go through this service — never
hash/compare passwords or query User directly from a view."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import bcrypt
from sqlalchemy.orm import Session

from database.models.user import Permission, Role, User
from database.repositories.user_repository import PermissionRepository, RoleRepository, UserRepository


class AuthError(Exception):
    pass


PERMISSION_CODES: dict[str, str] = {
    "view": "View records",
    "create": "Create new records",
    "edit": "Edit existing records",
    "delete": "Delete records",
    "export": "Export data",
    "reports": "Access reports",
    "settings": "Manage settings",
    "users": "Manage users",
    "backup": "Manage backup/restore",
}

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Admin": list(PERMISSION_CODES.keys()),
    "Manager": ["view", "create", "edit", "export", "reports"],
    "Accountant": ["view", "create", "edit", "export", "reports", "backup"],
    "Operator": ["view", "create"],
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


@dataclass
class CurrentSession:
    user_id: int | None = None
    username: str | None = None
    full_name: str | None = None
    role_name: str | None = None
    permissions: set[str] = field(default_factory=set)

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def clear(self) -> None:
        self.user_id = None
        self.username = None
        self.full_name = None
        self.role_name = None
        self.permissions = set()


current_session = CurrentSession()


def seed_roles_and_permissions(session: Session) -> None:
    """Idempotent: creates the standard permission + role rows if missing."""
    permission_repo = PermissionRepository(session)
    role_repo = RoleRepository(session)

    permission_by_code: dict[str, Permission] = {}
    for code, description in PERMISSION_CODES.items():
        existing = permission_repo.get_by_code(code)
        if existing is None:
            existing = permission_repo.add(Permission(code=code, description=description))
        permission_by_code[code] = existing

    for role_name, codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = role_repo.get_by_name(role_name)
        if role is None:
            role = Role(name=role_name, description=f"{role_name} role")
            role.permissions = [permission_by_code[c] for c in codes]
            role_repo.add(role)
        else:
            role.permissions = [permission_by_code[c] for c in codes]


def is_first_run(session: Session) -> bool:
    return UserRepository(session).count() == 0


def bootstrap_first_run(
    session: Session,
    username: str,
    full_name: str,
    password: str,
    email: str | None = None,
) -> User:
    if not is_first_run(session):
        raise AuthError("Setup has already been completed.")

    seed_roles_and_permissions(session)

    admin_role = RoleRepository(session).get_by_name("Admin")
    if admin_role is None:
        raise AuthError("Admin role could not be created.")

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role_id=admin_role.id,
        is_active=True,
    )
    return UserRepository(session).add(user)


def login(session: Session, username: str, password: str) -> User:
    user = UserRepository(session).get_by_username(username.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid username or password.")
    if not user.is_active:
        raise AuthError("This account has been deactivated. Contact an administrator.")

    user.last_login_at = datetime.now(timezone.utc)
    session.flush()

    current_session.user_id = user.id
    current_session.username = user.username
    current_session.full_name = user.full_name
    current_session.role_name = user.role.name
    current_session.permissions = {p.code for p in user.role.permissions}
    return user


def logout() -> None:
    current_session.clear()
