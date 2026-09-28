"""Generic audit logging + activity querying (Section 24). Any service
that creates/edits/deletes a record, or handles login/settings/backup,
should call `log()`. The Audit Log screen reads through `list_logs()` —
never update/delete rows from here (the table is append-only)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database.models.audit_log import AuditLog
from database.models.user import User

DEFAULT_LIST_LIMIT = 500


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


def _to_dict(log: AuditLog, username: str | None) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": username or "—",
        "action": log.action,
        "entity_type": log.entity_type or "—",
        "entity_id": log.entity_id or "",
        "description": log.description or "",
        "timestamp": log.timestamp,
    }


def list_logs(
    session: Session,
    query: str = "",
    action: str | None = None,
    entity_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = DEFAULT_LIST_LIMIT,
) -> list[dict]:
    """Newest-first activity rows with the acting username joined in."""
    stmt = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.id.desc())
    )
    if query and query.strip():
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                AuditLog.description.ilike(like),
                AuditLog.action.ilike(like),
                AuditLog.entity_type.ilike(like),
                AuditLog.entity_id.ilike(like),
                User.username.ilike(like),
            )
        )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if date_from:
        stmt = stmt.where(AuditLog.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(AuditLog.timestamp < datetime.combine(date_to, time.min) + timedelta(days=1))
    if limit and limit > 0:
        stmt = stmt.limit(limit)
    return [_to_dict(log, username) for log, username in session.execute(stmt).all()]


def distinct_values(session: Session, column) -> list[str]:
    rows = session.execute(
        select(column).where(column != "").distinct().order_by(column)
    ).scalars().all()
    return [r for r in rows if r]


def distinct_actions(session: Session) -> list[str]:
    return distinct_values(session, AuditLog.action)


def distinct_entity_types(session: Session) -> list[str]:
    return distinct_values(session, AuditLog.entity_type)


def count_since(session: Session, since: datetime) -> int:
    from sqlalchemy import func

    return (
        session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= since)
        ).scalar_one()
    )
