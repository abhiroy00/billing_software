from datetime import date
from decimal import Decimal

from database.models.customer import Customer
from database.models.expense import Expense, ExpenseCategory
from database.models.invoice import Invoice, InvoiceItem
from database.models.payment import Payment
from services import dashboard_service


def _seed_billing_scenario(session):
    """Course = 10,000; Discount = 1,000; GST 18% -> matches Section 40 of the spec."""
    customer = Customer(customer_code="C-0001", name="Test Student", mobile="9876543210")
    session.add(customer)
    session.flush()

    invoice = Invoice(
        invoice_number="CH-2026-000001",
        invoice_date=date.today(),
        customer_id=customer.id,
        subtotal=Decimal("9000.00"),
        discount_total=Decimal("1000.00"),
        cgst_total=Decimal("810.00"),
        sgst_total=Decimal("810.00"),
        grand_total=Decimal("10620.00"),
        paid_amount=Decimal("5000.00"),
        due_amount=Decimal("5620.00"),
        status="PARTIAL",
    )
    session.add(invoice)
    session.flush()

    session.add(
        InvoiceItem(
            invoice_id=invoice.id,
            item_name="Python Bootcamp",
            quantity=Decimal("1"),
            rate=Decimal("10000.00"),
            discount=Decimal("1000.00"),
            tax_percentage=Decimal("18.00"),
            taxable_amount=Decimal("9000.00"),
            cgst_amount=Decimal("810.00"),
            sgst_amount=Decimal("810.00"),
            total_amount=Decimal("10620.00"),
        )
    )

    session.add(
        Payment(
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount=Decimal("5000.00"),
            payment_mode="Cash",
            payment_date=date.today(),
        )
    )

    category = ExpenseCategory(name="Rent")
    session.add(category)
    session.flush()
    session.add(
        Expense(
            category_id=category.id,
            description="Office rent",
            amount=Decimal("2000.00"),
            expense_date=date.today(),
            payment_mode="Bank Transfer",
            vendor="Landlord",
        )
    )
    session.flush()
    return customer, invoice


def test_kpis_reflect_seeded_data(db_session):
    _seed_billing_scenario(db_session)

    kpis = dashboard_service.get_kpis(db_session)

    assert kpis.today_revenue == Decimal("5000.00")
    assert kpis.month_revenue == Decimal("5000.00")
    assert kpis.pending_payments == Decimal("5620.00")
    assert kpis.total_customers == 1


def test_kpis_are_zero_with_no_data(db_session):
    kpis = dashboard_service.get_kpis(db_session)

    assert kpis.today_revenue == Decimal("0")
    assert kpis.month_revenue == Decimal("0")
    assert kpis.pending_payments == Decimal("0")
    assert kpis.total_customers == 0


def test_recent_invoices_and_payments(db_session):
    _, invoice = _seed_billing_scenario(db_session)

    recent_invoices = dashboard_service.get_recent_invoices(db_session)
    recent_payments = dashboard_service.get_recent_payments(db_session)

    assert len(recent_invoices) == 1
    assert recent_invoices[0]["invoice_number"] == "CH-2026-000001"
    assert recent_invoices[0]["grand_total"] == Decimal("10620.00")

    assert len(recent_payments) == 1
    assert recent_payments[0]["amount"] == Decimal("5000.00")
    assert recent_payments[0]["invoice_id"] == invoice.id


def test_top_courses_and_payment_mode_breakdown(db_session):
    _seed_billing_scenario(db_session)
    today = date.today()

    top_courses = dashboard_service.get_top_courses(db_session, today, today)
    breakdown = dashboard_service.get_payment_mode_breakdown(db_session, today, today)

    assert top_courses == [("Python Bootcamp", Decimal("10620.00"))]
    assert breakdown == [("Cash", Decimal("5000.00"))]


def test_overview_is_empty_state_safe_with_no_data(db_session):
    today = date.today()
    overview = dashboard_service.get_overview(db_session, today, today)

    assert overview.recent_invoices == []
    assert overview.recent_payments == []
    assert overview.recent_expenses == []
    assert overview.top_courses == []
    assert overview.monthly_revenue == []
    assert overview.payment_mode_breakdown == []
    assert overview.outstanding_dues == Decimal("0")
