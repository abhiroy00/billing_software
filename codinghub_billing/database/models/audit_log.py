"""Audit log model (Section 24). Immutable — no update timestamp."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
