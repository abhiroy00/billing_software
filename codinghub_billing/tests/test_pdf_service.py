from datetime import date
from decimal import Decimal

from services import pdf_service


def _detail():
    return {
        "invoice": {
            "id": 1, "invoice_number": "CH-2026-000001", "invoice_date": date(2026, 9, 26),
            "customer_id": 1, "customer_name": "Ramakant", "customer_mobile": "9876543210",
            "billing_address": "", "customer_gstin": "", "subtotal": Decimal("25000.00"),
            "discount_total": Decimal("0.00"), "cgst_total": Decimal("0.00"),
            "sgst_total": Decimal("0.00"), "igst_total": Decimal("0.00"),
            "round_off": Decimal("0.00"), "grand_total": Decimal("25000.00"),
            "paid_amount": Decimal("25000.00"), "due_amount": Decimal("0.00"),
            "notes": "", "status": "PAID",
        },
        "items": [
            {"id": 1, "item_name": "Internship (Project Cost)", "quantity": Decimal("1"),
             "rate": Decimal("25000.00"), "discount": Decimal("0.00"),
             "tax_percentage": Decimal("0"), "taxable_amount": Decimal("25000.00"),
             "cgst_amount": Decimal("0.00"), "sgst_amount": Decimal("0.00"),
             "igst_amount": Decimal("0.00"), "total_amount": Decimal("25000.00")},
        ],
        "payments": [
            {"id": 7, "amount": Decimal("25000.00"), "payment_mode": "Cash",
             "payment_date": date(2026, 9, 26), "reference_number": ""},
        ],
    }


def _business():
    return {
        "business_name": "Innovative AI Solution", "address": "2nd Floor, Kapil Vihar, Pitampura, New Delhi",
        "phone": "+91 7464099059", "email": "info@innovativeais.com", "gstin": "",
        "pan": "", "state": "Delhi", "logo_path": None,
    }


def _settings():
    return {"prefix": "IAS", "terms": "Payment due on receipt.",
            "footer_text": "Thank you for your business.", "signature_path": None}


def test_amount_in_words_sample_receipt():
    assert pdf_service.amount_in_words_inr(Decimal("25000")) == "Rupees Twenty Five Thousand Only"


def test_amount_in_words_zero_and_paise():
    assert pdf_service.amount_in_words_inr(0) == "Rupees Zero Only"
    assert pdf_service.amount_in_words_inr(Decimal("1500.50")) == "Rupees One Thousand Five Hundred and Paise Fifty Only"


def test_amount_in_words_indian_system():
    assert "Crore" in pdf_service.amount_in_words_inr(12_000_000)
    assert "Lakh" in pdf_service.amount_in_words_inr(250_000)


def test_format_inr_grouping():
    assert pdf_service.format_inr(Decimal("25000")) == "25,000.00"
    assert pdf_service.format_inr(Decimal("100000")) == "1,00,000.00"
    assert pdf_service.format_inr(Decimal("10000000")) == "1,00,00,000.00"


def test_receipt_number_format():
    assert pdf_service.receipt_number("IAS", date(2026, 9, 26), 1) == "IAS/RCPT-2026-0001"


def test_build_receipt_pdf_bytes():
    detail = _detail()
    pdf = pdf_service.build_receipt_pdf(detail, detail["payments"][0], _business(), _settings())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 3000


def test_build_invoice_pdf_bytes():
    pdf = pdf_service.build_invoice_pdf(_detail(), _business(), _settings())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 3000


def test_project_summary():
    assert pdf_service.project_summary([]) == "—"
    assert pdf_service.project_summary([{"item_name": "A"}, {"item_name": "B"}]) == "A, B"
    assert "+1 more" in pdf_service.project_summary([{"item_name": "A"}, {"item_name": "B"}, {"item_name": "C"}])
