"""BusinessSetting / InvoiceSetting singleton-row models (Section 26)."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class BusinessSetting(Base, TimestampMixin):
    __tablename__ = "business_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    pan: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    state_code: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class InvoiceSetting(Base, TimestampMixin):
    __tablename__ = "invoice_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="CH")
    starting_number: Mapped[int] = mapped_column(default=1, nullable=False)
    next_number: Mapped[int] = mapped_column(default=1, nullable=False)
    terms: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    footer_text: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AppSetting(Base, TimestampMixin):
    """Generic key/value store for misc settings (backup dir, appearance, ...)."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
