"""GUI-facing layer over backup_service (Section 27). Views call these
functions and get back plain dicts / (success, message) tuples — never a
raw DB session. Every mutating action re-checks the "backup" permission
here too — the nav item being hidden is not the only line of defense."""
from __future__ import annotations

import logging

from config import config
from controllers import settings_controller
from database.connection import get_engine, get_session
from services import auth_service, backup_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

PERMISSION_DENIED = "You do not have permission to manage backups."


def _require_backup_permission() -> str | None:
    if not auth_service.current_session.has_permission("backup"):
        return PERMISSION_DENIED
    return None


def get_backup_dir() -> str:
    return settings_controller.get_backup_dir()


def list_backups() -> list[dict]:
    return backup_service.list_backups(get_backup_dir())


def create_backup() -> tuple[bool, str, dict | None]:
    denied = _require_backup_permission()
    if denied:
        return False, denied, None
    try:
        info = backup_service.create_backup(config.database_path, get_backup_dir())
        return True, "", info
    except backup_service.BackupError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Backup failed")
        return False, USER_FRIENDLY_MESSAGE, None


def delete_backup(path: str) -> tuple[bool, str]:
    denied = _require_backup_permission()
    if denied:
        return False, denied
    try:
        name = path.split("/")[-1].split("\\")[-1]
        backup_service.delete_backup(path, get_backup_dir())
        return True, ""
    except backup_service.BackupError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Backup delete failed")
        return False, USER_FRIENDLY_MESSAGE


def restore_backup(path: str) -> tuple[bool, str]:
    """Backup file se live DB replace + engine dispose + verify.

    Success pe app restart zaroori hai — GUI ye message clearly dikhaye.
    """
    denied = _require_backup_permission()
    if denied:
        return False, denied
    try:
        result = backup_service.restore_backup(path, config.database_path, get_backup_dir())
    except backup_service.BackupError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Restore copy failed")
        return False, USER_FRIENDLY_MESSAGE

    # Pooled connections purani file pe latke na rahen — engine dispose.
    try:
        get_engine().dispose()
    except Exception:
        logger.exception("Engine dispose failed after restore")

    try:
        backup_service.verify_database_tables(config.database_path)
    except backup_service.BackupError as exc:
        return False, str(exc)

    safety = (result.get("safety_copy") or {}).get("name", "")
    restart_note = "Restore ho gaya. App ko restart karo taaki saara data fresh load ho."
    if safety:
        restart_note += f" Safety copy bani hai: {safety}."
    return True, restart_note
