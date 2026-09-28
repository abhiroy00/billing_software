from datetime import date
from decimal import Decimal

import pytest

from database.models.audit_log import AuditLog
from database.models.course import Course
from database.models.invoice import Invoice
from services import customer_service


def _valid_data(**overrides) -> dict:
    data = {
        "name": "Ravi Kumar",
        "mobile": "9876543210",
        "email": "ravi@example.com",
        "gender": "Male",
        "student_id": "STU-1",
        "address": "12 MG Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "gstin": "",
        "pan": "",
        "course_id": None,
        "date_of_birth": None,
        "enrollment_date": date.today(),
        "status": "Active",
        "notes": "",
    }
    data.update(overrides)
    return data


def test_generate_customer_code_is_sequential(db_session):
    assert customer_service.generate_customer_code(db_session) == "CUS-0001"
    customer_service.create_customer(db_session, None, _valid_data())
    assert customer_service.generate_customer_code(db_session) == "CUS-0002"


def test_create_customer_success_and_audit_log(db_session):
    customer = customer_service.create_customer(db_session, None, _valid_data())

    assert customer["customer_code"] == "CUS-0001"
    assert customer["name"] == "Ravi Kumar"

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "create"
    assert logs[0].entity_type == "customer"
    assert logs[0].entity_id == str(customer["id"])


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"name": ""}, "Name"),
        ({"mobile": ""}, "Mobile number"),
        ({"mobile": "12345"}, "valid 10-digit"),
        ({"email": "not-an-email"}, "valid email"),
        ({"gstin": "invalid"}, "GSTIN"),
        ({"pan": "invalid"}, "PAN"),
    ],
)
def test_create_customer_validation_errors(db_session, overrides, expected_snippet):
    with pytest.raises(customer_service.CustomerError, match=expected_snippet):
        customer_service.create_customer(db_session, None, _valid_data(**overrides))


def test_update_customer(db_session):
    created = customer_service.create_customer(db_session, None, _valid_data())
    updated = customer_service.update_customer(
        db_session, None, created["id"], _valid_data(name="Ravi K. Sharma", city="Mysuru")
    )
    assert updated["name"] == "Ravi K. Sharma"
    assert updated["city"] == "Mysuru"


def test_delete_customer_success(db_session):
    created = customer_service.create_customer(db_session, None, _valid_data())
    customer_service.delete_customer(db_session, None, created["id"])
    assert customer_service.get_customer_dict(db_session, created["id"]) is None


def test_delete_customer_blocked_when_invoices_exist(db_session):
    created = customer_service.create_customer(db_session, None, _valid_data())
    db_session.add(
        Invoice(
            invoice_number="CH-0001",
            invoice_date=date.today(),
            customer_id=created["id"],
            grand_total=Decimal("1000.00"),
            due_amount=Decimal("1000.00"),
        )
    )
    db_session.flush()

    with pytest.raises(customer_service.CustomerError, match="existing invoices"):
        customer_service.delete_customer(db_session, None, created["id"])


def test_list_customers_search_filter_and_outstanding(db_session):
    course = Course(name="Python Bootcamp", price=Decimal("10000"))
    db_session.add(course)
    db_session.flush()

    active = customer_service.create_customer(
        db_session, None, _valid_data(name="Asha Verma", mobile="9998887771", course_id=course.id)
    )
    customer_service.create_customer(
        db_session, None, _valid_data(name="Bala Reddy", mobile="9998887772", status="Inactive")
    )

    db_session.add(
        Invoice(
            invoice_number="CH-0002",
            invoice_date=date.today(),
            customer_id=active["id"],
            grand_total=Decimal("5000.00"),
            due_amount=Decimal("2000.00"),
        )
    )
    db_session.flush()

    all_rows = customer_service.list_customers(db_session)
    assert len(all_rows) == 2

    active_rows = customer_service.list_customers(db_session, status="Active")
    assert len(active_rows) == 1
    assert active_rows[0]["name"] == "Asha Verma"
    assert active_rows[0]["course_name"] == "Python Bootcamp"
    assert active_rows[0]["outstanding"] == Decimal("2000.00")

    searched = customer_service.list_customers(db_session, query="Bala")
    assert len(searched) == 1
    assert searched[0]["name"] == "Bala Reddy"
    assert searched[0]["outstanding"] == Decimal("0")


def test_get_customer_detail_aggregation(db_session):
    created = customer_service.create_customer(db_session, None, _valid_data())
    invoice = Invoice(
        invoice_number="CH-0003",
        invoice_date=date.today(),
        customer_id=created["id"],
        grand_total=Decimal("3000.00"),
        paid_amount=Decimal("1000.00"),
        due_amount=Decimal("2000.00"),
        status="PARTIAL",
    )
    db_session.add(invoice)
    db_session.flush()

    detail = customer_service.get_customer_detail(db_session, created["id"])

    assert detail["customer"]["name"] == "Ravi Kumar"
    assert len(detail["invoices"]) == 1
    assert detail["invoices"][0]["invoice_number"] == "CH-0003"
    assert detail["outstanding"] == Decimal("2000.00")
    assert len(detail["activity"]) == 1
    assert detail["activity"][0]["action"] == "create"


def test_get_customer_detail_missing_raises(db_session):
    with pytest.raises(customer_service.CustomerError):
        customer_service.get_customer_detail(db_session, 999)
