from datetime import date, timedelta
from decimal import Decimal

from services import expense_service, invoice_service, report_service
from tests.test_invoice_service import _seed_business, _seed_customer

TODAY = date.today()


def _create_invoice(session, customer_id, rate, discount="0", tax="0", payment=None, invoice_date=None):
    return invoice_service.create_invoice(
        session, None, customer_id,
        items=[{"item_name": "Python Bootcamp", "quantity": 1, "rate": rate, "discount": discount, "tax_percentage": tax}],
        invoice_date=invoice_date or TODAY,
        initial_payment=payment,
    )


def test_sales_report_summary_excludes_cancelled(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    bala = _seed_customer(db_session, name="Bala Reddy", mobile="9998887772")

    _create_invoice(db_session, asha["id"], "10000", discount="1000",
                     payment={"amount": "5000", "payment_mode": "Cash", "payment_date": TODAY})
    cancelled = _create_invoice(db_session, bala["id"], "2000", tax="0")
    invoice_service.cancel_invoice(db_session, None, cancelled["invoice"]["id"])

    result = report_service.sales_report(db_session, TODAY, TODAY)

    assert len(result.rows) == 2
    assert result.summary["total_invoices"] == 1
    assert result.summary["total_sales"] == Decimal("9000.00")
    assert result.summary["total_collected"] == Decimal("5000.00")
    assert result.summary["total_due"] == Decimal("4000.00")
    assert result.summary["average_invoice_value"] == Decimal("9000.00")


def test_sales_report_filters_by_customer_and_status(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    bala = _seed_customer(db_session, name="Bala Reddy", mobile="9998887772")
    _create_invoice(db_session, asha["id"], "1000", tax="0")
    _create_invoice(db_session, bala["id"], "2000", tax="0")

    only_asha = report_service.sales_report(db_session, TODAY, TODAY, customer_id=asha["id"])
    assert len(only_asha.rows) == 1
    assert only_asha.rows[0]["customer_name"] == "Asha Verma"

    only_pending = report_service.sales_report(db_session, TODAY, TODAY, status="PENDING")
    assert len(only_pending.rows) == 2


def test_payment_report_totals_and_mode_breakdown(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    bala = _seed_customer(db_session, name="Bala Reddy", mobile="9998887772")
    _create_invoice(db_session, asha["id"], "1000", tax="0", payment={"amount": "1000", "payment_mode": "Cash", "payment_date": TODAY})
    _create_invoice(db_session, bala["id"], "2000", tax="0", payment={"amount": "2000", "payment_mode": "UPI", "payment_date": TODAY})

    result = report_service.payment_report(db_session, TODAY, TODAY)
    assert result.summary["total_collected"] == Decimal("3000.00")
    assert result.summary["total_transactions"] == 2
    assert result.summary["by_mode"] == {"Cash": Decimal("1000.00"), "UPI": Decimal("2000.00")}

    cash_only = report_service.payment_report(db_session, TODAY, TODAY, payment_mode="Cash")
    assert len(cash_only.rows) == 1
    assert cash_only.summary["total_collected"] == Decimal("1000.00")


def test_payment_report_respects_date_range(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    _create_invoice(db_session, asha["id"], "1000", tax="0", payment={"amount": "1000", "payment_mode": "Cash", "payment_date": TODAY})

    yesterday = TODAY - timedelta(days=1)
    result = report_service.payment_report(db_session, yesterday, yesterday)
    assert result.rows == []
    assert result.summary["total_collected"] == Decimal("0")


def test_pending_payments_report_only_shows_dues(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    bala = _seed_customer(db_session, name="Bala Reddy", mobile="9998887772")
    _create_invoice(db_session, asha["id"], "1000", tax="0", payment={"amount": "1000", "payment_mode": "Cash", "payment_date": TODAY})
    _create_invoice(db_session, bala["id"], "2000", tax="0", payment={"amount": "500", "payment_mode": "Cash", "payment_date": TODAY})

    result = report_service.pending_payments_report(db_session)
    assert len(result.rows) == 1
    assert result.rows[0]["customer_name"] == "Bala Reddy"
    assert result.summary["total_outstanding"] == Decimal("1500.00")
    assert result.summary["total_pending_invoices"] == 1
    assert result.summary["customers_with_dues"] == 1


def test_gst_report_matches_section_40_example(db_session):
    _seed_business(db_session, state="Karnataka")
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771", state="Karnataka")
    _create_invoice(db_session, asha["id"], "10000", discount="1000", tax="0")

    result = report_service.gst_report(db_session, TODAY, TODAY)
    assert result.summary["taxable_total"] == Decimal("9000.00")
    assert result.summary["cgst_total"] == Decimal("0.00")
    assert result.summary["sgst_total"] == Decimal("0.00")
    assert result.summary["igst_total"] == Decimal("0.00")
    assert result.summary["total_tax"] == Decimal("0.00")
    assert result.summary["grand_total"] == Decimal("9000.00")


def test_gst_report_inter_state_uses_igst(db_session):
    _seed_business(db_session, state="Karnataka")
    bala = _seed_customer(db_session, name="Bala Reddy", mobile="9998887772", state="Maharashtra")
    _create_invoice(db_session, bala["id"], "1000", tax="0")

    result = report_service.gst_report(db_session, TODAY, TODAY)
    assert result.summary["cgst_total"] == Decimal("0.00")
    assert result.summary["sgst_total"] == Decimal("0.00")
    assert result.summary["igst_total"] == Decimal("0.00")


def test_expense_report_totals_and_category_breakdown(db_session):
    categories = expense_service.list_categories(db_session)
    rent_id = next(c["id"] for c in categories if c["name"] == "Rent")
    software_id = next(c["id"] for c in categories if c["name"] == "Software")

    expense_service.create_expense(db_session, None, {
        "category_id": rent_id, "description": "Rent", "amount": "10000", "expense_date": TODAY,
        "payment_mode": "Bank Transfer", "vendor": "Landlord", "notes": "", "attachment_path": None,
    })
    expense_service.create_expense(db_session, None, {
        "category_id": software_id, "description": "Subscription", "amount": "2000", "expense_date": TODAY,
        "payment_mode": "Card", "vendor": "Adobe", "notes": "", "attachment_path": None,
    })

    result = report_service.expense_report(db_session, TODAY, TODAY)
    assert result.summary["total_expenses"] == Decimal("12000.00")
    assert result.summary["total_count"] == 2
    assert result.summary["by_category"] == {"Rent": Decimal("10000.00"), "Software": Decimal("2000.00")}

    rent_only = report_service.expense_report(db_session, TODAY, TODAY, category_id=rent_id)
    assert len(rent_only.rows) == 1


def test_profit_summary_computes_net_profit(db_session):
    _seed_business(db_session)
    asha = _seed_customer(db_session, name="Asha Verma", mobile="9998887771")
    _create_invoice(db_session, asha["id"], "5000", tax="0", payment={"amount": "5000", "payment_mode": "Cash", "payment_date": TODAY})

    categories = expense_service.list_categories(db_session)
    rent_id = next(c["id"] for c in categories if c["name"] == "Rent")
    expense_service.create_expense(db_session, None, {
        "category_id": rent_id, "description": "Rent", "amount": "2000", "expense_date": TODAY,
        "payment_mode": "Cash", "vendor": "Landlord", "notes": "", "attachment_path": None,
    })

    result = report_service.profit_summary(db_session, TODAY, TODAY)
    assert result.summary["revenue_collected"] == Decimal("5000.00")
    assert result.summary["total_expenses"] == Decimal("2000.00")
    assert result.summary["net_profit"] == Decimal("3000.00")
    assert result.summary["invoiced_sales"] == Decimal("5000.00")
