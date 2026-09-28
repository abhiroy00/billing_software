"""GUI-facing layer over customer_service (Section 11). Views call these
functions and get back plain dicts / (success, message) tuples — never a
raw DB session or ORM instance."""
from __future__ import annotations

import logging

from sqlalchemy import select

from database.connection import get_session
from database.models.course import Course
from services import auth_service, customer_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")


def list_customers(query: str = "", status: str | None = None) -> list[dict]:
    with get_session() as session:
        return customer_service.list_customers(session, query=query, status=status)


def get_customer(customer_id: int) -> dict | None:
    with get_session() as session:
        return customer_service.get_customer_dict(session, customer_id)


def get_customer_detail(customer_id: int) -> tuple[dict | None, str]:
    try:
        with get_session() as session:
            return customer_service.get_customer_detail(session, customer_id), ""
    except customer_service.CustomerError as exc:
        return None, str(exc)


def create_customer(data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            customer = customer_service.create_customer(session, auth_service.current_session.user_id, data)
        return True, "", customer
    except customer_service.CustomerError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to create customer")
        return False, USER_FRIENDLY_MESSAGE, None


def update_customer(customer_id: int, data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            customer = customer_service.update_customer(session, auth_service.current_session.user_id, customer_id, data)
        return True, "", customer
    except customer_service.CustomerError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to update customer")
        return False, USER_FRIENDLY_MESSAGE, None


def delete_customer(customer_id: int) -> tuple[bool, str]:
    try:
        with get_session() as session:
            customer_service.delete_customer(session, auth_service.current_session.user_id, customer_id)
        return True, ""
    except customer_service.CustomerError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to delete customer")
        return False, USER_FRIENDLY_MESSAGE


def list_course_options() -> list[tuple[int, str]]:
    with get_session() as session:
        rows = session.execute(select(Course.id, Course.name).where(Course.status == "Active").order_by(Course.name)).all()
        return [(cid, name) for cid, name in rows]


CUSTOMER_TEMPLATE_HEADERS = [
    "Name", "Mobile", "Email", "Gender", "Student ID", "Date of Birth (DD-MM-YYYY)",
    "Address", "City", "State", "Pincode", "GSTIN", "PAN",
    "Course", "Enrollment Date (DD-MM-YYYY)", "Status", "Notes",
]
_CUSTOMER_TEMPLATE_SAMPLE = [
    "Rahul Sharma", "9876543210", "rahul@example.com", "Male", "STU-001", "15-08-2005",
    "MG Road", "Bengaluru", "Karnataka", "560001", "", "",
    "Python Full Stack", "01-09-2026", "Active", "Blank Name/Mobile auto-bhar jayega",
]


def customer_template_file(path: str) -> tuple[bool, str]:
    try:
        from utils import import_utils

        import_utils.write_template(path, "Customers", CUSTOMER_TEMPLATE_HEADERS, _CUSTOMER_TEMPLATE_SAMPLE)
        return True, ""
    except Exception:
        logger.exception("Failed to write customer template")
        return False, USER_FRIENDLY_MESSAGE


def import_customers(path: str) -> tuple[int, list[str], list[str]]:
    """Lenient import: blank Name/Mobile are auto-filled, never skipped.
    Returns (imported_count, errors, warnings)."""
    from utils import import_utils
    from utils.formatters import parse_date

    try:
        _, rows = import_utils.read_table_rows(path)
    except ValueError as exc:
        return 0, [str(exc)], []

    course_by_name = {name.lower(): cid for cid, name in list_course_options()}
    used_mobiles = {r["mobile"] for r in list_customers()}
    placeholder_seq = 9000000000
    imported = 0
    errors: list[str] = []
    warnings: list[str] = []
    for lineno, row in enumerate(rows, start=2):
        get = lambda *names: import_utils.cell(row, *names)  # noqa: E731
        name = get("name")
        mobile = get("mobile", "phone")
        auto_notes: list[str] = []
        if not name:
            name = f"Customer Row {lineno}"
            auto_notes.append("name missing tha")
        if not mobile:
            while str(placeholder_seq) in used_mobiles:
                placeholder_seq += 1
            mobile = str(placeholder_seq)
            used_mobiles.add(mobile)
            placeholder_seq += 1
            auto_notes.append("mobile missing tha")
        if auto_notes:
            warnings.append(f"Row {lineno}: {' + '.join(auto_notes)} — auto-fill kiya ('{name}', {mobile}).")
        course_name = get("course")
        course_id = None
        if course_name:
            course_id = course_by_name.get(course_name.lower())
            if course_id is None:
                errors.append(f"Row {lineno}: unknown course '{course_name}'.")
                continue
        try:
            dob = parse_date(get("date of birth (dd-mm-yyyy)", "dob", "date of birth")) if get("date of birth (dd-mm-yyyy)", "dob", "date of birth") else None
            enrolled = parse_date(get("enrollment date (dd-mm-yyyy)", "enrollment date")) if get("enrollment date (dd-mm-yyyy)", "enrollment date") else None
        except Exception:
            errors.append(f"Row {lineno}: date must be DD-MM-YYYY.")
            continue
        notes = get("notes")
        if auto_notes:
            notes = (notes + " | " if notes else "") + f"[Import: {' + '.join(auto_notes)}]"
        data = {
            "student_id": get("student id"),
            "name": name,
            "mobile": mobile,
            "email": get("email"),
            "gender": get("gender"),
            "date_of_birth": dob,
            "address": get("address"),
            "city": get("city"),
            "state": get("state"),
            "pincode": get("pincode"),
            "gstin": get("gstin"),
            "pan": get("pan"),
            "course_id": course_id,
            "enrollment_date": enrolled,
            "status": get("status") or "Active",
            "notes": notes,
        }
        success, message, _ = create_customer(data)
        if success:
            imported += 1
        else:
            errors.append(f"Row {lineno}: {message}")
        if len(errors) >= 20:
            errors.append("…stopping error list at 20, fix these and re-import the rest.")
            break
    return imported, errors, warnings


def export_customers_to_excel(path: str, query: str = "", status: str | None = None) -> tuple[bool, str]:
    try:
        from openpyxl import Workbook

        with get_session() as session:
            rows = customer_service.list_customers(session, query=query, status=status)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Customers"
        headers = ["Customer Code", "Name", "Mobile", "Email", "Course", "Status", "Outstanding"]
        sheet.append(headers)
        for row in rows:
            sheet.append(
                [
                    row["customer_code"],
                    row["name"],
                    row["mobile"],
                    row["email"],
                    row["course_name"],
                    row["status"],
                    float(row["outstanding"]),
                ]
            )
        for column_cells in sheet.columns:
            length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None)
            sheet.column_dimensions[column_cells[0].column_letter].width = max(12, length + 2)

        workbook.save(path)
        return True, ""
    except Exception:
        logger.exception("Failed to export customers")
        return False, USER_FRIENDLY_MESSAGE
