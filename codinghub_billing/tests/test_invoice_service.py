from datetime import date
from decimal import Decimal

import pytest

from services import course_service, customer_service, invoice_service, payment_service, settings_service


def _seed_business(session, state="Karnataka"):
    settings_service.save_business_settings(session, business_name="CodingHub", state=state)


def _seed_customer(session, name="Ravi Kumar", state="Karnataka", **overrides):
    data = {
        "name": name, "mobile": "9876543210", "email": "", "gender": "", "student_id": "",
        "address": "", "city": "", "state": state, "pincode": "", "gstin": "", "pan": "",
        "course_id": None, "date_of_birth": None, "enrollment_date": None, "status": "Active", "notes": "",
    }
    data.update(overrides)
    return customer_service.create_customer(session, None, data)


def _seed_course(session, name="Python Bootcamp", price="10000", gst="0", discount="0"):
    return course_service.create_course(
        session, None,
        {"name": name, "category": "Programming", "description": "", "price": price,
         "gst_percentage": gst, "discount": discount, "duration": "3 months", "status": "Active"},
    )


def test_peek_and_generate_invoice_number_increment(db_session):
    settings_service.save_invoice_settings(db_session, prefix="CH", starting_number=1, next_number=1)

    first_peek = invoice_service.peek_next_invoice_number(db_session, date(2026, 1, 1))
    assert first_peek == "CH-2026-000001"

    _seed_business(db_session)
    customer = _seed_customer(db_session)
    invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "10000", "discount": "1000", "tax_percentage": "0"}],
        invoice_date=date(2026, 1, 1),
    )

    second_peek = invoice_service.peek_next_invoice_number(db_session, date(2026, 1, 1))
    assert second_peek == "CH-2026-000002"


def test_create_invoice_matches_section_40_example(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)

    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "10000", "discount": "1000", "tax_percentage": "0"}],
        invoice_date=date.today(),
        initial_payment={"amount": "5000", "payment_mode": "Cash", "payment_date": date.today()},
    )

    invoice = detail["invoice"]
    assert invoice["subtotal"] == Decimal("10000.00")
    assert invoice["discount_total"] == Decimal("1000.00")
    assert invoice["cgst_total"] == Decimal("0.00")
    assert invoice["sgst_total"] == Decimal("0.00")
    assert invoice["grand_total"] == Decimal("9000.00")
    assert invoice["paid_amount"] == Decimal("5000.00")
    assert invoice["due_amount"] == Decimal("4000.00")
    assert invoice["status"] == "PARTIAL"
    assert len(detail["payments"]) == 1


def test_create_invoice_inter_state_uses_igst(db_session):
    _seed_business(db_session, state="Karnataka")
    customer = _seed_customer(db_session, state="Maharashtra")

    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )
    invoice = detail["invoice"]
    assert invoice["cgst_total"] == Decimal("0.00")
    assert invoice["sgst_total"] == Decimal("0.00")
    assert invoice["igst_total"] == Decimal("0.00")
    assert invoice["status"] == "PENDING"


def test_tax_is_fixed_at_zero_even_if_nonzero_passed(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)

    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "18"}],
        invoice_date=date.today(),
    )
    invoice = detail["invoice"]
    assert invoice["cgst_total"] == Decimal("0.00")
    assert invoice["sgst_total"] == Decimal("0.00")
    assert invoice["igst_total"] == Decimal("0.00")
    assert invoice["grand_total"] == Decimal("1000.00")


def test_create_invoice_rejects_empty_items(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    with pytest.raises(invoice_service.InvoiceError, match="At least one item"):
        invoice_service.create_invoice(db_session, None, customer["id"], items=[], invoice_date=date.today())


def test_create_invoice_rejects_unknown_customer(db_session):
    _seed_business(db_session)
    with pytest.raises(invoice_service.InvoiceError, match="Customer not found"):
        invoice_service.create_invoice(
            db_session, None, 9999,
            items=[{"item_name": "X", "quantity": 1, "rate": "100", "discount": "0", "tax_percentage": "0"}],
            invoice_date=date.today(),
        )


def test_full_payment_marks_invoice_paid(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )
    invoice_id = detail["invoice"]["id"]

    payment_service.record_payment(db_session, None, invoice_id, Decimal("1000"), "Cash", date.today())

    updated = invoice_service.get_invoice_detail(db_session, invoice_id)
    assert updated["invoice"]["status"] == "PAID"
    assert updated["invoice"]["due_amount"] == Decimal("0.00")


def test_overpayment_is_rejected(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )
    invoice_id = detail["invoice"]["id"]

    with pytest.raises(payment_service.PaymentError, match="cannot exceed"):
        payment_service.record_payment(db_session, None, invoice_id, Decimal("5000"), "Cash", date.today())


def test_cancel_invoice_without_payments(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )
    invoice_id = detail["invoice"]["id"]

    invoice_service.cancel_invoice(db_session, None, invoice_id)
    updated = invoice_service.get_invoice_detail(db_session, invoice_id)
    assert updated["invoice"]["status"] == "CANCELLED"


def test_cancel_invoice_with_payments_is_blocked(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
        initial_payment={"amount": "500", "payment_mode": "Cash", "payment_date": date.today()},
    )
    invoice_id = detail["invoice"]["id"]

    with pytest.raises(invoice_service.InvoiceError, match="recorded payments"):
        invoice_service.cancel_invoice(db_session, None, invoice_id)


def test_list_invoices_search_and_filter(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session, name="Asha Verma")
    invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )

    rows = invoice_service.list_invoices(db_session)
    assert len(rows) == 1
    assert rows[0]["customer_name"] == "Asha Verma"

    searched = invoice_service.list_invoices(db_session, query="Asha")
    assert len(searched) == 1

    none_found = invoice_service.list_invoices(db_session, query="Nobody")
    assert none_found == []


def test_invoice_creation(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session)
    detail = invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "1000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )
    assert detail["invoice"]["grand_total"] == Decimal("1000.00")
