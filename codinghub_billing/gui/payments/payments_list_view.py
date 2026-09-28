"""Payments list screen (Section 15): every payment ever recorded, across
all invoices, searchable/filterable and exportable."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import payment_controller
from gui.billing.invoice_detail_view import InvoiceDetailModal
from gui.components.buttons import SecondaryButton
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date

MODE_FILTERS = ["All"] + payment_controller.PAYMENT_MODES


class PaymentsListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._mode_filter = "All"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("payment_date", "Date", 90, "w"),
                ("invoice_number", "Invoice No", 120, "w"),
                ("customer_name", "Customer", 170, "w"),
                ("amount", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
                ("reference_number", "Reference", 140, "w"),
            ],
            on_row_double_click=self._open_invoice,
            empty_message="No payments recorded yet",
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.lg)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search by invoice no. or customer...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        self.mode_menu = ctk.CTkOptionMenu(
            bar, values=MODE_FILTERS, command=self._on_mode_change, width=150,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.mode_menu.set("All")
        self.mode_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        SecondaryButton(bar, text="Export", icon="\U0001F4E4", command=self._export).grid(row=0, column=2)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_mode_change(self, value: str) -> None:
        self._mode_filter = value
        self._load()

    def _load(self) -> None:
        rows = payment_controller.list_payments(query=self._query, payment_mode=self._mode_filter)
        display_rows = [
            {
                **row,
                "payment_date": format_date(row["payment_date"]),
                "amount": format_currency(row["amount"]),
                "reference_number": row["reference_number"] or "—",
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)

    def _open_invoice(self, row: dict) -> None:
        InvoiceDetailModal(self, invoice_id=row["invoice_id"], on_changed=self._load)

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export payments", defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not path:
            return
        success, message = payment_controller.export_payments_to_excel(path, query=self._query, payment_mode=self._mode_filter)
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Payments exported successfully.", variant="success")
        else:
            show_toast(root, message, variant="error")
