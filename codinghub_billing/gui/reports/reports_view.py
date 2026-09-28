"""Reports module container (Section 18): a report-type selector plus the
active report panel, following the same filter -> summary -> table ->
export layout throughout (Section 50)."""
from __future__ import annotations

import customtkinter as ctk

from gui.reports.expense_report_panel import ExpenseReportPanel
from gui.reports.gst_report_panel import GstReportPanel
from gui.reports.payment_report_panel import PaymentReportPanel
from gui.reports.pending_payments_panel import PendingPaymentsPanel
from gui.reports.profit_summary_panel import ProfitSummaryPanel
from gui.reports.sales_report_panel import SalesReportPanel
from gui.theme import theme

REPORT_PANELS: dict[str, type[ctk.CTkFrame]] = {
    "Sales": SalesReportPanel,
    "Payments": PaymentReportPanel,
    "Pending Dues": PendingPaymentsPanel,
    "GST": GstReportPanel,
    "Expenses": ExpenseReportPanel,
    "Profit Summary": ProfitSummaryPanel,
}


class ReportsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._current: ctk.CTkFrame | None = None

        self.selector = ctk.CTkSegmentedButton(
            self, values=list(REPORT_PANELS.keys()), command=self._show, font=theme.fonts.body
        )
        self.selector.grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=theme.spacing.lg)

        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        self.content.grid_columnconfigure(0, weight=1)

        first_key = next(iter(REPORT_PANELS))
        self.selector.set(first_key)
        self._show(first_key)

    def _show(self, key: str) -> None:
        if self._current is not None:
            self._current.destroy()
        panel_cls = REPORT_PANELS[key]
        self._current = panel_cls(self.content)
        self._current.grid(row=0, column=0, sticky="nsew")
