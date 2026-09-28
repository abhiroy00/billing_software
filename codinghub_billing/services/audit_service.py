"""Generic audit logging (Section 24). Any service that creates/edits/
deletes a record, or handles login/settings/backup, should call `log()`."""
from __future__ import annotations

from sqlalchemy.orm import Session

from database.models.audit_log import AuditLog


def log(
    session: Session,
    user_id: int | None,
    action: str,
    entity_type: str = "",
    entity_id: object = "",
    description: str = "",
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id != "" else "",
        description=description,
    )
    session.add(entry)
    session.flush()
    return entry
