"""Reusable field validators (Section 22). Each returns an error message
string, or ``None`` when the value is valid, so forms can show the message
right next to the offending field."""
from __future__ import annotations

import re
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z]{1}[A-Z\d]{1}$")
PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]{1}$")


def required(value: str | None, field_label: str = "This field") -> str | None:
    if value is None or str(value).strip() == "":
        return f"{field_label} is required."
    return None


def valid_email(value: str | None, field_label: str = "Email") -> str | None:
    if not value:
        return None
    if not EMAIL_RE.match(value.strip()):
        return f"{field_label} is not a valid email address."
    return None


def valid_mobile(value: str | None, field_label: str = "Mobile number") -> str | None:
    if not value:
        return None
    if not MOBILE_RE.match(value.strip()):
        return f"{field_label} must be a valid 10-digit Indian mobile number."
    return None


def valid_gstin(value: str | None, field_label: str = "GSTIN") -> str | None:
    if not value:
        return None
    if not GSTIN_RE.match(value.strip().upper()):
        return f"{field_label} is not a valid GSTIN."
    return None


def valid_pan(value: str | None, field_label: str = "PAN") -> str | None:
    if not value:
        return None
    if not PAN_RE.match(value.strip().upper()):
        return f"{field_label} is not a valid PAN."
    return None


def valid_numeric(value: str | None, field_label: str = "Value", allow_negative: bool = False) -> str | None:
    if value is None or str(value).strip() == "":
        return f"{field_label} is required."
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{field_label} must be a number."
    if not allow_negative and number < 0:
        return f"{field_label} cannot be negative."
    return None


def valid_date(value: str | None, date_format: str = "%d-%m-%Y", field_label: str = "Date") -> str | None:
    if not value:
        return None
    try:
        datetime.strptime(value.strip(), date_format)
    except ValueError:
        return f"{field_label} must be a valid date in {date_format} format."
    return None


def valid_discount(discount: float, base_amount: float, field_label: str = "Discount") -> str | None:
    if discount < 0:
        return f"{field_label} cannot be negative."
    if discount > base_amount:
        return f"{field_label} cannot be greater than the amount it applies to."
    return None


def run_validators(*errors: str | None) -> list[str]:
    return [e for e in errors if e]
