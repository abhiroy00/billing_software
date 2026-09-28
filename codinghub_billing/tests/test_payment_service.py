from datetime import date
from decimal import Decimal

from services import invoice_service, payment_service
from tests.test_invoice_service import _seed_business, _seed_customer


def _seed_invoice_with_payment(session, customer_name, mobile, amount_paid, payment_mode="Cash"):
    customer = _seed_customer(session, name=customer_name, mobile=mobile)
    detail = invoice_service.create_invoice(
        session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "2000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
        initial_payment={"amount": amount_paid, "payment_mode": payment_mode, "payment_date": date.today()},
    )
    return detail


def test_list_all_payments_joins_invoice_and_customer(db_session):
    _seed_business(db_session)
    _seed_invoice_with_payment(db_session, "Asha Verma", "9998887771", "500", payment_mode="Cash")
    _seed_invoice_with_payment(db_session, "Bala Reddy", "9998887772", "1000", payment_mode="UPI")

    rows = payment_service.list_all_payments(db_session)
    assert len(rows) == 2
    names = {r["customer_name"] for r in rows}
    assert names == {"Asha Verma", "Bala Reddy"}
    assert all(r["invoice_number"].startswith("CH-") for r in rows)


def test_list_all_payments_filters_by_mode(db_session):
    _seed_business(db_session)
    _seed_invoice_with_payment(db_session, "Asha Verma", "9998887771", "500", payment_mode="Cash")
    _seed_invoice_with_payment(db_session, "Bala Reddy", "9998887772", "1000", payment_mode="UPI")

    cash_only = payment_service.list_all_payments(db_session, payment_mode="Cash")
    assert len(cash_only) == 1
    assert cash_only[0]["customer_name"] == "Asha Verma"
    assert cash_only[0]["amount"] == Decimal("500.00")


def test_list_all_payments_search_by_customer_name(db_session):
    _seed_business(db_session)
    _seed_invoice_with_payment(db_session, "Asha Verma", "9998887771", "500")
    _seed_invoice_with_payment(db_session, "Bala Reddy", "9998887772", "1000")

    results = payment_service.list_all_payments(db_session, query="Bala")
    assert len(results) == 1
    assert results[0]["customer_name"] == "Bala Reddy"


def test_list_all_payments_search_by_invoice_number(db_session):
    _seed_business(db_session)
    detail = _seed_invoice_with_payment(db_session, "Asha Verma", "9998887771", "500")
    invoice_number = detail["invoice"]["invoice_number"]

    results = payment_service.list_all_payments(db_session, query=invoice_number)
    assert len(results) == 1


def test_list_all_payments_empty_when_no_payments(db_session):
    _seed_business(db_session)
    customer = _seed_customer(db_session, name="No Payment Yet", mobile="9111111111")
    invoice_service.create_invoice(
        db_session, None, customer["id"],
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": "2000", "discount": "0", "tax_percentage": "0"}],
        invoice_date=date.today(),
    )

    assert payment_service.list_all_payments(db_session) == []
