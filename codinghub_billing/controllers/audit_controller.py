"""GUI-facing layer over audit_service (Section 24). The audit table is
append-only — this controller only reads and exports, following the same
filter -> summary -> table -> export layout as Reports."""
from __future__ import annotations

import logging
from datetime import date

from database.connection import get_session
from services import audit_service
from utils.export_utils import write_csv_rows, write_excel_rows
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

FILTER_ALL = "All"


def list_logs(
    query: str = "",
    action: str | None = None,
    entity_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    with get_session() as session:
        return audit_service.list_logs(
            session,
            query=query,
            action=None if action in (None, FILTER_ALL) else action,
            entity_type=None if entity_type in (None, FILTER_ALL) else entity_type,
            date_from=date_from,
            date_to=date_to,
        )


def filter_options() -> dict:
    """Distinct actions/entity types actually present in the table."""
    with get_session() as session:
        return {
            "actions": audit_service.distinct_actions(session),
            "entity_types": audit_service.distinct_entity_types(session),
        }


def export_logs_to_file(path: str, fmt: str, rows: list[dict]) -> tuple[bool, str]:
    headers = ["When", "User", "Action", "Entity", "Entity ID", "Description"]
    data = [
        [
            r["timestamp"].strftime("%d-%m-%Y %H:%M") if r.get("timestamp") else "",
            r.get("username", ""),
            r.get("action", ""),
            r.get("entity_type", ""),
            r.get("entity_id", ""),
            r.get("description", ""),
        ]
        for r in rows
    ]
    try:
        if fmt == "csv":
            write_csv_rows(path, headers, data)
        else:
            write_excel_rows(path, "Audit Log", headers, data)
        return True, ""
    except Exception:
        logger.exception("Failed to export audit log")
        return False, USER_FRIENDLY_MESSAGE
