"""Payments list screen (Section 15): every payment ever recorded, across
all invoices, searchable/filterable and exportable."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import payment_controller
from gui.billing.invoice_detail_view import InvoiceDetailModal
from gui.components.buttons import SecondaryButton
from gui.components.cards import Card
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date

MODE_FILTERS = ["All"] + payment_controller.PAYMENT_MODES

_MODE_ICONS = {"Cash": "💵", "UPI": "📱", "Card": "💳", "Bank Transfer": "🏦", "Cheque": "🧾", "Other": "🧾"}


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class PaymentsListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._mode_filter = "All"

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_summary()
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
        self.table.grid(row=2, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="pay")

        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("💰", "TOTAL COLLECTED", theme.colors.success),
             ("🧾", "TRANSACTIONS", theme.colors.primary),
             ("📱", "TOP MODE", theme.colors.info)]
        ):
            card = Card(strip)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, theme.spacing.sm) if i < 2 else (theme.spacing.sm, 0))
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card, text=icon, font=("Segoe UI", 22), text_color=accent,
                fg_color=_soft(accent), corner_radius=10, width=46, height=46,
            ).grid(row=0, column=0, rowspan=2, padx=theme.spacing.sm, pady=theme.spacing.sm)
            ctk.CTkLabel(
                card, text=label, font=theme.fonts.kpi_label, text_color=theme.colors.text_secondary, anchor="w"
            ).grid(row=0, column=1, sticky="w", padx=(0, theme.spacing.sm), pady=(theme.spacing.sm, 0))
            value_label = ctk.CTkLabel(
                card, text="—", font=("Segoe UI", 20, "bold"), text_color=theme.colors.text, anchor="w"
            )
            value_label.grid(row=1, column=1, sticky="w", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
            self._sum_values.append(value_label)

    def _refresh_summary(self, rows: list[dict]) -> None:
        from collections import Counter
        from decimal import Decimal

        total = sum((r.get("amount") or Decimal("0")) for r in rows)
        counts = Counter(r.get("payment_mode") or "Other" for r in rows)
        if counts:
            top_mode, top_n = counts.most_common(1)[0]
            top_text = f"{_MODE_ICONS.get(top_mode, '🧾')} {top_mode} ×{top_n}"
        else:
            top_text = "—"
        texts = [format_currency(total), f"{len(rows):,}", top_text]
        try:
            from gui.components.animations import count_up

            count_up(self._sum_values[0], texts[0], duration_ms=500)
            count_up(self._sum_values[1], texts[1], duration_ms=500)
            self._sum_values[2].configure(text=texts[2])
        except Exception:
            for label, text in zip(self._sum_values, texts):
                try:
                    label.configure(text=text)
                except Exception:
                    pass

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.md)
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
                "payment_mode": f"{_MODE_ICONS.get(row['payment_mode'], '🧾')} {row['payment_mode']}",
                "reference_number": row["reference_number"] or "—",
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)
        self._refresh_summary(rows)

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
