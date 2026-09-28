"""Expense tracking business logic (Section 16)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from database.models.expense import Expense, ExpenseCategory
from database.repositories.expense_repository import ExpenseCategoryRepository, ExpenseRepository
from services import audit_service
from utils import validators

DEFAULT_CATEGORIES = [
    "Rent", "Salary", "Electricity", "Internet", "Marketing", "Software", "Hardware", "Travel", "Other",
]

PAYMENT_MODES = ["Cash", "UPI", "Bank Transfer", "Card", "Cheque", "Other"]


class ExpenseError(Exception):
    pass


def ensure_default_categories(session: Session) -> None:
    repo = ExpenseCategoryRepository(session)
    for name in DEFAULT_CATEGORIES:
        if repo.get_by_name(name) is None:
            repo.add(ExpenseCategory(name=name, is_default=True))


def list_categories(session: Session) -> list[dict]:
    ensure_default_categories(session)
    return [{"id": c.id, "name": c.name} for c in ExpenseCategoryRepository(session).list_all()]


def _to_dict(expense: Expense, category_name: str) -> dict:
    return {
        "id": expense.id,
        "category_id": expense.category_id,
        "category_name": category_name,
        "description": expense.description,
        "amount": Decimal(str(expense.amount)),
        "expense_date": expense.expense_date,
        "payment_mode": expense.payment_mode,
        "vendor": expense.vendor,
        "notes": expense.notes,
        "attachment_path": expense.attachment_path,
    }


def validate_expense_fields(data: dict) -> list[str]:
    return validators.run_validators(
        validators.required(data.get("category_id"), "Category"),
        validators.valid_numeric(data.get("amount"), "Amount"),
        validators.required(data.get("expense_date"), "Expense date"),
    )


def list_expenses(
    session: Session,
    query: str = "",
    category_id: int | None = None,
    payment_mode: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    rows = ExpenseRepository(session).search(
        query=query, category_id=category_id, payment_mode=payment_mode, date_from=date_from, date_to=date_to
    )
    return [_to_dict(expense, category_name) for expense, category_name in rows]


def get_expense_dict(session: Session, expense_id: int) -> dict | None:
    expense = ExpenseRepository(session).get(expense_id)
    if expense is None:
        return None
    category = session.get(ExpenseCategory, expense.category_id)
    return _to_dict(expense, category.name if category else "")


def create_expense(session: Session, user_id: int | None, data: dict) -> dict:
    errors = validate_expense_fields(data)
    if errors:
        raise ExpenseError(" ".join(errors))

    expense = Expense(
        category_id=data["category_id"],
        description=(data.get("description") or "").strip(),
        amount=Decimal(str(data["amount"])),
        expense_date=data["expense_date"],
        payment_mode=data.get("payment_mode", "Cash"),
        vendor=(data.get("vendor") or "").strip(),
        notes=(data.get("notes") or "").strip(),
        attachment_path=data.get("attachment_path"),
        created_by=user_id,
    )
    ExpenseRepository(session).add(expense)

    category = session.get(ExpenseCategory, expense.category_id)
    audit_service.log(
        session, user_id, "create", entity_type="expense", entity_id=expense.id,
        description=f"Recorded expense of {expense.amount} ({category.name if category else ''})",
    )
    return _to_dict(expense, category.name if category else "")


def update_expense(session: Session, user_id: int | None, expense_id: int, data: dict) -> dict:
    errors = validate_expense_fields(data)
    if errors:
        raise ExpenseError(" ".join(errors))

    repo = ExpenseRepository(session)
    expense = repo.get(expense_id)
    if expense is None:
        raise ExpenseError("Expense not found.")

    expense.category_id = data["category_id"]
    expense.description = (data.get("description") or "").strip()
    expense.amount = Decimal(str(data["amount"]))
    expense.expense_date = data["expense_date"]
    expense.payment_mode = data.get("payment_mode", expense.payment_mode)
    expense.vendor = (data.get("vendor") or "").strip()
    expense.notes = (data.get("notes") or "").strip()
    if "attachment_path" in data:
        expense.attachment_path = data.get("attachment_path")
    repo.update(expense)

    category = session.get(ExpenseCategory, expense.category_id)
    audit_service.log(
        session, user_id, "update", entity_type="expense", entity_id=expense.id,
        description=f"Updated expense of {expense.amount} ({category.name if category else ''})",
    )
    return _to_dict(expense, category.name if category else "")


def delete_expense(session: Session, user_id: int | None, expense_id: int) -> None:
    repo = ExpenseRepository(session)
    expense = repo.get(expense_id)
    if expense is None:
        raise ExpenseError("Expense not found.")

    amount = expense.amount
    repo.delete(expense)
    audit_service.log(
        session, user_id, "delete", entity_type="expense", entity_id=expense_id,
        description=f"Deleted expense of {amount}",
    )
