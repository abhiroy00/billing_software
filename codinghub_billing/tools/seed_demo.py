"""Client-demo seeder: fills an EMPTY database with realistic sample data
so the Dashboard looks alive on day one.

Usage:
    python3 tools/seed_demo.py            # uses the real app database
    CODINGHUB_APP_DATA_DIR=/tmp/demo python3 tools/seed_demo.py

Safety: refuses to run if any users/customers/invoices already exist.
Login after seeding:  username `admin` / password `admin123`.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from config import config  # noqa: E402
from database import connection  # noqa: E402
from database.connection import init_db  # noqa: E402
from database.models.user import User  # noqa: E402
from services import (  # noqa: E402
    auth_service,
    course_service,
    customer_service,
    expense_service,
    invoice_service,
    payment_service,
    settings_service,
)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def _month_ago(months: int) -> date:
    today = date.today()
    month = today.month - months
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(today.day, 28)
    return date(year, month, day)


def main() -> None:
    init_db(config.database_url)
    with connection.get_session() as session:
        existing_users = session.execute(select(func.count()).select_from(User)).scalar_one()
        n_invoices = len(invoice_service.list_invoices(session))
        if existing_users > 0 or n_invoices > 0:
            print("STOP: database already has data — seeder only runs on an empty DB.")
            print("Use a fresh CODINGHUB_APP_DATA_DIR to try the demo.")
            return

        admin = auth_service.bootstrap_first_run(
            session, username=ADMIN_USERNAME, full_name="Demo Admin",
            password=ADMIN_PASSWORD, email="admin@codinghub.demo",
        )
        uid = admin.id
        print(f"Admin created: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

        settings_service.save_business_settings(
            session, business_name="CodingHub Demo", email="hello@codinghub.demo",
            phone="9876543210", address="MG Road", city="Bengaluru",
            state="Karnataka", pincode="560001",
        )
        settings_service.save_invoice_settings(session, prefix="CH", starting_number=1, next_number=1)
        expense_service.ensure_default_categories(session)

        courses = []
        for name, category, price in [
            ("Python Full Stack", "Programming", "25000"),
            ("Data Science Bootcamp", "Programming", "35000"),
            ("Tally Prime + GST", "Accounting", "12000"),
            ("Digital Marketing Pro", "Marketing", "15000"),
            ("Spoken English", "Language", "8000"),
        ]:
            courses.append(course_service.create_course(session, uid, {
                "name": name, "category": category, "description": f"{name} complete course",
                "price": price, "gst_percentage": "0", "discount": "0",
                "duration": "3 months", "status": "Active",
            }))
        print(f"Courses: {len(courses)}")

        customers = []
        for i, (name, mobile) in enumerate([
            ("Rahul Sharma", "9876543210"), ("Priya Verma", "9876543211"),
            ("Amit Patel", "9876543212"), ("Sneha Rao", "9876543213"),
            ("Vikram Singh", "9876543214"), ("Anjali Gupta", "9876543215"),
        ]):
            customers.append(customer_service.create_customer(session, uid, {
                "name": name, "mobile": mobile, "email": "", "gender": "",
                "student_id": "", "address": "", "city": "Bengaluru", "state": "Karnataka",
                "pincode": "", "gstin": "", "pan": "", "course_id": courses[i % len(courses)]["id"],
                "date_of_birth": None, "enrollment_date": _month_ago(5), "status": "Active", "notes": "",
            }))
        print(f"Customers: {len(customers)}")

        modes = ["Cash", "UPI", "Card", "Bank Transfer"]
        plan = [
            (5, 0, None), (5, 1, "full"), (4, 2, "full"), (4, 3, "half"),
            (3, 4, "full"), (3, 0, "full"), (2, 1, "half"), (2, 5, "full"),
            (1, 2, "full"), (0, 3, "half"), (0, 4, None), (0, 0, "full"),
        ]
        for months_back, cust_idx, pay in plan:
            course = courses[(months_back + cust_idx) % len(courses)]
            inv_date = _month_ago(months_back)
            initial = None
            if pay in ("full", "half"):
                initial = {"amount": course["price"] if pay == "full" else str(int(course["price"]) // 2),
                           "payment_mode": modes[(months_back + cust_idx) % len(modes)],
                           "payment_date": inv_date}
            invoice_service.create_invoice(
                session, uid, customers[cust_idx]["id"],
                items=[{"item_name": course["name"], "quantity": 1, "rate": course["price"],
                        "discount": "0", "tax_percentage": "0"}],
                invoice_date=inv_date, notes="Demo invoice", initial_payment=initial,
            )
        print(f"Invoices: {len(plan)} (Paid / Partial / Pending mix)")

        rent = next(c for c in expense_service.list_categories(session) if c["name"] == "Rent")
        for months_back, desc, amount in [(2, "Office rent", "15000"), (1, "Office rent", "15000"),
                                         (1, "Facebook ads", "5000"), (0, "Stationery", "1200")]:
            expense_service.create_expense(session, uid, {
                "category_id": rent["id"], "description": desc, "amount": amount,
                "expense_date": _month_ago(months_back), "payment_mode": "Bank Transfer",
                "vendor": "Demo vendor", "notes": "", "attachment_path": None,
            })
        print("Expenses: 4")
        print("\nDone! Run `python3 app.py` and login as admin / admin123.")


if __name__ == "__main__":
    main()
