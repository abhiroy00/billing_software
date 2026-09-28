"""Thin GUI-facing layer over auth_service + settings_service. Views call
these functions and get back plain (success, message) results — they never
open a DB session or touch the ORM directly."""
from __future__ import annotations

from database.connection import get_session
from services import auth_service, settings_service
from utils.logger import USER_FRIENDLY_MESSAGE
import logging

logger = logging.getLogger("codinghub")


def is_first_run() -> bool:
    with get_session() as session:
        return auth_service.is_first_run(session)


def complete_first_run_setup(
    business_info: dict,
    admin_info: dict,
    invoice_info: dict,
) -> tuple[bool, str]:
    try:
        with get_session() as session:
            settings_service.save_business_settings(session, **business_info)
            settings_service.save_invoice_settings(session, **invoice_info)
            auth_service.bootstrap_first_run(
                session,
                username=admin_info["username"],
                full_name=admin_info["full_name"],
                password=admin_info["password"],
                email=admin_info.get("email"),
            )
        return True, ""
    except auth_service.AuthError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Setup wizard failed")
        return False, USER_FRIENDLY_MESSAGE


def login(username: str, password: str) -> tuple[bool, str]:
    try:
        with get_session() as session:
            auth_service.login(session, username, password)
        return True, ""
    except auth_service.AuthError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Login failed unexpectedly")
        return False, USER_FRIENDLY_MESSAGE


def logout() -> None:
    auth_service.logout()


_REMEMBERED_USERNAME_KEY = "remembered_username"


def get_remembered_username() -> str:
    with get_session() as session:
        return settings_service.get_app_setting(session, _REMEMBERED_USERNAME_KEY, "")


def set_remembered_username(username: str | None) -> None:
    with get_session() as session:
        settings_service.set_app_setting(session, _REMEMBERED_USERNAME_KEY, username or "")


_BACKUP_DIR_KEY = "backup_dir_override"


def set_backup_dir_override(path: str) -> None:
    with get_session() as session:
        settings_service.set_app_setting(session, _BACKUP_DIR_KEY, path)


def get_backup_dir_override() -> str:
    with get_session() as session:
        return settings_service.get_app_setting(session, _BACKUP_DIR_KEY, "")
