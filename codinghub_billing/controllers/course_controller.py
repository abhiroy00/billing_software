"""GUI-facing layer over course_service (Section 12)."""
from __future__ import annotations

import logging

from database.connection import get_session
from services import auth_service, course_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")


def list_courses(query: str = "", status: str | None = None, category: str | None = None) -> list[dict]:
    with get_session() as session:
        return course_service.list_courses(session, query=query, status=status, category=category)


def list_categories() -> list[str]:
    with get_session() as session:
        return course_service.list_categories(session)


def list_active_courses_for_billing() -> list[dict]:
    """Slim (id, name, price, gst_percentage, discount) list used by the
    Billing item picker to auto-fill rate/tax/discount on selection."""
    with get_session() as session:
        rows = course_service.list_courses(session, status="Active")
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "price": r["price"],
                "gst_percentage": r["gst_percentage"],
                "discount": r["discount"],
            }
            for r in rows
        ]


def get_course(course_id: int) -> dict | None:
    with get_session() as session:
        return course_service.get_course_dict(session, course_id)


def create_course(data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            course = course_service.create_course(session, auth_service.current_session.user_id, data)
        return True, "", course
    except course_service.CourseError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to create course")
        return False, USER_FRIENDLY_MESSAGE, None


def update_course(course_id: int, data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            course = course_service.update_course(session, auth_service.current_session.user_id, course_id, data)
        return True, "", course
    except course_service.CourseError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to update course")
        return False, USER_FRIENDLY_MESSAGE, None


def delete_course(course_id: int) -> tuple[bool, str]:
    try:
        with get_session() as session:
            course_service.delete_course(session, auth_service.current_session.user_id, course_id)
        return True, ""
    except course_service.CourseError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to delete course")
        return False, USER_FRIENDLY_MESSAGE


def set_course_status(course_id: int, status: str) -> tuple[bool, str]:
    try:
        with get_session() as session:
            course_service.set_course_status(session, auth_service.current_session.user_id, course_id, status)
        return True, ""
    except course_service.CourseError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to update course status")
        return False, USER_FRIENDLY_MESSAGE


def export_courses_to_excel(path: str, query: str = "", status: str | None = None, category: str | None = None) -> tuple[bool, str]:
    try:
        from openpyxl import Workbook

        rows = list_courses(query=query, status=status, category=category)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Courses"
        headers = ["Name", "Category", "Price", "GST %", "Discount", "Duration", "Status"]
        sheet.append(headers)
        for row in rows:
            sheet.append(
                [
                    row["name"],
                    row["category"],
                    float(row["price"]),
                    float(row["gst_percentage"]),
                    float(row["discount"]),
                    row["duration"],
                    row["status"],
                ]
            )
        for column_cells in sheet.columns:
            length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None)
            sheet.column_dimensions[column_cells[0].column_letter].width = max(10, length + 2)

        workbook.save(path)
        return True, ""
    except Exception:
        logger.exception("Failed to export courses")
        return False, USER_FRIENDLY_MESSAGE
