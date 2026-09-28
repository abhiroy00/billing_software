"""Profit Summary panel (Section 18): revenue collected vs expenses for a
date range. No export — it's a derived snapshot, not a row-level report."""
from __future__ import annotations

import customtkinter as ctk

from controllers import report_controller
from gui.components.cards import Card
from gui.components.date_range import DateRangeFilter
from gui.reports._shared import build_summary_row
from gui.theme import theme
from utils.formatters import format_currency


class ProfitSummaryPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        self.date_range = DateRangeFilter(self, on_apply=self._load)
        self.date_range.grid(row=0, column=0, sticky="w", pady=(0, theme.spacing.md))

        self.summary_holder = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_holder.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))

        self.net_profit_card = Card(self)
        self.net_profit_card.grid(row=2, column=0, sticky="ew")
        self.net_profit_card.configure(fg_color=theme.colors.secondary)
        self.net_profit_emoji = ctk.CTkLabel(
            self.net_profit_card, text="📈", font=("Segoe UI", 44), text_color=theme.colors.white
        )
        self.net_profit_emoji.pack(pady=(theme.spacing.lg, 0))
        self.net_profit_label = ctk.CTkLabel(
            self.net_profit_card, text="", font=theme.fonts.page_heading, text_color=theme.colors.white
        )
        self.net_profit_label.pack()
        self.net_profit_sub = ctk.CTkLabel(
            self.net_profit_card, text="", font=theme.fonts.body, text_color="#94A3B8"
        )
        self.net_profit_sub.pack(pady=(4, theme.spacing.lg))

        self.date_range.trigger_initial_load()

    def _load(self, date_from, date_to) -> None:
        data = report_controller.profit_summary(date_from, date_to)
        summary = data["summary"]

        for child in self.summary_holder.winfo_children():
            child.destroy()
        cards = [
            ("INVOICED SALES", format_currency(summary.get("invoiced_sales", 0)), theme.colors.info),
            ("REVENUE COLLECTED", format_currency(summary.get("revenue_collected", 0)), theme.colors.success),
            ("TOTAL EXPENSES", format_currency(summary.get("total_expenses", 0)), theme.colors.danger),
        ]
        build_summary_row(self.summary_holder, cards).pack(fill="x")

        net_profit = summary.get("net_profit", 0)
        is_profit = net_profit >= 0
        color = theme.colors.success if is_profit else theme.colors.danger
        label = "Net Profit" if is_profit else "Net Loss"
        self.net_profit_emoji.configure(text="📈" if is_profit else "📉")
        self.net_profit_label.configure(text=f"{label}:  {format_currency(abs(net_profit))}", text_color=color)
        collected = summary.get("revenue_collected", 0) or 0
        try:
            margin = (float(net_profit) / float(collected) * 100) if float(collected) > 0 else 0.0
            self.net_profit_sub.configure(text=f"Profit margin {margin:.1f}% on collected revenue")
        except Exception:
            self.net_profit_sub.configure(text="")
