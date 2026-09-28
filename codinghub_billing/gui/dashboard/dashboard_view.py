"""Dashboard (Section 10): real DB-backed KPIs, recent activity, top
courses, monthly revenue chart, and payment-mode breakdown."""
from __future__ import annotations

from decimal import Decimal

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from controllers import dashboard_controller
from gui.components.cards import Card, StatCard
from gui.components.empty_state import EmptyState
from gui.components.table import DataTable
from gui.theme import theme
from services.dashboard_service import DashboardOverview
from utils.formatters import format_currency, format_date

_RANGE_LABELS = [("today", "Today"), ("week", "This Week"), ("month", "This Month"), ("year", "This Year")]


class DashboardView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._range_key = "month"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        self.scroll.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        self._load()

    # --------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.lg)

        self.segment = ctk.CTkSegmentedButton(
            bar,
            values=[label for _key, label in _RANGE_LABELS],
            command=self._on_range_change,
            font=theme.fonts.body,
        )
        self.segment.set("This Month")
        self.segment.pack(side="left")

    def _on_range_change(self, label: str) -> None:
        self._range_key = next(key for key, lbl in _RANGE_LABELS if lbl == label)
        self._load()

    # ------------------------------------------------------------------ data
    def _load(self) -> None:
        overview = dashboard_controller.get_overview(self._range_key)
        for child in self.scroll.winfo_children():
            child.destroy()
        self._render(overview)

    def _render(self, overview: DashboardOverview) -> None:
        kpis = overview.kpis

        StatCard(self.scroll, "TODAY'S REVENUE", format_currency(kpis.today_revenue), accent=theme.colors.success).grid(
            row=0, column=0, sticky="nsew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.lg)
        )
        StatCard(self.scroll, "THIS MONTH REVENUE", format_currency(kpis.month_revenue), accent=theme.colors.primary).grid(
            row=0, column=1, sticky="nsew", padx=theme.spacing.sm, pady=(0, theme.spacing.lg)
        )
        StatCard(self.scroll, "PENDING PAYMENTS", format_currency(kpis.pending_payments), accent=theme.colors.danger).grid(
            row=0, column=2, sticky="nsew", padx=theme.spacing.sm, pady=(0, theme.spacing.lg)
        )
        StatCard(self.scroll, "TOTAL CUSTOMERS", str(kpis.total_customers), accent=theme.colors.info).grid(
            row=0, column=3, sticky="nsew", padx=(theme.spacing.sm, 0), pady=(0, theme.spacing.lg)
        )

        left = ctk.CTkFrame(self.scroll, fg_color="transparent")
        left.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(0, theme.spacing.sm))
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self.scroll, fg_color="transparent")
        right.grid(row=1, column=3, sticky="nsew", padx=(theme.spacing.sm, 0))
        right.grid_columnconfigure(0, weight=1)

        self._build_revenue_chart(left, overview.monthly_revenue)
        self._build_recent_invoices(left, overview.recent_invoices)

        self._build_payment_breakdown(right, overview.payment_mode_breakdown)
        self._build_top_courses(right, overview.top_courses)
        self._build_recent_payments(right, overview.recent_payments)
        self._build_recent_expenses(right, overview.recent_expenses)

    # ---------------------------------------------------------------- pieces
    def _section_card(self, parent, title: str, row: int) -> Card:
        card = Card(parent)
        card.grid(row=row, column=0, sticky="nsew", pady=(0, theme.spacing.lg))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=theme.fonts.section_heading, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        return card

    def _build_revenue_chart(self, parent, monthly_revenue: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "Monthly Revenue", row=0)
        if not monthly_revenue:
            EmptyState(card, message="No revenue collected in this period yet.", icon="\U0001F4C8").grid(
                row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md)
            )
            return

        months = [m for m, _ in monthly_revenue]
        totals = [float(v) for _, v in monthly_revenue]

        figure = Figure(figsize=(5, 2.6), dpi=100)
        axis = figure.add_subplot(111)
        axis.bar(months, totals, color=theme.colors.primary, width=0.5)
        axis.set_facecolor(theme.colors.card)
        figure.patch.set_facecolor(theme.colors.card)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
        axis.tick_params(labelsize=8, colors=theme.colors.text_secondary)
        figure.tight_layout()

        canvas = FigureCanvasTkAgg(figure, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))

    def _build_recent_invoices(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "Recent Invoices", row=1)
        table_rows = [
            {
                "id": r["id"],
                "invoice_number": r["invoice_number"],
                "invoice_date": format_date(r["invoice_date"]),
                "grand_total": format_currency(r["grand_total"]),
                "due_amount": format_currency(r["due_amount"]),
                "status": r["status"],
            }
            for r in rows
        ]
        table = DataTable(
            card,
            columns=[
                ("invoice_number", "Invoice No", 110, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            empty_message="No invoices found",
        )
        table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=220)
        table.set_rows(table_rows)

    def _build_payment_breakdown(self, parent, rows: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "Payment Mode Breakdown", row=0)
        if not rows:
            EmptyState(card, message="No payments recorded yet.", icon="\U0001F4B3").grid(
                row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md)
            )
            return

        max_amount = max(float(v) for _, v in rows) or 1
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        body.grid_columnconfigure(0, weight=1)

        for i, (mode, amount) in enumerate(rows):
            ctk.CTkLabel(body, text=f"{mode}", font=theme.fonts.small_bold, text_color=theme.colors.text, anchor="w").grid(
                row=i * 2, column=0, sticky="w", pady=(theme.spacing.xs, 0)
            )
            ctk.CTkLabel(
                body, text=format_currency(amount), font=theme.fonts.small, text_color=theme.colors.text_secondary
            ).grid(row=i * 2, column=1, sticky="e")
            bar = ctk.CTkProgressBar(body, height=8, progress_color=theme.colors.primary)
            bar.set(float(amount) / max_amount)
            bar.grid(row=i * 2 + 1, column=0, columnspan=2, sticky="ew", pady=(2, theme.spacing.sm))

    def _build_top_courses(self, parent, rows: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "Top Courses", row=1)
        table_rows = [{"id": i, "name": name, "revenue": format_currency(amount)} for i, (name, amount) in enumerate(rows)]
        table = DataTable(
            card,
            columns=[("name", "Course/Product", 150, "w"), ("revenue", "Revenue", 100, "e")],
            empty_message="No course sales in this period yet",
        )
        table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)

    def _build_recent_payments(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "Recent Payments", row=2)
        table_rows = [
            {
                "id": r["id"],
                "payment_date": format_date(r["payment_date"]),
                "amount": format_currency(r["amount"]),
                "payment_mode": r["payment_mode"],
            }
            for r in rows
        ]
        table = DataTable(
            card,
            columns=[
                ("payment_date", "Date", 90, "w"),
                ("amount", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
            ],
            empty_message="No payments found",
        )
        table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)

    def _build_recent_expenses(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "Recent Expenses", row=3)
        table_rows = [
            {
                "id": r["id"],
                "expense_date": format_date(r["expense_date"]),
                "description": r["description"] or r["vendor"],
                "amount": format_currency(r["amount"]),
            }
            for r in rows
        ]
        table = DataTable(
            card,
            columns=[
                ("expense_date", "Date", 90, "w"),
                ("description", "Description", 140, "w"),
                ("amount", "Amount", 100, "e"),
            ],
            empty_message="No expenses found",
        )
        table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)
