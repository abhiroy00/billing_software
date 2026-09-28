"""GST Report panel (Section 18): tax liability breakdown for a date range."""
from __future__ import annotations

import customtkinter as ctk

from controllers import report_controller
from gui.components.date_range import DateRangeFilter
from gui.components.table import DataTable
from gui.reports._shared import build_export_row, build_summary_row
from gui.theme import theme
from utils.formatters import format_currency, format_date


class GstReportPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._data: dict = {"summary": {}, "rows": []}

        self.date_range = DateRangeFilter(self, on_apply=self._load)
        self.date_range.grid(row=0, column=0, sticky="w", pady=(0, theme.spacing.md))

        self.summary_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_holder.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))

        export_row = build_export_row(self, lambda: self._data, report_controller.export_gst_report, "GST Report")
        export_row.grid(row=2, column=0, sticky="w", pady=(0, theme.spacing.sm))

        self.table = DataTable(
            self,
            columns=[
                ("invoice_number", "Invoice No", 110, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("customer_name", "Customer", 140, "w"),
                ("customer_gstin", "GSTIN", 110, "w"),
                ("taxable_amount", "Taxable", 100, "e"),
                ("cgst_total", "CGST", 90, "e"),
                ("sgst_total", "SGST", 90, "e"),
                ("igst_total", "IGST", 90, "e"),
                ("grand_total", "Total", 100, "e"),
            ],
            empty_message="No taxed invoices in this period",
        )
        self.table.grid(row=3, column=0, sticky="nsew")
        self.table.configure(height=320)

        self.date_range.trigger_initial_load()

    def _load(self, date_from, date_to) -> None:
        self._data = report_controller.gst_report(date_from, date_to)
        self._render_summary()
        self._render_table()

    def _render_summary(self) -> None:
        for child in self.summary_holder.winfo_children():
            child.destroy()
        s = self._data["summary"]
        cards = [
            ("TAXABLE VALUE", format_currency(s.get("taxable_total", 0)), theme.colors.info),
            ("CGST", format_currency(s.get("cgst_total", 0)), theme.colors.primary),
            ("SGST", format_currency(s.get("sgst_total", 0)), theme.colors.primary),
            ("IGST", format_currency(s.get("igst_total", 0)), theme.colors.primary),
            ("TOTAL TAX", format_currency(s.get("total_tax", 0)), theme.colors.success),
        ]
        build_summary_row(self.summary_holder, cards).pack(fill="x")

    def _render_table(self) -> None:
        rows = [
            {
                **r,
                "invoice_date": format_date(r["invoice_date"]),
                "taxable_amount": format_currency(r["taxable_amount"]),
                "cgst_total": format_currency(r["cgst_total"]),
                "sgst_total": format_currency(r["sgst_total"]),
                "igst_total": format_currency(r["igst_total"]),
                "grand_total": format_currency(r["grand_total"]),
            }
            for r in self._data["rows"]
        ]
        self.table.set_rows(rows)
