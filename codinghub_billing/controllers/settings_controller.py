"""GUI-facing layer over settings_service (Section 26). Views call these
functions and get back plain dicts / (success, message) tuples — never a
raw DB session or ORM instance. Every mutating action re-checks the
"settings" permission here too — the nav item being hidden is not the
only line of defense."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from config import config
from database.connection import get_session
from services import auth_service, settings_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

PERMISSION_DENIED = "You do not have permission to manage settings."


def _require_settings_permission() -> str | None:
    if not auth_service.current_session.has_permission("settings"):
        return PERMISSION_DENIED
    return None


def _actor() -> int | None:
    return auth_service.current_session.user_id


# ------------------------------------------------------------------ business
def get_business() -> dict:
    with get_session() as session:
        return settings_service.business_to_dict(
            settings_service.get_business_settings(session)
        )


def save_business(data: dict) -> tuple[bool, str, dict | None]:
    denied = _require_settings_permission()
    if denied:
        return False, denied, None
    try:
        with get_session() as session:
            saved = settings_service.update_business_settings(session, _actor(), data)
        return True, "", saved
    except settings_service.SettingsError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to save business settings")
        return False, USER_FRIENDLY_MESSAGE, None


# ------------------------------------------------------------------ invoice
def get_invoice() -> dict:
    with get_session() as session:
        return settings_service.invoice_to_dict(
            settings_service.get_invoice_settings(session)
        )


def save_invoice(data: dict) -> tuple[bool, str, dict | None]:
    denied = _require_settings_permission()
    if denied:
        return False, denied, None
    try:
        with get_session() as session:
            saved = settings_service.update_invoice_settings(session, _actor(), data)
        return True, "", saved
    except settings_service.SettingsError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to save invoice settings")
        return False, USER_FRIENDLY_MESSAGE, None


def preview_next_invoice_number(prefix: str, next_number: int, year: int | None = None) -> str:
    """Next invoice number jaisa save ke baad dikhega — bina save kiye."""
    from datetime import date

    year = year or date.today().year
    try:
        nxt = int(next_number)
    except (TypeError, ValueError):
        nxt = 1
    return f"{(prefix or '').strip().upper() or 'CH'}-{year}-{max(nxt, 1):06d}"


# ------------------------------------------------------------------ backup folder
def get_backup_dir() -> str:
    with get_session() as session:
        override = settings_service.get_app_setting(
            session, settings_service.BACKUP_DIR_KEY, ""
        )
    return override or str(config.backup_dir)


def set_backup_dir(path: str) -> tuple[bool, str, str | None]:
    denied = _require_settings_permission()
    if denied:
        return False, denied, None
    candidate = (path or "").strip()
    if not candidate:
        return False, "Backup folder path is required.", None
    try:
        Path(candidate).mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Invalid backup folder")
        return False, "That folder could not be created. Pick another location.", None
    try:
        with get_session() as session:
            settings_service.set_app_setting(
                session, settings_service.BACKUP_DIR_KEY, candidate
            )
        return True, "", candidate
    except Exception:
        logger.exception("Failed to save backup folder")
        return False, USER_FRIENDLY_MESSAGE, None


def open_backup_folder() -> tuple[bool, str]:
    folder = get_backup_dir()
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
        return True, ""
    except Exception:
        logger.exception("Failed to open backup folder")
        return False, USER_FRIENDLY_MESSAGE


# ------------------------------------------------------------------ preferences
def get_preferences() -> dict:
    with get_session() as session:
        return settings_service.get_preferences(
            session, default_tax_rate=config.DEFAULT_TAX_RATE
        )


def save_preferences(data: dict) -> tuple[bool, str, dict | None]:
    denied = _require_settings_permission()
    if denied:
        return False, denied, None
    try:
        with get_session() as session:
            saved = settings_service.update_preferences(session, _actor(), data)
        try:
            import customtkinter as ctk

            ctk.set_appearance_mode(saved.get("appearance_mode") or "Light")
        except Exception:
            pass
        return True, "", saved
    except settings_service.SettingsError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to save preferences")
        return False, USER_FRIENDLY_MESSAGE, None


def get_default_tax_rate() -> int:
    """Course form jaisa har jagah default GST % — settings me badla ja sakta hai."""
    try:
        prefs = get_preferences()
        return int(float(str(prefs.get("default_tax_rate") or config.DEFAULT_TAX_RATE)))
    except (TypeError, ValueError):
        return config.DEFAULT_TAX_RATE
