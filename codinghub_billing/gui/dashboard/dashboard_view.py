"""Dashboard (Section 10): real DB-backed KPIs, hero quick-actions,
collection health, recent activity, top courses, monthly revenue chart,
and payment-mode breakdown."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from controllers import dashboard_controller
from gui.components.buttons import PrimaryButton
from gui.components.cards import Card, StatCard
from gui.components.empty_state import EmptyState
from gui.components.table import DataTable
from gui.theme import theme
from services.dashboard_service import DashboardOverview
from utils.formatters import format_currency, format_date

_RANGE_LABELS = [("today", "Today"), ("week", "This Week"), ("month", "This Month"), ("year", "This Year")]

_MODE_ICONS = {"Cash": "💵", "UPI": "📱", "Card": "💳", "Bank": "🏦", "Bank Transfer": "🏦", "Cheque": "🧾", "Other": "🧾"}
_RANK_MEDALS = ("🥇", "🥈", "🥉", "4.", "5.")


class DashboardView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_new_invoice: Callable[[], None] | None = None,
        on_add_customer: Callable[[], None] | None = None,
        on_view_reports: Callable[[], None] | None = None,
    ):
        super().__init__(master, fg_color="transparent")
        self._range_key = "month"
        self._on_new_invoice = on_new_invoice
        self._on_add_customer = on_add_customer
        self._on_view_reports = on_view_reports

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
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bar, text=datetime.now().strftime("%A, %d %B %Y").upper(),
            font=("Segoe UI", 10, "bold"), text_color=theme.colors.primary, anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            bar, text=f"{self._greeting()} 👋", font=theme.fonts.page_heading, text_color=theme.colors.text, anchor="w"
        ).grid(row=1, column=0, sticky="w")

        self.segment = ctk.CTkSegmentedButton(
            bar,
            values=[label for _key, label in _RANGE_LABELS],
            command=self._on_range_change,
            font=theme.fonts.body,
        )
        self.segment.set("This Month")
        self.segment.grid(row=0, column=1, rowspan=2, sticky="e")

    @staticmethod
    def _greeting() -> str:
        try:
            hour = datetime.now().hour
            if hour < 12:
                return "Good morning"
            if hour < 17:
                return "Good afternoon"
            return "Good evening"
        except Exception:
            return "Welcome back"

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

        self._build_hero(kpis, overview.outstanding_dues)

        cards = [
            StatCard(self.scroll, "💰 TODAY'S REVENUE", format_currency(kpis.today_revenue), accent=theme.colors.success, icon="💰"),
            StatCard(self.scroll, "📈 MONTH REVENUE", format_currency(kpis.month_revenue), accent=theme.colors.primary, icon="📈"),
            StatCard(self.scroll, "⏳ PENDING DUES", format_currency(kpis.pending_payments), accent=theme.colors.danger, icon="⏳",
                     trend="✓ All clear" if kpis.pending_payments == 0 else "● Action needed"),
            StatCard(self.scroll, "👥 TOTAL CUSTOMERS", str(kpis.total_customers), accent=theme.colors.info, icon="👥"),
        ]
        pads = [(0, theme.spacing.sm), theme.spacing.sm, theme.spacing.sm, (theme.spacing.sm, 0)]
        for i, card in enumerate(cards):
            pad = pads[i]
            padx = (pad, theme.spacing.sm) if isinstance(pad, int) else pad
            card.grid(row=1, column=i, sticky="nsew", padx=padx, pady=(0, theme.spacing.lg))

        try:
            from gui.components.animations import stagger_in

            stagger_in(cards)
        except Exception:
            pass

        left = ctk.CTkFrame(self.scroll, fg_color="transparent")
        left.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=(0, theme.spacing.sm))
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self.scroll, fg_color="transparent")
        right.grid(row=2, column=3, sticky="nsew", padx=(theme.spacing.sm, 0))
        right.grid_columnconfigure(0, weight=1)

        self._build_revenue_chart(left, overview.monthly_revenue)
        self._build_recent_invoices(left, overview.recent_invoices)

        self._build_payment_breakdown(right, overview.payment_mode_breakdown)
        self._build_top_courses(right, overview.top_courses)
        self._build_recent_payments(right, overview.recent_payments)
        self._build_recent_expenses(right, overview.recent_expenses)

    # ------------------------------------------------------------------- hero
    def _build_hero(self, kpis, outstanding: Decimal) -> None:
        hero = ctk.CTkFrame(self.scroll, fg_color=theme.colors.secondary, corner_radius=theme.spacing.card_radius)
        hero.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, theme.spacing.lg))
        hero.grid_columnconfigure(0, weight=1)

        text_col = ctk.CTkFrame(hero, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=theme.spacing.lg)
        ctk.CTkLabel(
            text_col, text="🚀  Ready to bill today?",
            font=("Segoe UI", 20, "bold"), text_color=theme.colors.white, anchor="w",
        ).pack(anchor="w")
        collected = kpis.month_revenue or Decimal("0")
        outstanding = outstanding or Decimal("0")
        total = collected + outstanding
        if total > 0:
            rate = float(collected / total) * 100
            subtitle = f"You've collected {format_currency(collected)} of {format_currency(total)} billed  •  {rate:.0f}% collection rate"
        else:
            subtitle = "Create your first invoice and watch your business grow here."
        ctk.CTkLabel(
            text_col, text=subtitle, font=theme.fonts.body, text_color="#94A3B8", anchor="w"
        ).pack(anchor="w", pady=(4, 0))

        btn_col = ctk.CTkFrame(hero, fg_color="transparent")
        btn_col.grid(row=0, column=1, sticky="e", padx=theme.spacing.lg, pady=theme.spacing.lg)

        invoice_btn = PrimaryButton(btn_col, text="＋  New Invoice", command=self._quick_new_invoice, height=44)
        invoice_btn.pack(fill="x", pady=(0, theme.spacing.sm))

        for label, callback in (("👤  Add Customer", self._quick_add_customer), ("📊  View Reports", self._quick_view_reports)):
            ctk.CTkButton(
                btn_col, text=label, font=theme.fonts.button, height=40,
                fg_color="transparent", hover_color=theme.colors.sidebar_hover,
                text_color=theme.colors.white, border_width=1, border_color="#334155",
                corner_radius=theme.spacing.radius, command=callback,
            ).pack(fill="x", pady=(0, theme.spacing.sm) if label != "📊  View Reports" else 0)

    def _quick_new_invoice(self) -> None:
        if self._on_new_invoice:
            self._on_new_invoice()

    def _quick_add_customer(self) -> None:
        if self._on_add_customer:
            self._on_add_customer()

    def _quick_view_reports(self) -> None:
        if self._on_view_reports:
            self._on_view_reports()

    # ---------------------------------------------------------------- pieces
    def _section_card(self, parent, title: str, row: int, action_text: str | None = None,
                      on_action: Callable[[], None] | None = None) -> Card:
        card = Card(parent)
        card.grid(row=row, column=0, sticky="nsew", pady=(0, theme.spacing.lg))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=theme.fonts.card_title, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        if action_text and on_action:
            ctk.CTkButton(
                card, text=action_text, font=theme.fonts.small_bold, height=28,
                fg_color=theme.colors.primary_soft, hover_color="#E0E7FF",
                text_color=theme.colors.primary, corner_radius=8, command=on_action,
            ).grid(row=0, column=1, sticky="e", padx=theme.spacing.md)
        return card

    def _build_revenue_chart(self, parent, monthly_revenue: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "📊 Monthly Revenue", row=0)
        if not monthly_revenue:
            EmptyState(
                card, message="No revenue yet — your chart will shine here after the first payment.",
                icon="📈", action_label="Create First Invoice", on_action=self._quick_new_invoice,
            ).grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
            return

        months = [self._short_month(m) for m, _ in monthly_revenue]
        totals = [float(v) for _, v in monthly_revenue]

        figure = Figure(figsize=(5, 2.8), dpi=100)
        axis = figure.add_subplot(111)
        bars = axis.bar(
            months, totals, color=theme.colors.primary, width=0.45,
            edgecolor=theme.colors.primary_hover, linewidth=1.2, zorder=3,
        )
        axis.set_facecolor(theme.colors.card)
        figure.patch.set_facecolor(theme.colors.card)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            axis.spines[spine].set_color(theme.colors.border)
        axis.tick_params(labelsize=8, colors=theme.colors.text_secondary)
        axis.yaxis.grid(True, color=theme.colors.border, linewidth=0.6, alpha=0.7, zorder=0)
        axis.set_axisbelow(True)
        peak = max(totals) if totals else 0
        for bar, total in zip(bars, totals):
            is_peak = total == peak and peak > 0
            if is_peak:
                bar.set_color(theme.colors.success)
                bar.set_edgecolor(theme.colors.success)
            axis.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"₹{total:,.0f}", ha="center", va="bottom", fontsize=7,
                color=theme.colors.text if is_peak else theme.colors.text_secondary,
                weight="bold" if is_peak else "normal",
            )
        figure.tight_layout()

        canvas = FigureCanvasTkAgg(figure, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))

    @staticmethod
    def _short_month(yyyy_mm: str) -> str:
        try:
            parsed = datetime.strptime(yyyy_mm, "%Y-%m")
            return parsed.strftime("%b %y")
        except Exception:
            return yyyy_mm

    def _build_recent_invoices(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "🧾 Recent Invoices", row=1, action_text="＋ New", on_action=self._quick_new_invoice)
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
            row_tag_fn=lambda r: str(r.get("status", "")).upper(),
            tag_colors={status: colors[0] for status, colors in theme.STATUS_COLORS.items()},
            empty_message="No invoices yet — create one and it will appear here",
            empty_action_label="New Invoice",
            on_empty_action=self._quick_new_invoice,
        )
        table.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=220)
        table.set_rows(table_rows)

    def _build_payment_breakdown(self, parent, rows: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "💳 Payment Modes", row=0)
        if not rows:
            EmptyState(card, message="No payments recorded yet.", icon="💳").grid(
                row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md)
            )
            return

        max_amount = max(float(v) for _, v in rows) or 1
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, columnspan=2, sticky="ew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        body.grid_columnconfigure(0, weight=1)

        palette = list(theme.CHART_PALETTE)
        for i, (mode, amount) in enumerate(rows):
            icon = _MODE_ICONS.get(mode, "🧾")
            color = palette[i % len(palette)]
            ctk.CTkLabel(body, text=f"{icon}  {mode}", font=theme.fonts.small_bold, text_color=theme.colors.text, anchor="w").grid(
                row=i * 2, column=0, sticky="w", pady=(theme.spacing.xs, 0)
            )
            ctk.CTkLabel(
                body, text=format_currency(amount), font=theme.fonts.small, text_color=theme.colors.text_secondary
            ).grid(row=i * 2, column=1, sticky="e")
            bar = ctk.CTkProgressBar(body, height=8, progress_color=color, fg_color=theme.colors.background)
            bar.set(float(amount) / max_amount)
            bar.grid(row=i * 2 + 1, column=0, columnspan=2, sticky="ew", pady=(2, theme.spacing.sm))

    def _build_top_courses(self, parent, rows: list[tuple[str, Decimal]]) -> None:
        card = self._section_card(parent, "🏆 Top Courses", row=1)
        table_rows = [
            {"id": i, "rank": _RANK_MEDALS[i] if i < len(_RANK_MEDALS) else f"{i + 1}.",
             "name": name, "revenue": format_currency(amount)}
            for i, (name, amount) in enumerate(rows)
        ]
        table = DataTable(
            card,
            columns=[("rank", "", 40, "w"), ("name", "Course/Product", 140, "w"), ("revenue", "Revenue", 100, "e")],
            empty_message="No course sales in this period yet",
        )
        table.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)

    def _build_recent_payments(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "💰 Recent Payments", row=2)
        table_rows = [
            {
                "id": r["id"],
                "payment_date": format_date(r["payment_date"]),
                "amount": format_currency(r["amount"]),
                "payment_mode": f"{_MODE_ICONS.get(r['payment_mode'], '🧾')} {r['payment_mode']}",
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
        table.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)

    def _build_recent_expenses(self, parent, rows: list[dict]) -> None:
        card = self._section_card(parent, "🧮 Recent Expenses", row=3)
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
        table.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=160)
        table.set_rows(table_rows)
