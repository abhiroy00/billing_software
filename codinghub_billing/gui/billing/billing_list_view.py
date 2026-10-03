"""Invoice list screen (Section 13): search, filter by status, row actions
(view / record payment / cancel)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import invoice_controller
from gui.billing.invoice_detail_view import InvoiceDetailModal
from gui.components.buttons import DangerButton, PrimaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date

STATUS_FILTERS = ["All", "PENDING", "PARTIAL", "PAID", "CANCELLED"]


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class BillingListView(ctk.CTkFrame):
    def __init__(self, master, on_new_invoice: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self._on_new_invoice = on_new_invoice
        self._query = ""
        self._status_filter = "All"

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_summary()
        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("invoice_number", "Invoice No", 120, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("customer_name", "Customer", 170, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("paid_amount", "Paid", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            on_row_double_click=self._open_detail,
            on_row_context_menu=self._row_menu,
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={
                "paid": theme.colors.success,
                "partial": theme.colors.warning,
                "pending": theme.colors.danger,
                "cancelled": theme.colors.text_secondary,
            },
            empty_message="No invoices found",
            empty_action_label="Create Invoice",
            on_empty_action=self._on_new_invoice,
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="bill")

        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("🧾", "TOTAL INVOICES", theme.colors.primary),
             ("💰", "TOTAL BILLED", theme.colors.success),
             ("⏳", "TOTAL DUE", theme.colors.danger)]
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
        from decimal import Decimal

        billed = sum((r.get("grand_total") or Decimal("0")) for r in rows)
        due = sum((r.get("due_amount") or Decimal("0")) for r in rows)
        texts = [f"{len(rows):,}", format_currency(billed), format_currency(due)]
        try:
            from gui.components.animations import count_up

            for label, text in zip(self._sum_values, texts):
                count_up(label, text, duration_ms=500)
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

        self.status_menu = ctk.CTkOptionMenu(
            bar, values=STATUS_FILTERS, command=self._on_status_change, width=140,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.status_menu.set("All")
        self.status_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        PrimaryButton(bar, text="New Invoice", icon="+", command=self._on_new_invoice).grid(
            row=0, column=2, padx=(0, theme.spacing.sm)
        )
        DangerButton(
            bar, text="Delete", icon="🗑️", command=self._delete_selected,
            width=84, height=30, font=theme.fonts.small_bold, corner_radius=6,
        ).grid(row=0, column=3)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_status_change(self, value: str) -> None:
        self._status_filter = value
        self._load()

    def _load(self) -> None:
        rows = invoice_controller.list_invoices(query=self._query, status=self._status_filter)
        display_rows = [
            {
                **row,
                "invoice_date": format_date(row["invoice_date"]),
                "grand_total": format_currency(row["grand_total"]),
                "paid_amount": format_currency(row["paid_amount"]),
                "due_amount": format_currency(row["due_amount"]),
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)
        self._refresh_summary(rows)

    def _open_detail(self, row: dict) -> None:
        InvoiceDetailModal(self, invoice_id=row["id"], on_changed=self._load)

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        return [
            ("View Invoice", lambda: self._open_detail(row)),
            ("Download Invoice PDF", lambda: self._download_invoice_pdf(row)),
            ("Delete Invoice", lambda: self._confirm_delete(row)),
        ]

    def _selected_or_warn(self) -> dict | None:
        row = self.table.get_selected()
        if row is None:
            show_toast(self.winfo_toplevel(), "Pehle list me se ek invoice select karo.", variant="error")
        return row

    def _delete_selected(self) -> None:
        row = self._selected_or_warn()
        if row is not None:
            self._confirm_delete(row)

    def _confirm_delete(self, row: dict) -> None:
        def do_delete():
            success, message = invoice_controller.delete_invoice(row["id"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, f"Invoice {row['invoice_number']} deleted.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Invoice",
            message=(
                f"Permanently delete invoice {row['invoice_number']} for {row['customer_name']}? "
                "Its line items and payments will also be deleted. This cannot be undone."
            ),
            on_confirm=do_delete,
            confirm_label="Delete Invoice",
        )

    def _download_invoice_pdf(self, row: dict) -> None:
        from tkinter import filedialog

        from controllers import document_controller

        path = filedialog.asksaveasfilename(
            title="Save Invoice PDF",
            initialfile=document_controller.default_invoice_path(row["invoice_number"]).name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        success, message, saved = document_controller.generate_invoice_pdf(row["id"], path)
        root = self.winfo_toplevel()
        if not success:
            show_toast(root, message, variant="error")
            return
        show_toast(root, "Invoice PDF saved. Opening…", variant="success")
        document_controller.open_file(saved)

    def refresh(self) -> None:
        self._load()
