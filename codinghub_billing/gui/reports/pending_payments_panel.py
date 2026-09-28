"""Pending Payments Report panel (Section 18): a live snapshot of every
invoice with an outstanding balance, not a date-ranged report."""
from __future__ import annotations

import customtkinter as ctk

from controllers import report_controller
from gui.components.buttons import SecondaryButton
from gui.components.table import DataTable
from gui.reports._shared import build_export_row, build_summary_row
from gui.theme import theme
from utils.formatters import format_currency, format_date


class PendingPaymentsPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._data: dict = {"summary": {}, "rows": []}

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="w", pady=(0, theme.spacing.md))
        SecondaryButton(toolbar, text="Refresh", icon="\U0001F504", command=self._load).pack(side="left")

        self.summary_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_holder.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))

        export_row = build_export_row(
            self, lambda: self._data, report_controller.export_pending_payments_report, "Pending Payments"
        )
        export_row.grid(row=2, column=0, sticky="w", pady=(0, theme.spacing.sm))

        self.table = DataTable(
            self,
            columns=[
                ("invoice_number", "Invoice No", 110, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("customer_name", "Customer", 150, "w"),
                ("customer_mobile", "Mobile", 110, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={"partial": theme.colors.warning, "pending": theme.colors.danger},
            empty_message="No pending payments — everything is settled",
        )
        self.table.grid(row=3, column=0, sticky="nsew")
        self.table.configure(height=320)

        self._load()

    def _load(self) -> None:
        self._data = report_controller.pending_payments_report()
        self._render_summary()
        self._render_table()

    def _render_summary(self) -> None:
        for child in self.summary_holder.winfo_children():
            child.destroy()
        s = self._data["summary"]
        cards = [
            ("TOTAL OUTSTANDING", format_currency(s.get("total_outstanding", 0)), theme.colors.danger),
            ("PENDING INVOICES", str(s.get("total_pending_invoices", 0)), theme.colors.warning),
            ("CUSTOMERS WITH DUES", str(s.get("customers_with_dues", 0)), theme.colors.info),
        ]
        build_summary_row(self.summary_holder, cards).pack(fill="x")

    def _render_table(self) -> None:
        rows = [
            {**r, "invoice_date": format_date(r["invoice_date"]), "grand_total": format_currency(r["grand_total"]),
             "due_amount": format_currency(r["due_amount"])}
            for r in self._data["rows"]
        ]
        self.table.set_rows(rows)
