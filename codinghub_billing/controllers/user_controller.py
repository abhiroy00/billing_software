"""GUI-facing layer over user_service (Section 23). Every mutating action
re-checks the "users" permission here too — the nav item being hidden is
not the only line of defense."""
from __future__ import annotations

import logging

from database.connection import get_session
from services import auth_service, user_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

PERMISSION_DENIED = "You do not have permission to manage users."


def _require_users_permission() -> str | None:
    if not auth_service.current_session.has_permission("users"):
        return PERMISSION_DENIED
    return None


def list_roles() -> list[dict]:
    with get_session() as session:
        return user_service.list_roles(session)


def list_users(query: str = "", role_id: int | None = None) -> list[dict]:
    with get_session() as session:
        return user_service.list_users(session, query=query, role_id=role_id)


def get_user(user_id: int) -> dict | None:
    with get_session() as session:
        return user_service.get_user_dict(session, user_id)


def create_user(data: dict) -> tuple[bool, str, dict | None]:
    denied = _require_users_permission()
    if denied:
        return False, denied, None
    try:
        with get_session() as session:
            user = user_service.create_user(session, auth_service.current_session.user_id, data)
        return True, "", user
    except user_service.UserError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to create user")
        return False, USER_FRIENDLY_MESSAGE, None


def update_user(user_id: int, data: dict) -> tuple[bool, str, dict | None]:
    denied = _require_users_permission()
    if denied:
        return False, denied, None
    try:
        with get_session() as session:
            user = user_service.update_user(session, auth_service.current_session.user_id, user_id, data)
        return True, "", user
    except user_service.UserError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to update user")
        return False, USER_FRIENDLY_MESSAGE, None


def set_user_active(user_id: int, is_active: bool) -> tuple[bool, str]:
    denied = _require_users_permission()
    if denied:
        return False, denied
    try:
        with get_session() as session:
            user_service.set_user_active(session, auth_service.current_session.user_id, user_id, is_active)
        return True, ""
    except user_service.UserError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to update user status")
        return False, USER_FRIENDLY_MESSAGE
