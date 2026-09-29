"""Business/Invoice/App settings read+write (Section 9/26). Used by the
first-run Setup Wizard, and by the full Settings module (Business, Invoice,
Backup folder, Preferences tabs).

Raw ``save_*`` helpers stay non-validating for the wizard path; the
``update_*`` wrappers validate and are what the Settings UI
(and its controller) must call.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.settings import AppSetting, BusinessSetting, InvoiceSetting
from utils import validators


class SettingsError(Exception):
    pass


# ------------------------------------------------------------------ app keys
BACKUP_DIR_KEY = "backup_dir_override"
DEFAULT_TAX_RATE_KEY = "default_tax_rate"
APPEARANCE_MODE_KEY = "appearance_mode"

APPEARANCE_MODES = ("Light", "Dark", "System")


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


# ------------------------------------------------------------------ dicts
def business_to_dict(settings: BusinessSetting) -> dict:
    return {
        "business_name": settings.business_name or "",
        "address": settings.address or "",
        "phone": settings.phone or "",
        "email": settings.email or "",
        "gstin": settings.gstin or "",
        "pan": settings.pan or "",
        "state": settings.state or "",
        "state_code": settings.state_code or "",
        "logo_path": settings.logo_path,
    }


def invoice_to_dict(settings: InvoiceSetting) -> dict:
    return {
        "prefix": settings.prefix or "",
        "starting_number": settings.starting_number,
        "next_number": settings.next_number,
        "terms": settings.terms or "",
        "footer_text": settings.footer_text or "",
        "signature_path": settings.signature_path,
    }


# ------------------------------------------------------------------ validation
def validate_business_fields(data: dict) -> list[str]:
    return validators.run_validators(
        validators.required(data.get("business_name"), "Business name"),
        validators.valid_email(data.get("email")),
        validators.valid_gstin(data.get("gstin")),
        validators.valid_pan(data.get("pan")),
    )


def validate_invoice_fields(data: dict) -> list[str]:
    errors = validators.run_validators(
        validators.required(data.get("prefix"), "Invoice prefix"),
        validators.valid_numeric(data.get("starting_number"), "Starting number"),
        validators.valid_numeric(data.get("next_number"), "Next invoice number"),
    )
    if errors:
        return errors
    try:
        starting = int(float(str(data["starting_number"])))
        nxt = int(float(str(data["next_number"])))
    except (TypeError, ValueError):
        return ["Starting number and next invoice number must be numeric."]
    extra: list[str] = []
    if starting < 1:
        extra.append("Starting number must be at least 1.")
    if nxt < 1:
        extra.append("Next invoice number must be at least 1.")
    if not extra and nxt < starting:
        extra.append("Next invoice number cannot be less than the starting number.")
    return extra


def validate_preferences_fields(data: dict) -> list[str]:
    errors = validators.run_validators(
        validators.valid_numeric(data.get("default_tax_rate"), "Default GST %"),
    )
    if errors:
        return errors
    extra: list[str] = []
    try:
        rate = float(str(data["default_tax_rate"]))
    except (TypeError, ValueError):
        return ["Default GST % must be a number."]
    # Tax fixed at 0% — koi aur rate allow nahi hai.
    if rate != 0:
        extra.append("Tax is fixed at 0%. Default GST % must be 0.")
    mode = (data.get("appearance_mode") or "").strip()
    if mode and mode not in APPEARANCE_MODES:
        extra.append(f"Appearance mode must be one of: {', '.join(APPEARANCE_MODES)}.")
    return extra


# ------------------------------------------------------------------ validated updates
_BUSINESS_FIELDS = (
    "business_name", "address", "phone", "email", "gstin", "pan",
    "state", "state_code", "logo_path",
)

_INVOICE_FIELDS = (
    "prefix", "starting_number", "next_number",
    "terms", "footer_text", "signature_path",
)


def update_business_settings(session: Session, actor_user_id: int | None, data: dict) -> dict:
    errors = validate_business_fields(data)
    if errors:
        raise SettingsError(" ".join(errors))
    cleaned = {
        "business_name": (data.get("business_name") or "").strip(),
        "address": (data.get("address") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip(),
        "gstin": (data.get("gstin") or "").strip().upper(),
        "pan": (data.get("pan") or "").strip().upper(),
        "state": (data.get("state") or "").strip(),
        "state_code": (data.get("state_code") or "").strip(),
        "logo_path": data.get("logo_path") or None,
    }
    settings = save_business_settings(session, **{k: cleaned[k] for k in _BUSINESS_FIELDS})
    return business_to_dict(settings)


def update_invoice_settings(session: Session, actor_user_id: int | None, data: dict) -> dict:
    errors = validate_invoice_fields(data)
    if errors:
        raise SettingsError(" ".join(errors))
    starting = int(float(str(data["starting_number"])))
    nxt = int(float(str(data["next_number"])))
    settings = save_invoice_settings(
        session,
        prefix=(data.get("prefix") or "").strip().upper(),
        starting_number=starting,
        next_number=nxt,
        terms=data.get("terms") or "",
        footer_text=(data.get("footer_text") or "").strip(),
        signature_path=data.get("signature_path") or None,
    )
    return invoice_to_dict(settings)


def get_preferences(session: Session, default_tax_rate: int = 0) -> dict:
    return {
        "default_tax_rate": get_app_setting(session, DEFAULT_TAX_RATE_KEY, str(default_tax_rate)),
        "appearance_mode": get_app_setting(session, APPEARANCE_MODE_KEY, "Light"),
        "backup_dir": get_app_setting(session, BACKUP_DIR_KEY, ""),
    }


def update_preferences(session: Session, actor_user_id: int | None, data: dict) -> dict:
    errors = validate_preferences_fields(data)
    if errors:
        raise SettingsError(" ".join(errors))
    rate = "0"
    mode = (data.get("appearance_mode") or "Light").strip() or "Light"
    set_app_setting(session, DEFAULT_TAX_RATE_KEY, rate)
    set_app_setting(session, APPEARANCE_MODE_KEY, mode)
    return get_preferences(session)
