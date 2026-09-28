"""Record Payment modal (Section 15/49): shows invoice amount, already
paid, current due, and a live "remaining due" / overpayment warning as the
user types."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from controllers import payment_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date


class PaymentFormModal(Modal):
    def __init__(
        self,
        master,
        invoice_id: int,
        invoice_number: str,
        grand_total: Decimal,
        paid_amount: Decimal,
        due_amount: Decimal,
        on_recorded: Callable[[dict], None] | None = None,
    ):
        super().__init__(master, title=f"Record Payment — {invoice_number}", width=440, height=440)
        self._invoice_id = invoice_id
        self._due_amount = due_amount
        self._on_recorded = on_recorded

        info = ctk.CTkFrame(self.body, fg_color=theme.colors.background, corner_radius=theme.spacing.radius)
        info.pack(fill="x", pady=(0, theme.spacing.md))
        for label, value in (
            ("Invoice Amount", format_currency(grand_total)),
            ("Already Paid", format_currency(paid_amount)),
            ("Current Due", format_currency(due_amount)),
        ):
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=theme.spacing.md, pady=(theme.spacing.sm, 0))
            ctk.CTkLabel(row, text=label, font=theme.fonts.small, text_color=theme.colors.text_secondary).pack(side="left")
            ctk.CTkLabel(row, text=value, font=theme.fonts.small_bold, text_color=theme.colors.text).pack(side="right")
        ctk.CTkLabel(info, text="", height=theme.spacing.sm).pack()

        self.amount = FormField(self.body, "Payment Amount (₹)", required=True)
        self.amount.pack(fill="x", pady=(0, theme.spacing.sm))
        self.amount.input.bind("<KeyRelease>", self._update_preview)

        row2 = ctk.CTkFrame(self.body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, theme.spacing.sm))
        row2.grid_columnconfigure((0, 1), weight=1)
        self.payment_mode = FormField(row2, "Payment Mode", widget_factory=dropdown_factory(payment_controller.PAYMENT_MODES))
        self.payment_mode.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))
        self.payment_date = FormField(row2, "Payment Date (DD-MM-YYYY)")
        self.payment_date.set(format_date(date.today()))
        self.payment_date.grid(row=0, column=1, sticky="ew")

        self.reference_number = FormField(self.body, "Reference Number (UPI/Cheque no., optional)")
        self.reference_number.pack(fill="x", pady=(0, theme.spacing.sm))

        self.preview_label = ctk.CTkLabel(self.body, text="", font=theme.fonts.small_bold, text_color=theme.colors.text_secondary)
        self.preview_label.pack(anchor="w")

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Record Payment", command=self._save).pack(side="right")

    def _update_preview(self, _event=None) -> None:
        try:
            amount = Decimal(self.amount.get().strip() or "0")
        except InvalidOperation:
            self.preview_label.configure(text="Enter a valid amount.", text_color=theme.colors.danger)
            return

        remaining = self._due_amount - amount
        if amount <= 0:
            self.preview_label.configure(text="", text_color=theme.colors.text_secondary)
        elif amount > self._due_amount:
            self.preview_label.configure(
                text=f"⚠ This exceeds the due amount by {format_currency(amount - self._due_amount)}.",
                text_color=theme.colors.danger,
            )
        else:
            self.preview_label.configure(
                text=f"Remaining due after this payment: {format_currency(remaining)}",
                text_color=theme.colors.text_secondary,
            )

    def _save(self) -> None:
        from utils import validators

        self.amount.clear_error()
        self.payment_date.clear_error()

        date_error = validators.valid_date(self.payment_date.get(), field_label="Payment date")
        amount_error = validators.valid_numeric(self.amount.get(), "Payment amount")
        if date_error:
            self.payment_date.set_error(date_error)
        if amount_error:
            self.amount.set_error(amount_error)
        if date_error or amount_error:
            return

        from utils.formatters import parse_date

        success, message, result = payment_controller.record_payment(
            invoice_id=self._invoice_id,
            amount=self.amount.get().strip(),
            payment_mode=self.payment_mode.get(),
            payment_date=parse_date(self.payment_date.get()),
            reference_number=self.reference_number.get().strip(),
        )
        if not success:
            self.amount.set_error(message)
            return

        show_toast(self.master, "Payment recorded successfully.", variant="success")
        if self._on_recorded:
            self._on_recorded(result)
        self.destroy()
