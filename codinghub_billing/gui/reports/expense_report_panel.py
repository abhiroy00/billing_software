"""Expense Report panel (Section 18): expenses over a date range with a
by-category breakdown."""
from __future__ import annotations

import customtkinter as ctk

from controllers import report_controller
from gui.components.date_range import DateRangeFilter
from gui.components.table import DataTable
from gui.reports._shared import build_export_row, build_summary_row
from gui.theme import theme
from utils.formatters import format_currency, format_date


class ExpenseReportPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self._data: dict = {"summary": {}, "rows": []}

        self.date_range = DateRangeFilter(self, on_apply=self._load)
        self.date_range.grid(row=0, column=0, sticky="w", pady=(0, theme.spacing.md))

        self.summary_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_holder.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))

        self.category_breakdown_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.category_breakdown_holder.grid(row=2, column=0, sticky="ew", pady=(0, theme.spacing.md))

        export_row = build_export_row(self, lambda: self._data, report_controller.export_expense_report, "Expense Report")
        export_row.grid(row=3, column=0, sticky="w", pady=(0, theme.spacing.sm))

        self.table = DataTable(
            self,
            columns=[
                ("expense_date", "Date", 90, "w"),
                ("category_name", "Category", 120, "w"),
                ("description", "Description", 180, "w"),
                ("vendor", "Vendor", 130, "w"),
                ("amount", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
            ],
            empty_message="No expenses in this period",
        )
        self.table.grid(row=4, column=0, sticky="nsew")
        self.table.configure(height=320)

        self.date_range.trigger_initial_load()

    def _load(self, date_from, date_to) -> None:
        self._data = report_controller.expense_report(date_from, date_to)
        self._render_summary()
        self._render_table()

    def _render_summary(self) -> None:
        for child in self.summary_holder.winfo_children():
            child.destroy()
        for child in self.category_breakdown_holder.winfo_children():
            child.destroy()

        s = self._data["summary"]
        cards = [
            ("TOTAL EXPENSES", format_currency(s.get("total_expenses", 0)), theme.colors.danger),
            ("ENTRIES", str(s.get("total_count", 0)), theme.colors.info),
        ]
        build_summary_row(self.summary_holder, cards).pack(fill="x")

        by_category = s.get("by_category", {})
        if by_category:
            ctk.CTkLabel(
                self.category_breakdown_holder, text="By Category:", font=theme.fonts.small_bold,
                text_color=theme.colors.text_secondary,
            ).pack(side="left", padx=(0, theme.spacing.sm))
            for name, amount in sorted(by_category.items(), key=lambda kv: -kv[1]):
                ctk.CTkLabel(
                    self.category_breakdown_holder, text=f"{name}: {format_currency(amount)}",
                    font=theme.fonts.small, text_color=theme.colors.text,
                    fg_color=theme.colors.background, corner_radius=theme.spacing.radius,
                ).pack(side="left", padx=(0, theme.spacing.sm), ipadx=6, ipady=2)

    def _render_table(self) -> None:
        rows = [
            {**r, "expense_date": format_date(r["expense_date"]), "amount": format_currency(r["amount"])}
            for r in self._data["rows"]
        ]
        self.table.set_rows(rows)
