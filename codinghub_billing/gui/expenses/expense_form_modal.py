"""Add/Edit Expense modal (Section 16)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from controllers import expense_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme
from utils import validators
from utils.formatters import format_date, parse_date


class ExpenseFormModal(Modal):
    def __init__(self, master, expense_id: int | None = None, on_saved: Callable[[dict], None] | None = None):
        title = "Edit Expense" if expense_id else "New Expense"
        super().__init__(master, title=title, width=560, height=600, resizable=True, scrollable=True)
        self._expense_id = expense_id
        self._on_saved = on_saved
        self._attachment_path: str | None = None

        categories = expense_controller.list_categories()
        self._category_name_to_id = {c["name"]: c["id"] for c in categories}
        category_values = list(self._category_name_to_id.keys()) or ["Other"]

        self.scroll_body.grid_columnconfigure(0, weight=1)
        self.scroll_body.grid_columnconfigure(1, weight=1)

        self._section_label("💰 Expense Details", 0)
        self.category = self._field("Category", 1, 0, required=True, widget_factory=dropdown_factory(category_values))
        self.amount = self._field("Amount (₹)", 1, 1, required=True)
        self.expense_date = self._field("Expense Date (DD-MM-YYYY)", 2, 0)
        self.expense_date.set(format_date(date.today()))
        self.payment_mode = self._field(
            "Payment Mode", 2, 1, widget_factory=dropdown_factory(expense_controller.PAYMENT_MODES)
        )
        self._section_label("📝 Details & Receipt", 3)
        self.vendor = self._field("Vendor", 4, 0, colspan=2)
        self.description = self._field("Description", 5, 0, colspan=2)
        self.notes = self._field(
            "Notes", 6, 0, colspan=2, widget_factory=lambda m: ctk.CTkTextbox(m, height=60, font=theme.fonts.body)
        )

        attach_row = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        attach_row.grid(row=7, column=0, columnspan=2, sticky="w", pady=(theme.spacing.sm, 0))
        self.attachment_status = ctk.CTkLabel(
            attach_row, text="No attachment", font=theme.fonts.small, text_color=theme.colors.text_secondary
        )
        self.attachment_status.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(attach_row, text="Attach File", icon="\U0001F4CE", command=self._pick_attachment).pack(side="left")
        self.view_attachment_btn = SecondaryButton(attach_row, text="View", command=self._view_attachment)

        if expense_id:
            self._load_existing(expense_id)

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Save Expense", command=self._save).pack(side="right")

    def _section_label(self, text: str, row: int) -> None:
        ctk.CTkLabel(
            self.scroll_body, text=text, font=theme.fonts.card_title,
            text_color=theme.colors.primary, anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(theme.spacing.sm, theme.spacing.xs))

    def _field(self, label, row, col, required=False, colspan=1, widget_factory=None):
        field = FormField(self.scroll_body, label, required=required, widget_factory=widget_factory)
        field.grid(
            row=row, column=col, columnspan=colspan, sticky="ew",
            padx=(0, theme.spacing.sm) if col == 0 and colspan == 1 else 0,
            pady=(0, theme.spacing.sm),
        )
        return field

    def _pick_attachment(self) -> None:
        path = filedialog.askopenfilename(title="Select attachment (receipt, invoice, etc.)")
        if not path:
            return
        success, message, saved_path = expense_controller.attach_file(path)
        if not success:
            show_toast(self.master, message, variant="error")
            return
        self._attachment_path = saved_path
        self.attachment_status.configure(text=Path(path).name, text_color=theme.colors.success)
        self.view_attachment_btn.pack(side="left", padx=(theme.spacing.sm, 0))

    def _view_attachment(self) -> None:
        if not self._attachment_path:
            return
        success, message = expense_controller.open_attachment(self._attachment_path)
        if not success:
            show_toast(self.master, message, variant="error")

    def _load_existing(self, expense_id: int) -> None:
        expense = expense_controller.get_expense(expense_id)
        if not expense:
            return
        self.category.set(expense["category_name"])
        self.amount.set(str(expense["amount"]))
        self.expense_date.set(format_date(expense["expense_date"]))
        self.payment_mode.set(expense["payment_mode"])
        self.vendor.set(expense["vendor"] or "")
        self.description.set(expense["description"] or "")
        self.notes.set(expense["notes"] or "")
        if expense.get("attachment_path"):
            self._attachment_path = expense["attachment_path"]
            self.attachment_status.configure(text=Path(expense["attachment_path"]).name, text_color=theme.colors.success)
            self.view_attachment_btn.pack(side="left", padx=(theme.spacing.sm, 0))

    def _save(self) -> None:
        self.amount.clear_error()
        self.expense_date.clear_error()

        date_error = validators.valid_date(self.expense_date.get(), field_label="Expense date")
        amount_error = validators.valid_numeric(self.amount.get(), "Amount")
        if date_error:
            self.expense_date.set_error(date_error)
        if amount_error:
            self.amount.set_error(amount_error)
        if date_error or amount_error:
            return

        category_name = self.category.get()
        data = {
            "category_id": self._category_name_to_id.get(category_name),
            "description": self.description.get().strip(),
            "amount": self.amount.get().strip(),
            "expense_date": parse_date(self.expense_date.get()),
            "payment_mode": self.payment_mode.get(),
            "vendor": self.vendor.get().strip(),
            "notes": self.notes.get().strip(),
            "attachment_path": self._attachment_path,
        }

        if self._expense_id:
            success, message, expense = expense_controller.update_expense(self._expense_id, data)
        else:
            success, message, expense = expense_controller.create_expense(data)

        if not success:
            show_toast(self.master, message, variant="error")
            return

        show_toast(self.master, "Expense saved successfully.", variant="success")
        if self._on_saved:
            self._on_saved(expense)
        self.destroy()
