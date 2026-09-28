"""One-time migration: zero out all tax (GST / CGST / SGST / IGST).

Naya code pehle se har naya bill 0 tax par banata hai (invoice_service
tax_percentage force 0 karta hai). Ye script purane data ko fix karta hai:

- courses.gst_percentage -> 0
- invoice_items: tax_percentage / cgst / sgst / igst -> 0,
  total_amount = taxable_amount (recomputed as qty*rate - discount)
- invoices: cgst_total / sgst_total / igst_total -> 0,
  grand_total = subtotal - discount_total + round_off (recomputed),
  due_amount + status dobara calculate
- app_settings.default_tax_rate -> "0"

Usage:
    python3 tools/zero_tax_migration.py            # uses the real app database
    CODINGHUB_APP_DATA_DIR=/tmp/demo python3 tools/zero_tax_migration.py
"""
from __future__ import annotations

import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from config import config  # noqa: E402
from database.connection import get_session, init_db  # noqa: E402
from database.models.course import Course  # noqa: E402
from database.models.invoice import Invoice, InvoiceItem  # noqa: E402
from database.models.settings import AppSetting  # noqa: E402

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _q(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def main() -> None:
    init_db(config.database_url)
    with get_session() as session:
        courses = session.execute(select(Course)).scalars().all()
        n_courses = 0
        for course in courses:
            if Decimal(str(course.gst_percentage)) != 0:
                course.gst_percentage = ZERO
                n_courses += 1

        items = session.execute(select(InvoiceItem)).scalars().all()
        n_items = 0
        for item in items:
            qty = Decimal(str(item.quantity))
            rate = Decimal(str(item.rate))
            discount = Decimal(str(item.discount))
            taxable = _q(qty * rate - discount)
            if (
                Decimal(str(item.tax_percentage)) != 0
                or Decimal(str(item.cgst_amount)) != 0
                or Decimal(str(item.sgst_amount)) != 0
                or Decimal(str(item.igst_amount)) != 0
                or Decimal(str(item.total_amount)) != taxable
            ):
                item.tax_percentage = ZERO
                item.taxable_amount = taxable
                item.cgst_amount = ZERO
                item.sgst_amount = ZERO
                item.igst_amount = ZERO
                item.total_amount = taxable
                n_items += 1

        invoices = session.execute(select(Invoice)).scalars().all()
        n_invoices = 0
        for inv in invoices:
            subtotal = _q(Decimal(str(inv.subtotal)))
            discount_total = _q(Decimal(str(inv.discount_total)))
            paid = _q(Decimal(str(inv.paid_amount)))
            pre_round = subtotal - discount_total
            grand = pre_round.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            round_off = _q(grand - pre_round)
            due = _q(grand - paid)
            if due < 0:
                due = ZERO
            if (
                Decimal(str(inv.cgst_total)) != 0
                or Decimal(str(inv.sgst_total)) != 0
                or Decimal(str(inv.igst_total)) != 0
                or _q(Decimal(str(inv.grand_total))) != _q(grand)
            ):
                inv.cgst_total = ZERO
                inv.sgst_total = ZERO
                inv.igst_total = ZERO
                inv.round_off = round_off
                inv.grand_total = _q(grand)
                n_invoices += 1
            # Due + status hamesha consistent rakho (cancelled ko haath mat lagao).
            if inv.status != "CANCELLED":
                inv.due_amount = due
                if paid <= 0:
                    inv.status = "PENDING"
                elif paid >= _q(grand):
                    inv.status = "PAID"
                else:
                    inv.status = "PARTIAL"

        row = session.execute(
            select(AppSetting).where(AppSetting.key == "default_tax_rate")
        ).scalar_one_or_none()
        if row is None:
            session.add(AppSetting(key="default_tax_rate", value="0"))
        else:
            row.value = "0"

    print(f"Courses zeroed: {n_courses}")
    print(f"Invoice items zeroed: {n_items}")
    print(f"Invoices zeroed: {n_invoices}")
    print("Done — all GST/CGST/SGST/IGST are now 0.")


if __name__ == "__main__":
    main()
