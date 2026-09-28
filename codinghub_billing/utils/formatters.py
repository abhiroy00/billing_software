"""Indian currency + date formatting helpers (Section 53)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def format_indian_number(value: Decimal | float | int) -> str:
    """1000 -> '1,000', 100000 -> '1,00,000', 1234567.5 -> '12,34,567.50'."""
    value = Decimal(str(value))
    sign = "-" if value < 0 else ""
    value = abs(value)

    quantized = value.quantize(Decimal("0.01"))
    integer_part, _, decimal_part = f"{quantized:.2f}".partition(".")

    if len(integer_part) <= 3:
        grouped = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        parts = []
        while len(remaining) > 2:
            parts.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            parts.insert(0, remaining)
        grouped = ",".join(parts) + "," + last_three

    return f"{sign}{grouped}.{decimal_part}"


def format_currency(value: Decimal | float | int, symbol: str = "₹") -> str:
    return f"{symbol}{format_indian_number(value)}"


def format_date(value: date | datetime | None, date_format: str = "%d-%m-%Y") -> str:
    if value is None:
        return ""
    return value.strftime(date_format)


def parse_date(value: str, date_format: str = "%d-%m-%Y") -> date:
    return datetime.strptime(value.strip(), date_format).date()
