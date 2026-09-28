"""GST calculation logic (Section 14/40). Pure, side-effect-free functions —
kept separate from invoice_service so financial math can be unit tested in
isolation from the database.

Rule: same state (business vs customer) -> CGST + SGST split; different
state -> IGST. All money math uses Decimal, never float.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
WHOLE_RUPEE = Decimal("1")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def determine_tax_type(business_state: str, customer_state: str) -> str:
    """'intra' (CGST+SGST) if states match (case-insensitive), else 'inter' (IGST)."""
    business_state = (business_state or "").strip().lower()
    customer_state = (customer_state or "").strip().lower()
    if not business_state or not customer_state:
        return "intra"
    return "intra" if business_state == customer_state else "inter"


@dataclass
class LineItemCalculation:
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal


def calculate_line_item(
    rate: Decimal, quantity: Decimal, discount: Decimal, tax_percentage: Decimal, tax_type: str
) -> LineItemCalculation:
    gross = rate * quantity
    taxable_amount = gross - discount
    if taxable_amount < 0:
        raise ValueError("Discount cannot be greater than the item amount.")

    if tax_type == "intra":
        half_rate = tax_percentage / 2
        cgst = _q(taxable_amount * half_rate / 100)
        sgst = _q(taxable_amount * half_rate / 100)
        igst = Decimal("0.00")
    else:
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = _q(taxable_amount * tax_percentage / 100)

    taxable_amount = _q(taxable_amount)
    total_amount = _q(taxable_amount + cgst + sgst + igst)

    return LineItemCalculation(
        taxable_amount=taxable_amount, cgst_amount=cgst, sgst_amount=sgst, igst_amount=igst, total_amount=total_amount
    )


@dataclass
class InvoiceTotals:
    subtotal: Decimal
    discount_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    round_off: Decimal
    grand_total: Decimal


def calculate_invoice_totals(line_items: list[dict]) -> InvoiceTotals:
    """line_items: list of dicts with rate, quantity, discount (gross values)
    and cgst_amount/sgst_amount/igst_amount/taxable_amount (already computed
    per line via calculate_line_item)."""
    subtotal = sum((Decimal(str(i["rate"])) * Decimal(str(i["quantity"])) for i in line_items), Decimal("0"))
    discount_total = sum((Decimal(str(i["discount"])) for i in line_items), Decimal("0"))
    cgst_total = sum((Decimal(str(i["cgst_amount"])) for i in line_items), Decimal("0"))
    sgst_total = sum((Decimal(str(i["sgst_amount"])) for i in line_items), Decimal("0"))
    igst_total = sum((Decimal(str(i["igst_amount"])) for i in line_items), Decimal("0"))

    pre_round_total = subtotal - discount_total + cgst_total + sgst_total + igst_total
    grand_total = pre_round_total.quantize(WHOLE_RUPEE, rounding=ROUND_HALF_UP)
    round_off = _q(grand_total - pre_round_total)

    return InvoiceTotals(
        subtotal=_q(subtotal),
        discount_total=_q(discount_total),
        cgst_total=_q(cgst_total),
        sgst_total=_q(sgst_total),
        igst_total=_q(igst_total),
        round_off=round_off,
        grand_total=_q(grand_total),
    )
