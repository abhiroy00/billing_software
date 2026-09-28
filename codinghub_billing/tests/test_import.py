import pytest

from controllers import course_controller, customer_controller, expense_controller
from services import expense_service
from utils import import_utils
from utils.export_utils import write_excel_rows


def _xlsx(path, headers, rows):
    write_excel_rows(str(path), "Sheet1", headers, rows)
    return str(path)


def test_read_xlsx_and_headers(tmp_path):
    path = _xlsx(tmp_path / "a.xlsx", ["Name", "Mobile"], [["Ravi", "9876543210"]])
    headers, rows = import_utils.read_table_rows(path)
    assert headers == ["name", "mobile"]
    assert rows == [{"name": "Ravi", "mobile": "9876543210"}]


def test_read_csv(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("Name,Price\nPython,25000\n", encoding="utf-8-sig")
    headers, rows = import_utils.read_table_rows(str(path))
    assert rows[0]["price"] == "25000"


def test_unsupported_extension(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello")
    with pytest.raises(ValueError, match="Only .xlsx and .csv"):
        import_utils.read_table_rows(str(path))


def test_empty_file_rejected(tmp_path):
    path = _xlsx(tmp_path / "empty.xlsx", ["Name"], [])
    with pytest.raises(ValueError, match="No data rows"):
        import_utils.read_table_rows(path)


def test_cell_picks_first_match():
    row = {"mobile": "", "phone": "999"}
    assert import_utils.cell(row, "mobile", "phone") == "999"
    assert import_utils.cell(row, "nope") == ""


def test_import_customers_mixed_rows(db_session, tmp_path):
    path = _xlsx(
        tmp_path / "c.xlsx",
        ["Name", "Mobile", "City"],
        [["Ravi", "9876543210", "Bengaluru"], ["", "", ""], ["NoMobile", "", "Delhi"]],
    )
    imported, errors, warnings = customer_controller.import_customers(path)
    assert imported == 2
    assert errors == []
    assert len(warnings) == 1 and "Row 3" in warnings[0]
    names = {c["name"] for c in customer_controller.list_customers()}
    assert "Ravi" in names and "NoMobile" in names


def test_import_customers_blank_name_and_mobile(db_session, tmp_path):
    path = _xlsx(tmp_path / "blank.xlsx", ["Name", "Mobile", "City"], [["", "", "Delhi"]])
    imported, errors, warnings = customer_controller.import_customers(path)
    assert imported == 1
    assert errors == []
    assert len(warnings) == 1
    customers = customer_controller.list_customers()
    assert customers[0]["name"].startswith("Customer Row")
    assert len(customers[0]["mobile"]) == 10


def test_import_courses_and_template(db_session, tmp_path):
    template = str(tmp_path / "t.xlsx")
    ok, _ = course_controller.course_template_file(template)
    assert ok
    headers, rows = import_utils.read_table_rows(template)
    assert "name*" in headers

    path = _xlsx(
        tmp_path / "c.xlsx",
        ["Name", "Price (₹)", "GST %"],
        [["Python", "25000", "0"], ["Bad", "not-a-price", "0"]],
    )
    imported, errors = course_controller.import_courses(path)
    assert imported == 1
    assert len(errors) == 1
    assert len(course_controller.list_courses()) == 1


def test_import_expenses_unknown_category(db_session, tmp_path):
    expense_service.ensure_default_categories(db_session)
    db_session.commit()
    path = _xlsx(
        tmp_path / "e.xlsx",
        ["Category", "Amount (₹)", "Date (DD-MM-YYYY)"],
        [["Rent", "15000", "01-09-2026"], ["Nope", "100", "01-09-2026"]],
    )
    imported, errors = expense_controller.import_expenses(path)
    assert imported == 1
    assert any("unknown category" in e for e in errors)
