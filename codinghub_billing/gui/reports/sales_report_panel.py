"""Sales Report panel (Section 18)."""
from __future__ import annotations

import customtkinter as ctk

from controllers import report_controller
from gui.components.date_range import DateRangeFilter
from gui.components.table import DataTable
from gui.reports._shared import build_export_row, build_summary_row
from gui.theme import theme
from utils.formatters import format_currency, format_date


class SalesReportPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._data: dict = {"summary": {}, "rows": []}

        self.date_range = DateRangeFilter(self, on_apply=self._load)
        self.date_range.grid(row=0, column=0, sticky="w", pady=(0, theme.spacing.md))

        self.summary_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_holder.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))

        export_row = build_export_row(self, lambda: self._data, report_controller.export_sales_report, "Sales Report")
        export_row.grid(row=2, column=0, sticky="w", pady=(0, theme.spacing.sm))

        self.table = DataTable(
            self,
            columns=[
                ("invoice_number", "Invoice No", 110, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("customer_name", "Customer", 160, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("paid_amount", "Paid", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={
                "paid": theme.colors.success, "partial": theme.colors.warning,
                "pending": theme.colors.danger, "cancelled": theme.colors.text_secondary,
            },
            empty_message="No sales in this period",
        )
        self.table.grid(row=3, column=0, sticky="nsew")
        self.table.configure(height=320)

        self.date_range.trigger_initial_load()

    def _load(self, date_from, date_to) -> None:
        self._data = report_controller.sales_report(date_from, date_to)
        self._render_summary()
        self._render_table()

    def _render_summary(self) -> None:
        for child in self.summary_holder.winfo_children():
            child.destroy()
        s = self._data["summary"]
        cards = [
            ("TOTAL INVOICES", str(s.get("total_invoices", 0)), theme.colors.info),
            ("TOTAL SALES", format_currency(s.get("total_sales", 0)), theme.colors.primary),
            ("COLLECTED", format_currency(s.get("total_collected", 0)), theme.colors.success),
            ("OUTSTANDING", format_currency(s.get("total_due", 0)), theme.colors.danger),
        ]
        build_summary_row(self.summary_holder, cards).pack(fill="x")

    def _render_table(self) -> None:
        rows = [
            {
                **r,
                "invoice_date": format_date(r["invoice_date"]),
                "grand_total": format_currency(r["grand_total"]),
                "paid_amount": format_currency(r["paid_amount"]),
                "due_amount": format_currency(r["due_amount"]),
            }
            for r in self._data["rows"]
        ]
        self.table.set_rows(rows)
