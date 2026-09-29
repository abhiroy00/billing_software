"""Course / Product business logic (Section 12). GUI code never touches
the Course model or CourseRepository directly."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.course import Course
from database.models.customer import Customer
from database.models.invoice import InvoiceItem
from database.repositories.course_repository import CourseRepository
from utils import validators

STATUS_OPTIONS = ["Active", "Inactive"]


class CourseError(Exception):
    pass


def _to_dict(course: Course) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "category": course.category,
        "description": course.description,
        "price": Decimal(str(course.price)),
        "gst_percentage": Decimal(str(course.gst_percentage)),
        "discount": Decimal(str(course.discount)),
        "duration": course.duration,
        "status": course.status,
    }


def validate_course_fields(data: dict) -> list[str]:
    errors = validators.run_validators(
        validators.required(data.get("name"), "Name"),
        validators.valid_numeric(data.get("price"), "Price"),
        validators.valid_numeric(data.get("gst_percentage"), "GST percentage"),
        validators.valid_numeric(data.get("discount"), "Discount", allow_negative=False),
    )
    # Tax fixed at 0% — koi aur GST allow nahi hai.
    try:
        if float(data.get("gst_percentage") or 0) != 0:
            errors.append("Tax is fixed at 0%. GST percentage must be 0.")
    except (TypeError, ValueError):
        pass
    try:
        price = float(data.get("price") or 0)
        discount = float(data.get("discount") or 0)
        discount_error = validators.valid_discount(discount, price)
        if discount_error:
            errors.append(discount_error)
    except (TypeError, ValueError):
        pass
    return errors


def list_courses(session: Session, query: str = "", status: str | None = None, category: str | None = None) -> list[dict]:
    courses = CourseRepository(session).search(query=query, status=status, category=category)
    return [_to_dict(c) for c in courses]


def list_categories(session: Session) -> list[str]:
    return CourseRepository(session).list_categories()


def get_course_dict(session: Session, course_id: int) -> dict | None:
    course = CourseRepository(session).get(course_id)
    return _to_dict(course) if course else None


def create_course(session: Session, user_id: int | None, data: dict) -> dict:
    errors = validate_course_fields(data)
    if errors:
        raise CourseError(" ".join(errors))

    course = Course(
        name=data["name"].strip(),
        category=(data.get("category") or "").strip(),
        description=(data.get("description") or "").strip(),
        price=Decimal(str(data.get("price") or 0)),
        gst_percentage=Decimal("0"),
        discount=Decimal(str(data.get("discount") or 0)),
        duration=(data.get("duration") or "").strip(),
        status=data.get("status", "Active"),
    )
    CourseRepository(session).add(course)
    return _to_dict(course)


def update_course(session: Session, user_id: int | None, course_id: int, data: dict) -> dict:
    errors = validate_course_fields(data)
    if errors:
        raise CourseError(" ".join(errors))

    repo = CourseRepository(session)
    course = repo.get(course_id)
    if course is None:
        raise CourseError("Course not found.")

    course.name = data["name"].strip()
    course.category = (data.get("category") or "").strip()
    course.description = (data.get("description") or "").strip()
    course.price = Decimal(str(data.get("price") or 0))
    course.gst_percentage = Decimal("0")
    course.discount = Decimal(str(data.get("discount") or 0))
    course.duration = (data.get("duration") or "").strip()
    course.status = data.get("status", course.status)
    repo.update(course)
    return _to_dict(course)


def delete_course(session: Session, user_id: int | None, course_id: int) -> None:
    repo = CourseRepository(session)
    course = repo.get(course_id)
    if course is None:
        raise CourseError("Course not found.")

    item_count = session.execute(
        select(func.count(InvoiceItem.id)).where(InvoiceItem.course_id == course_id)
    ).scalar_one()
    customer_count = session.execute(
        select(func.count(Customer.id)).where(Customer.course_id == course_id)
    ).scalar_one()
    if item_count > 0 or customer_count > 0:
        raise CourseError(
            "This course is linked to existing invoices or customers and cannot be deleted. Deactivate it instead."
        )

    name = course.name
    repo.delete(course)


def set_course_status(session: Session, user_id: int | None, course_id: int, status: str) -> dict:
    repo = CourseRepository(session)
    course = repo.get(course_id)
    if course is None:
        raise CourseError("Course not found.")
    course.status = status
    repo.update(course)
    return _to_dict(course)
