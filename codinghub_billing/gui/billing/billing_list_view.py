"""Invoice list screen (Section 13): search, filter by status, row actions
(view / record payment / cancel)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import invoice_controller
from gui.billing.invoice_detail_view import InvoiceDetailModal
from gui.components.buttons import PrimaryButton
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date

STATUS_FILTERS = ["All", "PENDING", "PARTIAL", "PAID", "CANCELLED"]


class BillingListView(ctk.CTkFrame):
    def __init__(self, master, on_new_invoice: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self._on_new_invoice = on_new_invoice
        self._query = ""
        self._status_filter = "All"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("invoice_number", "Invoice No", 120, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("customer_name", "Customer", 170, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("paid_amount", "Paid", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            on_row_double_click=self._open_detail,
            on_row_context_menu=self._row_menu,
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={
                "paid": theme.colors.success,
                "partial": theme.colors.warning,
                "pending": theme.colors.danger,
                "cancelled": theme.colors.text_secondary,
            },
            empty_message="No invoices found",
            empty_action_label="Create Invoice",
            on_empty_action=self._on_new_invoice,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.lg)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search by invoice no. or customer...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        self.status_menu = ctk.CTkOptionMenu(
            bar, values=STATUS_FILTERS, command=self._on_status_change, width=140,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.status_menu.set("All")
        self.status_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        PrimaryButton(bar, text="New Invoice", icon="+", command=self._on_new_invoice).grid(row=0, column=2)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_status_change(self, value: str) -> None:
        self._status_filter = value
        self._load()

    def _load(self) -> None:
        rows = invoice_controller.list_invoices(query=self._query, status=self._status_filter)
        display_rows = [
            {
                **row,
                "invoice_date": format_date(row["invoice_date"]),
                "grand_total": format_currency(row["grand_total"]),
                "paid_amount": format_currency(row["paid_amount"]),
                "due_amount": format_currency(row["due_amount"]),
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)

    def _open_detail(self, row: dict) -> None:
        InvoiceDetailModal(self, invoice_id=row["id"], on_changed=self._load)

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        return [("View Invoice", lambda: self._open_detail(row))]

    def refresh(self) -> None:
        self._load()
