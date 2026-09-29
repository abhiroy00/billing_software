"""Print-ready PDF documents (Section 21): GST Tax Invoice + Payment Receipt.

Pure functions — dicts in, PDF bytes out — so they are unit-testable
without a database or a display. The controller layer fetches the dicts.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1F2A44")
ORANGE = colors.HexColor("#E8913A")
GREY_LABEL = colors.HexColor("#F1F5F9")
GREY_BORDER = colors.HexColor("#D7DEE8")
TEXT = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three_digits(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} Hundred")
        n %= 100
    if n:
        parts.append(_two_digits(n))
    return " ".join(parts)


def number_to_words_in(n: int) -> str:
    """Indian-system words: Crore, Lakh, Thousand, Hundred."""
    if n == 0:
        return "Zero"
    parts: list[str] = []
    for value, name in ((10_000_000, "Crore"), (100_000, "Lakh"), (1_000, "Thousand")):
        if n >= value:
            parts.append(f"{_three_digits(n // value)} {name}")
            n %= value
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


def amount_in_words_inr(amount: Decimal | float | int) -> str:
    """'Rupees Twenty Five Thousand Only.' — paise appended when present."""
    total = Decimal(str(amount)).quantize(Decimal("0.01"))
    rupees = int(total)
    paise = int((total - rupees) * 100)
    words = f"Rupees {number_to_words_in(rupees)} Only"
    if paise:
        words = f"Rupees {number_to_words_in(rupees)} and Paise {number_to_words_in(paise)} Only"
    return words


def format_inr(amount: Decimal | float | int) -> str:
    """Indian digit grouping: 25000 -> '25,000.00'."""
    total = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
    sign = "-" if total < 0 else ""
    whole, _, frac = f"{abs(total):.2f}".partition(".")
    if len(whole) > 3:
        tail = whole[-3:]
        head = whole[:-3]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}{whole}.{frac}"

def format_long_date(value: date | str) -> str:
    if isinstance(value, str):
        return value
    try:
        return value.strftime("%d %B %Y")
    except Exception:
        return str(value)


def format_qty(value) -> str:
    try:
        quantized = Decimal(str(value or 0)).normalize()
        return format(quantized, "f")
    except Exception:
        return str(value)


# ------------------------------------------------------------------- styles
def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9, leading=12, textColor=TEXT)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=10, textColor=MUTED),
        "bold": ParagraphStyle("bold", parent=base, fontName="Helvetica-Bold"),
        "business": ParagraphStyle("business", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY),
        "tagline": ParagraphStyle("tagline", parent=base, fontSize=8, leading=10, textColor=MUTED),
        "band": ParagraphStyle(
            "band", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=16,
            textColor=colors.white, alignment=1,
        ),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9, leading=11),
        "cell_bold": ParagraphStyle("cell_bold", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=11),
        "cell_right": ParagraphStyle("cell_right", parent=base, fontSize=9, leading=11, alignment=2),
        "cell_right_bold": ParagraphStyle(
            "cell_right_bold", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=2,
        ),
        "label": ParagraphStyle("label", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=11),
        "footer": ParagraphStyle("footer", parent=base, fontSize=8, leading=11, textColor=MUTED),
        "sign": ParagraphStyle("sign", parent=base, fontSize=9, leading=11, alignment=2),
    }


def _header_table(business: dict, right_lines: list[str], st: dict) -> Table:
    """Logo | business name || right-aligned contact block (like the sample)."""
    logo_path = business.get("logo_path") or ""
    if logo_path and Path(logo_path).is_file():
        try:
            logo = Image(logo_path, width=22 * mm, height=22 * mm)
            logo.hAlign = "LEFT"
        except Exception:
            logo = Paragraph("", st["base"])
    else:
        logo = Paragraph("", st["base"])

    name_para = Paragraph(business.get("business_name") or "Business", st["business"])
    tagline = Paragraph("Smart Solutions for a Smarter Future", st["tagline"])
    left = [[logo, [name_para, tagline]]]

    right_paras = [Paragraph(line, st["small"]) for line in right_lines]
    table = Table([[left, right_paras]], colWidths=[95 * mm, 85 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return table


def _contact_lines(business: dict) -> list[str]:
    lines = []
    address_bits = [business.get("address") or "", business.get("state") or ""]
    address = ", ".join(b for b in address_bits if b).strip()
    if address:
        lines.append(f"<b>Office Address:</b> {address}")
    if business.get("email"):
        lines.append(f"<b>Email:</b> {business['email']}")
    if business.get("phone"):
        lines.append(f"<b>Tel:</b> {business['phone']}")
    if business.get("gstin"):
        lines.append(f"<b>GSTIN:</b> {business['gstin']}")
    return lines or ["<b>Office Address:</b> —"]


def _band(title: str, st: dict, color=ORANGE) -> Table:
    table = Table([[Paragraph(title, st["band"])]], colWidths=[180 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _info_table(pairs: list[tuple[str, str, str, str]], st: dict) -> Table:
    """Two label/value pairs per row, grey label cells (like the sample)."""
    rows = []
    for left_label, left_value, right_label, right_value in pairs:
        rows.append([
            Paragraph(f"<b>{left_label}</b>", st["label"]), Paragraph(left_value or "—", st["cell"]),
            Paragraph(f"<b>{right_label}</b>", st["label"]), Paragraph(right_value or "—", st["cell"]),
        ])
    table = Table(rows, colWidths=[32 * mm, 58 * mm, 32 * mm, 58 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), GREY_LABEL),
        ("BACKGROUND", (2, 0), (2, -1), GREY_LABEL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _items_table(header: list[str], rows: list[list[str]], st: dict,
                 col_widths: list, header_color=NAVY, amount_col: int = -1) -> Table:
    head_style = ParagraphStyle("head", parent=st["base"], fontName="Helvetica-Bold",
                                fontSize=9, leading=11, textColor=colors.white)
    data = [[Paragraph(f"<b>{h}</b>", head_style) for h in header]]
    for row in rows:
        data.append([
            Paragraph(cell, st["cell_right"] if i == len(row) + amount_col else st["cell"])
            for i, cell in enumerate(row)
        ])
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]
    table.setStyle(TableStyle(style))
    return table


def _totals_rows(pairs: list[tuple[str, Decimal | str, bool]], st: dict) -> list[list]:
    rows = []
    for label, value, bold in pairs:
        text = value if isinstance(value, str) else f"Rs. {format_inr(value)}"
        label_style = st["cell_right_bold"] if bold else st["cell_right"]
        value_style = st["cell_right_bold"] if bold else st["cell_right"]
        label_para = Paragraph(f"<b>{label}</b>" if bold and label else label, label_style) if label else Paragraph("", label_style)
        rows.append([Paragraph("", st["cell"]), label_para, Paragraph(text, value_style)])
    return rows


def _totals_table(pairs: list[tuple[str, Decimal | str, bool]], st: dict) -> Table:
    table = Table(_totals_rows(pairs, st), colWidths=[86 * mm, 50 * mm, 44 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _signature_block(business: dict, invoice_settings: dict, st: dict):
    name = business.get("business_name") or "Business"
    sig_path = invoice_settings.get("signature_path") or ""
    if sig_path and Path(sig_path).is_file():
        try:
            sig = Image(sig_path, width=35 * mm, height=15 * mm)
            sig.hAlign = "RIGHT"
        except Exception:
            sig = Paragraph("", st["sign"])
    else:
        sig = Paragraph("", st["sign"])
    return [
        Paragraph(f"For {name}", st["sign"]),
        Spacer(1, 12 * mm),
        sig,
        Paragraph("Authorized Signatory", st["sign"]),
    ]


def _build(business: dict, story: list) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title="Document", author=business.get("business_name") or "",
    )
    doc.build(story)
    return buffer.getvalue()


# ------------------------------------------------------------------ receipt
def receipt_number(prefix: str, payment_date: date, payment_id: int) -> str:
    year = payment_date.year if isinstance(payment_date, date) else date.today().year
    return f"{prefix or 'CH'}/RCPT-{year}-{payment_id:04d}"


def project_summary(items: list[dict]) -> str:
    if not items:
        return "—"
    names = [i.get("item_name", "") for i in items if i.get("item_name")]
    if len(names) <= 2:
        return ", ".join(names)
    return f"{names[0]}, {names[1]} (+{len(names) - 2} more)"


def build_receipt_pdf(detail: dict, payment: dict, business: dict, invoice_settings: dict) -> bytes:
    """Payment receipt exactly like the reference sample."""
    st = _styles()
    inv = detail["invoice"]
    items = detail["items"]

    story: list = [
        _header_table(business, _contact_lines(business), st),
        Spacer(1, 3 * mm),
        Table([[""]], colWidths=[180 * mm], style=TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1.2, NAVY)])),
        Spacer(1, 4 * mm),
        _band("PAYMENT RECEIPT", st, ORANGE),
        Spacer(1, 4 * mm),
        _info_table([
            ("Receipt No.", receipt_number(invoice_settings.get("prefix"), payment["payment_date"], payment["id"]),
             "Date", format_long_date(payment["payment_date"])),
            ("Received From", inv.get("customer_name", ""), "Payment Mode", payment.get("payment_mode", "")),
            ("Project", project_summary(items), "Payment Status", "Paid"),
        ], st),
        Spacer(1, 5 * mm),
        Paragraph("<b>Cost Breakdown</b>", st["bold"]),
        Spacer(1, 2 * mm),
    ]

    item_rows = [
        [str(i + 1), it.get("item_name", ""), format_qty(it.get("quantity", "")),
         "Rs. " + format_inr(it.get("total_amount", 0))]
        for i, it in enumerate(items)
    ]
    story.append(_items_table(
        ["S.No", "Description", "Qty / Basis", "Amount (Rs.)"], item_rows, st,
        col_widths=[14 * mm, 92 * mm, 30 * mm, 44 * mm],
    ))

    totals = _totals_table([
        ("", f"Rs. {format_inr(inv.get('grand_total', 0))}", True),
        ("", f"Rs. {format_inr(inv.get('paid_amount', 0))}", True),
        ("", f"Rs. {format_inr(inv.get('due_amount', 0))}", True),
    ], st)
    story.append(totals)
    story.append(Spacer(1, 6 * mm))
    footer = (invoice_settings.get("footer_text")
              or "This is a system-generated receipt confirming the payment received against the above project. Thank you for your business.")
    story.append(Paragraph(footer, st["footer"]))
    story.append(Spacer(1, 10 * mm))
    story.extend(_signature_block(business, invoice_settings, st))
    return _build(business, story)


# ------------------------------------------------------------------ invoice
def build_invoice_pdf(detail: dict, business: dict, invoice_settings: dict) -> bytes:
    """GST tax invoice with the same branded header."""
    st = _styles()
    inv = detail["invoice"]
    items = detail["items"]

    story: list = [
        _header_table(business, _contact_lines(business), st),
        Spacer(1, 3 * mm),
        Table([[""]], colWidths=[180 * mm], style=TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1.2, NAVY)])),
        Spacer(1, 4 * mm),
        _band("TAX INVOICE", st, NAVY),
        Spacer(1, 4 * mm),
        _info_table([
            ("Invoice No.", inv.get("invoice_number", ""), "Date", format_long_date(inv.get("invoice_date"))),
            ("Billed To", inv.get("customer_name", ""), "Mobile", inv.get("customer_mobile", "")),
            ("GSTIN", inv.get("customer_gstin") or "—", "Status", inv.get("status", "")),
        ], st),
        Spacer(1, 5 * mm),
        Paragraph("<b>Items</b>", st["bold"]),
        Spacer(1, 2 * mm),
    ]

    item_rows = [
        [str(i + 1), it.get("item_name", ""), format_qty(it.get("quantity", "")),
         "Rs. " + format_inr(it.get("rate", 0)),
         "Rs. " + format_inr(it.get("discount", 0)),
         f"{it.get('tax_percentage', 0)}%",
         "Rs. " + format_inr(it.get("total_amount", 0))]
        for i, it in enumerate(items)
    ]
    story.append(_items_table(
        ["S.No", "Description", "Qty", "Rate", "Discount", "Tax", "Amount"], item_rows, st,
        col_widths=[12 * mm, 62 * mm, 14 * mm, 26 * mm, 26 * mm, 16 * mm, 24 * mm],
    ))

    totals = _totals_table([
        ("Subtotal", inv.get("subtotal", 0), False),
        ("Discount", inv.get("discount_total", 0), False),
        ("CGST", inv.get("cgst_total", 0), False),
        ("SGST", inv.get("sgst_total", 0), False),
        ("IGST", inv.get("igst_total", 0), False),
        ("Round Off", inv.get("round_off", 0), False),
        ("Grand Total", inv.get("grand_total", 0), True),
        ("Paid", inv.get("paid_amount", 0), False),
        ("Balance Due", inv.get("due_amount", 0), True),
    ], st)
    story.append(totals)
    story.append(Spacer(1, 4 * mm))
    terms = invoice_settings.get("terms") or ""
    if terms:
        story.append(Paragraph("<b>Terms & Conditions:</b>", st["bold"]))
        story.append(Paragraph(terms, st["footer"]))
        story.append(Spacer(1, 3 * mm))
    notes = inv.get("notes") or ""
    if notes:
        story.append(Paragraph(f"<b>Notes:</b> {notes}", st["footer"]))
        story.append(Spacer(1, 3 * mm))
    footer = invoice_settings.get("footer_text") or "This is a system-generated invoice. Thank you for your business."
    story.append(Paragraph(footer, st["footer"]))
    story.append(Spacer(1, 10 * mm))
    story.extend(_signature_block(business, invoice_settings, st))
    return _build(business, story)
