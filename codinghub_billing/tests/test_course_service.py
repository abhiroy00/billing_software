from datetime import date
from decimal import Decimal

import pytest

from database.models.customer import Customer
from database.models.invoice import Invoice, InvoiceItem
from services import course_service


def _valid_data(**overrides) -> dict:
    data = {
        "name": "Python Bootcamp",
        "category": "Programming",
        "description": "Learn Python from scratch.",
        "price": "10000",
        "gst_percentage": "0",
        "discount": "1000",
        "duration": "3 months",
        "status": "Active",
    }
    data.update(overrides)
    return data


def test_create_course_success(db_session):
    course = course_service.create_course(db_session, None, _valid_data())

    assert course["name"] == "Python Bootcamp"
    assert course["price"] == Decimal("10000")
    assert course["gst_percentage"] == Decimal("0")


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"name": ""}, "Name"),
        ({"price": "abc"}, "Price"),
        ({"price": "-100"}, "Price"),
        ({"gst_percentage": "18"}, "fixed at 0"),
        ({"gst_percentage": "150"}, "fixed at 0"),
        ({"discount": "50000"}, "cannot be greater"),
    ],
)
def test_create_course_validation_errors(db_session, overrides, expected_snippet):
    with pytest.raises(course_service.CourseError, match=expected_snippet):
        course_service.create_course(db_session, None, _valid_data(**overrides))


def test_update_course(db_session):
    created = course_service.create_course(db_session, None, _valid_data())
    updated = course_service.update_course(db_session, None, created["id"], _valid_data(price="12000", status="Inactive"))
    assert updated["price"] == Decimal("12000")
    assert updated["status"] == "Inactive"


def test_delete_course_success(db_session):
    created = course_service.create_course(db_session, None, _valid_data())
    course_service.delete_course(db_session, None, created["id"])
    assert course_service.get_course_dict(db_session, created["id"]) is None


def test_delete_course_blocked_when_linked_to_invoice_item(db_session):
    created = course_service.create_course(db_session, None, _valid_data())
    customer = Customer(customer_code="CUS-9001", name="Test User", mobile="9998887766")
    db_session.add(customer)
    db_session.flush()

    invoice = Invoice(invoice_number="CH-0001", invoice_date=date.today(), customer_id=customer.id)
    db_session.add(invoice)
    db_session.flush()
    db_session.add(
        InvoiceItem(
            invoice_id=invoice.id, course_id=created["id"], item_name="Python Bootcamp",
            quantity=Decimal("1"), rate=Decimal("10000"), total_amount=Decimal("10000"),
        )
    )
    db_session.flush()

    with pytest.raises(course_service.CourseError, match="linked to existing"):
        course_service.delete_course(db_session, None, created["id"])


def test_delete_course_blocked_when_linked_to_customer(db_session):
    created = course_service.create_course(db_session, None, _valid_data())
    db_session.add(Customer(customer_code="CUS-9002", name="Enrolled User", mobile="9998887755", course_id=created["id"]))
    db_session.flush()

    with pytest.raises(course_service.CourseError, match="linked to existing"):
        course_service.delete_course(db_session, None, created["id"])


def test_set_course_status(db_session):
    created = course_service.create_course(db_session, None, _valid_data())
    updated = course_service.set_course_status(db_session, None, created["id"], "Inactive")
    assert updated["status"] == "Inactive"


def test_list_courses_search_and_filter(db_session):
    course_service.create_course(db_session, None, _valid_data(name="Python Bootcamp", category="Programming"))
    course_service.create_course(db_session, None, _valid_data(name="Spoken English", category="Soft Skills", status="Inactive"))

    all_rows = course_service.list_courses(db_session)
    assert len(all_rows) == 2

    active_rows = course_service.list_courses(db_session, status="Active")
    assert len(active_rows) == 1
    assert active_rows[0]["name"] == "Python Bootcamp"

    searched = course_service.list_courses(db_session, query="English")
    assert len(searched) == 1
    assert searched[0]["name"] == "Spoken English"


def test_list_categories(db_session):
    course_service.create_course(db_session, None, _valid_data(name="Course A", category="Programming"))
    course_service.create_course(db_session, None, _valid_data(name="Course B", category="Design"))

    categories = course_service.list_categories(db_session)
    assert categories == ["Design", "Programming"]
