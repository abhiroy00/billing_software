"""Customer business logic (Section 11). GUI code never touches the
Customer model or CustomerRepository directly — it always goes through
here so validation and code generation stay centralized."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.course import Course
from database.models.customer import Customer
from database.models.invoice import Invoice
from database.models.payment import Payment
from database.repositories.customer_repository import CustomerRepository
from utils import validators

CUSTOMER_CODE_PREFIX = "CUS-"


class CustomerError(Exception):
    pass


def _to_dict(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "student_id": customer.student_id,
        "name": customer.name,
        "mobile": customer.mobile,
        "email": customer.email,
        "gender": customer.gender,
        "date_of_birth": customer.date_of_birth,
        "address": customer.address,
        "city": customer.city,
        "state": customer.state,
        "pincode": customer.pincode,
        "gstin": customer.gstin,
        "pan": customer.pan,
        "course_id": customer.course_id,
        "enrollment_date": customer.enrollment_date,
        "status": customer.status,
        "notes": customer.notes,
    }


def generate_customer_code(session: Session) -> str:
    stmt = select(Customer.customer_code).where(Customer.customer_code.like(f"{CUSTOMER_CODE_PREFIX}%"))
    codes = session.execute(stmt).scalars().all()
    max_number = 0
    for code in codes:
        suffix = code.removeprefix(CUSTOMER_CODE_PREFIX)
        if suffix.isdigit():
            max_number = max(max_number, int(suffix))
    return f"{CUSTOMER_CODE_PREFIX}{max_number + 1:04d}"


def validate_customer_fields(data: dict) -> list[str]:
    return validators.run_validators(
        validators.required(data.get("name"), "Name"),
        validators.required(data.get("mobile"), "Mobile number"),
        validators.valid_mobile(data.get("mobile")),
        validators.valid_email(data.get("email")),
        validators.valid_gstin(data.get("gstin")),
        validators.valid_pan(data.get("pan")),
    )


def list_customers(session: Session, query: str = "", status: str | None = None) -> list[dict]:
    customers = CustomerRepository(session).search(query=query, status=status)
    customer_ids = [c.id for c in customers]

    outstanding_by_customer: dict[int, Decimal] = {}
    if customer_ids:
        rows = session.execute(
            select(Invoice.customer_id, func.coalesce(func.sum(Invoice.due_amount), 0))
            .where(Invoice.customer_id.in_(customer_ids))
            .group_by(Invoice.customer_id)
        ).all()
        outstanding_by_customer = {cid: Decimal(str(total)) for cid, total in rows}

    course_ids = {c.course_id for c in customers if c.course_id is not None}
    course_names: dict[int, str] = {}
    if course_ids:
        rows = session.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids))).all()
        course_names = dict(rows)

    return [
        {
            "id": c.id,
            "customer_code": c.customer_code,
            "name": c.name,
            "mobile": c.mobile,
            "email": c.email or "",
            "course_name": course_names.get(c.course_id, "") if c.course_id else "",
            "status": c.status,
            "outstanding": outstanding_by_customer.get(c.id, Decimal("0")),
        }
        for c in customers
    ]


def get_customer_dict(session: Session, customer_id: int) -> dict | None:
    customer = CustomerRepository(session).get(customer_id)
    return _to_dict(customer) if customer else None


def create_customer(session: Session, user_id: int | None, data: dict) -> dict:
    errors = validate_customer_fields(data)
    if errors:
        raise CustomerError(" ".join(errors))

    repo = CustomerRepository(session)
    customer = Customer(
        customer_code=generate_customer_code(session),
        student_id=data.get("student_id") or None,
        name=data["name"].strip(),
        mobile=data["mobile"].strip(),
        email=(data.get("email") or "").strip() or None,
        gender=data.get("gender") or None,
        date_of_birth=data.get("date_of_birth"),
        address=data.get("address", ""),
        city=data.get("city", ""),
        state=data.get("state", ""),
        pincode=data.get("pincode", ""),
        gstin=(data.get("gstin") or "").strip().upper() or None,
        pan=(data.get("pan") or "").strip().upper() or None,
        course_id=data.get("course_id"),
        enrollment_date=data.get("enrollment_date"),
        status=data.get("status", "Active"),
        notes=data.get("notes", ""),
    )
    repo.add(customer)
    return _to_dict(customer)


def update_customer(session: Session, user_id: int | None, customer_id: int, data: dict) -> dict:
    errors = validate_customer_fields(data)
    if errors:
        raise CustomerError(" ".join(errors))

    repo = CustomerRepository(session)
    customer = repo.get(customer_id)
    if customer is None:
        raise CustomerError("Customer not found.")

    customer.student_id = data.get("student_id") or None
    customer.name = data["name"].strip()
    customer.mobile = data["mobile"].strip()
    customer.email = (data.get("email") or "").strip() or None
    customer.gender = data.get("gender") or None
    customer.date_of_birth = data.get("date_of_birth")
    customer.address = data.get("address", "")
    customer.city = data.get("city", "")
    customer.state = data.get("state", "")
    customer.pincode = data.get("pincode", "")
    customer.gstin = (data.get("gstin") or "").strip().upper() or None
    customer.pan = (data.get("pan") or "").strip().upper() or None
    customer.course_id = data.get("course_id")
    customer.enrollment_date = data.get("enrollment_date")
    customer.status = data.get("status", customer.status)
    customer.notes = data.get("notes", "")
    repo.update(customer)

    return _to_dict(customer)


def delete_customer(session: Session, user_id: int | None, customer_id: int) -> None:
    repo = CustomerRepository(session)
    customer = repo.get(customer_id)
    if customer is None:
        raise CustomerError("Customer not found.")

    invoice_count = session.execute(
        select(func.count(Invoice.id)).where(Invoice.customer_id == customer_id)
    ).scalar_one()
    if invoice_count > 0:
        raise CustomerError(
            "This customer has existing invoices and cannot be deleted. Deactivate them instead."
        )

    name, code = customer.name, customer.customer_code
    repo.delete(customer)


def get_customer_detail(session: Session, customer_id: int) -> dict:
    customer = CustomerRepository(session).get(customer_id)
    if customer is None:
        raise CustomerError("Customer not found.")

    invoice_rows = session.execute(
        select(Invoice).where(Invoice.customer_id == customer_id).order_by(Invoice.invoice_date.desc())
    ).scalars().all()
    invoices = [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "grand_total": Decimal(str(inv.grand_total)),
            "paid_amount": Decimal(str(inv.paid_amount)),
            "due_amount": Decimal(str(inv.due_amount)),
            "status": inv.status,
        }
        for inv in invoice_rows
    ]

    payment_rows = session.execute(
        select(Payment).where(Payment.customer_id == customer_id).order_by(Payment.payment_date.desc())
    ).scalars().all()
    payments = [
        {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "amount": Decimal(str(p.amount)),
            "payment_mode": p.payment_mode,
            "payment_date": p.payment_date,
        }
        for p in payment_rows
    ]

    outstanding = sum((inv["due_amount"] for inv in invoices), Decimal("0"))

    course_name = ""
    if customer.course_id:
        course = session.get(Course, customer.course_id)
        course_name = course.name if course else ""

    activity = []

    customer_dict = _to_dict(customer)
    customer_dict["course_name"] = course_name

    return {
        "customer": customer_dict,
        "invoices": invoices,
        "payments": payments,
        "outstanding": outstanding,
        "activity": activity,
    }
