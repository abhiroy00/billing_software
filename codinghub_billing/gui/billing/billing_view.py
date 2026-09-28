"""Billing tab container: routes between the invoice list and the New
Invoice creation screen within the Billing sidebar section."""
from __future__ import annotations

import customtkinter as ctk

from gui.billing.billing_list_view import BillingListView
from gui.billing.invoice_form_view import InvoiceFormView


class BillingView(ctk.CTkFrame):
    def __init__(self, master, start_with_new_invoice: bool = False):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._current: ctk.CTkFrame | None = None

        if start_with_new_invoice:
            self.show_new_invoice()
        else:
            self.show_list()

    def _swap(self, widget: ctk.CTkFrame) -> None:
        if self._current is not None:
            self._current.destroy()
        self._current = widget
        widget.grid(row=0, column=0, sticky="nsew")

    def show_list(self) -> None:
        self._swap(BillingListView(self, on_new_invoice=self.show_new_invoice))

    def show_new_invoice(self) -> None:
        self._swap(InvoiceFormView(self, on_saved=self.show_list, on_cancel=self.show_list))
