"""Business/Invoice/App settings read+write (Section 9/26). Used by the
first-run Setup Wizard now, and by the full Settings module in a later phase."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.settings import AppSetting, BusinessSetting, InvoiceSetting


def get_business_settings(session: Session) -> BusinessSetting:
    settings = session.execute(select(BusinessSetting)).scalars().first()
    if settings is None:
        settings = BusinessSetting()
        session.add(settings)
        session.flush()
    return settings


def save_business_settings(session: Session, **fields) -> BusinessSetting:
    settings = get_business_settings(session)
    for key, value in fields.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    session.flush()
    return settings


def get_invoice_settings(session: Session) -> InvoiceSetting:
    settings = session.execute(select(InvoiceSetting)).scalars().first()
    if settings is None:
        settings = InvoiceSetting()
        session.add(settings)
        session.flush()
    return settings


def save_invoice_settings(session: Session, **fields) -> InvoiceSetting:
    settings = get_invoice_settings(session)
    for key, value in fields.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    session.flush()
    return settings


def get_app_setting(session: Session, key: str, default: str = "") -> str:
    row = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
    return row.value if row is not None else default


def set_app_setting(session: Session, key: str, value: str) -> AppSetting:
    row = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
    if row is None:
        row = AppSetting(key=key, value=value)
        session.add(row)
    else:
        row.value = value
    session.flush()
    return row
