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
