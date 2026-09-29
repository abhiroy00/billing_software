from datetime import date
from decimal import Decimal

import pytest

from services import expense_service


def test_ensure_default_categories_is_idempotent(db_session):
    expense_service.ensure_default_categories(db_session)
    expense_service.ensure_default_categories(db_session)

    categories = expense_service.list_categories(db_session)
    names = {c["name"] for c in categories}
    assert names == set(expense_service.DEFAULT_CATEGORIES)
    assert len(categories) == len(expense_service.DEFAULT_CATEGORIES)


def _valid_data(session, **overrides) -> dict:
    categories = expense_service.list_categories(session)
    rent = next(c for c in categories if c["name"] == "Rent")
    data = {
        "category_id": rent["id"],
        "description": "Office rent for September",
        "amount": "15000",
        "expense_date": date.today(),
        "payment_mode": "Bank Transfer",
        "vendor": "Landlord Properties",
        "notes": "",
        "attachment_path": None,
    }
    data.update(overrides)
    return data


def test_create_expense_success(db_session):
    expense = expense_service.create_expense(db_session, None, _valid_data(db_session))

    assert expense["category_name"] == "Rent"
    assert expense["amount"] == Decimal("15000")
    assert expense["vendor"] == "Landlord Properties"


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"category_id": None}, "Category"),
        ({"amount": "abc"}, "Amount"),
        ({"amount": "-500"}, "Amount"),
        ({"expense_date": None}, "Expense date"),
    ],
)
def test_create_expense_validation_errors(db_session, overrides, expected_snippet):
    with pytest.raises(expense_service.ExpenseError, match=expected_snippet):
        expense_service.create_expense(db_session, None, _valid_data(db_session, **overrides))


def test_update_expense(db_session):
    created = expense_service.create_expense(db_session, None, _valid_data(db_session))
    updated = expense_service.update_expense(
        db_session, None, created["id"], _valid_data(db_session, amount="18000", vendor="New Landlord")
    )
    assert updated["amount"] == Decimal("18000")
    assert updated["vendor"] == "New Landlord"


def test_delete_expense(db_session):
    created = expense_service.create_expense(db_session, None, _valid_data(db_session))
    expense_service.delete_expense(db_session, None, created["id"])
    assert expense_service.get_expense_dict(db_session, created["id"]) is None


def test_list_expenses_search_and_filter_by_category(db_session):
    categories = expense_service.list_categories(db_session)
    rent_id = next(c["id"] for c in categories if c["name"] == "Rent")
    software_id = next(c["id"] for c in categories if c["name"] == "Software")

    expense_service.create_expense(
        db_session, None, _valid_data(db_session, category_id=rent_id, description="Office rent", vendor="Landlord Co")
    )
    expense_service.create_expense(
        db_session, None,
        _valid_data(db_session, category_id=software_id, description="Adobe subscription", vendor="Adobe Inc", amount="2000"),
    )

    all_rows = expense_service.list_expenses(db_session)
    assert len(all_rows) == 2

    rent_only = expense_service.list_expenses(db_session, category_id=rent_id)
    assert len(rent_only) == 1
    assert rent_only[0]["category_name"] == "Rent"

    searched = expense_service.list_expenses(db_session, query="Adobe")
    assert len(searched) == 1
    assert searched[0]["vendor"] == "Adobe Inc"
