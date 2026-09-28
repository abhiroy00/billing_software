"""Expense list screen (Section 16): search, filter by category/mode,
export, and row actions (edit/delete)."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import expense_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.expenses.expense_form_modal import ExpenseFormModal
from gui.theme import theme
from utils.formatters import format_currency, format_date

CATEGORY_FILTER_ALL = "All Categories"


class ExpenseListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._category_id: int | None = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._categories = expense_controller.list_categories()
        self._category_id_by_name = {c["name"]: c["id"] for c in self._categories}

        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("expense_date", "Date", 90, "w"),
                ("category_name", "Category", 120, "w"),
                ("description", "Description", 190, "w"),
                ("vendor", "Vendor", 130, "w"),
                ("amount_display", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
            ],
            on_row_double_click=self._open_edit_form,
            on_row_context_menu=self._row_menu,
            empty_message="No expenses found",
            empty_action_label="Add Expense",
            on_empty_action=self._open_add_form,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.lg)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search by description or vendor...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        category_values = [CATEGORY_FILTER_ALL] + [c["name"] for c in self._categories]
        self.category_menu = ctk.CTkOptionMenu(
            bar, values=category_values, command=self._on_category_change, width=160,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.category_menu.set(CATEGORY_FILTER_ALL)
        self.category_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        SecondaryButton(bar, text="Export", icon="\U0001F4E4", command=self._export).grid(
            row=0, column=2, padx=(0, theme.spacing.sm)
        )
        PrimaryButton(bar, text="New Expense", icon="+", command=self._open_add_form).grid(row=0, column=3)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_category_change(self, value: str) -> None:
        self._category_id = None if value == CATEGORY_FILTER_ALL else self._category_id_by_name.get(value)
        self._load()

    def _load(self) -> None:
        rows = expense_controller.list_expenses(query=self._query, category_id=self._category_id)
        display_rows = [
            {
                **row,
                "expense_date": format_date(row["expense_date"]),
                "amount_display": format_currency(row["amount"]),
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)

    def _open_add_form(self) -> None:
        ExpenseFormModal(self, on_saved=lambda _e: self._load())

    def _open_edit_form(self, row: dict) -> None:
        ExpenseFormModal(self, expense_id=row["id"], on_saved=lambda _e: self._load())

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        return [
            ("Edit", lambda: self._open_edit_form(row)),
            ("Delete", lambda: self._confirm_delete(row)),
        ]

    def _confirm_delete(self, row: dict) -> None:
        def do_delete():
            success, message = expense_controller.delete_expense(row["id"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, "Expense deleted.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Expense",
            message=f"Are you sure you want to delete this {row['category_name']} expense of {format_currency(row['amount'])}?",
            on_confirm=do_delete,
        )

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export expenses", defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not path:
            return
        success, message = expense_controller.export_expenses_to_excel(path, query=self._query, category_id=self._category_id)
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Expenses exported successfully.", variant="success")
        else:
            show_toast(root, message, variant="error")
