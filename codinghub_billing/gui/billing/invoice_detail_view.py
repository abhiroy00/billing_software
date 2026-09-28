"""Invoice detail modal (Section 13): items, tax breakdown, payments,
and actions (Record Payment / Cancel Invoice)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import invoice_controller
from gui.components.badges import StatusBadge
from gui.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog, Modal
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils.formatters import format_currency, format_date


class InvoiceDetailModal(Modal):
    def __init__(self, master, invoice_id: int, on_changed: Callable[[], None] | None = None):
        super().__init__(master, title="Invoice Details", width=780, height=700, resizable=True, scrollable=True)
        self._invoice_id = invoice_id
        self._on_changed = on_changed

        self.scroll_body.grid_columnconfigure(0, weight=1)
        self._reload()

    def _reload(self) -> None:
        for child in self.scroll_body.winfo_children():
            child.destroy()
        for child in self.actions.winfo_children():
            child.destroy()

        detail, error = invoice_controller.get_invoice_detail(self._invoice_id)
        if detail is None:
            ctk.CTkLabel(self.scroll_body, text=error or "Invoice not found.", text_color=theme.colors.danger).grid(
                row=0, column=0, pady=theme.spacing.lg
            )
            SecondaryButton(self.actions, text="Close", command=self.destroy).pack(side="right")
            return

        self._render(detail)

    def _render(self, detail: dict) -> None:
        invoice = detail["invoice"]

        header = Card(self.scroll_body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, theme.spacing.md))
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            title_row, text=invoice["invoice_number"], font=theme.fonts.section_heading, text_color=theme.colors.text
        ).pack(side="left")
        StatusBadge(title_row, status=invoice["status"]).pack(side="left", padx=(theme.spacing.sm, 0))

        meta_text = f"{format_date(invoice['invoice_date'])}  •  {invoice['customer_name']}  •  {invoice['customer_mobile']}"
        ctk.CTkLabel(
            header, text=meta_text, font=theme.fonts.body, text_color=theme.colors.text_secondary, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        items_card = Card(self.scroll_body)
        items_card.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))
        items_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(items_card, text="Items", font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        items_table = DataTable(
            items_card,
            columns=[
                ("item_name", "Item", 180, "w"),
                ("quantity", "Qty", 60, "e"),
                ("rate", "Rate", 90, "e"),
                ("discount", "Discount", 90, "e"),
                ("tax_percentage", "Tax %", 70, "e"),
                ("total_amount", "Total", 100, "e"),
            ],
            empty_message="No items.",
        )
        items_table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        items_table.configure(height=140)
        items_table.set_rows(
            [
                {
                    **item,
                    "rate": format_currency(item["rate"]),
                    "discount": format_currency(item["discount"]),
                    "tax_percentage": f"{item['tax_percentage']}%",
                    "total_amount": format_currency(item["total_amount"]),
                }
                for item in detail["items"]
            ]
        )

        summary = Card(self.scroll_body)
        summary.grid(row=2, column=0, sticky="ew", pady=(0, theme.spacing.md))
        summary.grid_columnconfigure(1, weight=1)
        summary_rows = [
            ("Subtotal", invoice["subtotal"], theme.fonts.body, theme.colors.text),
            ("Discount", -invoice["discount_total"], theme.fonts.body, theme.colors.text),
            ("CGST", invoice["cgst_total"], theme.fonts.body, theme.colors.text),
            ("SGST", invoice["sgst_total"], theme.fonts.body, theme.colors.text),
            ("IGST", invoice["igst_total"], theme.fonts.body, theme.colors.text),
            ("Round Off", invoice["round_off"], theme.fonts.body, theme.colors.text),
            ("Grand Total", invoice["grand_total"], theme.fonts.body_bold, theme.colors.text),
            ("Paid", invoice["paid_amount"], theme.fonts.body, theme.colors.success),
            ("Due", invoice["due_amount"], theme.fonts.body_bold, theme.colors.danger if invoice["due_amount"] > 0 else theme.colors.success),
        ]
        for i, (label, value, font, color) in enumerate(summary_rows):
            top_pad = theme.spacing.md if i == 0 else 2
            bottom_pad = theme.spacing.md if i == len(summary_rows) - 1 else 2
            ctk.CTkLabel(summary, text=label, font=font, text_color=theme.colors.text_secondary).grid(
                row=i, column=0, sticky="w", padx=theme.spacing.md, pady=(top_pad, bottom_pad)
            )
            ctk.CTkLabel(summary, text=format_currency(value), font=font, text_color=color).grid(
                row=i, column=1, sticky="e", padx=theme.spacing.md, pady=(top_pad, bottom_pad)
            )

        payments_card = Card(self.scroll_body)
        payments_card.grid(row=3, column=0, sticky="ew", pady=(0, theme.spacing.md))
        payments_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(payments_card, text="Payments", font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        payments_table = DataTable(
            payments_card,
            columns=[
                ("payment_date", "Date", 90, "w"),
                ("amount", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
                ("reference_number", "Reference", 140, "w"),
            ],
            empty_message="No payments recorded yet.",
        )
        payments_table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        payments_table.configure(height=120)
        payments_table.set_rows(
            [
                {**p, "payment_date": format_date(p["payment_date"]), "amount": format_currency(p["amount"])}
                for p in detail["payments"]
            ]
        )

        SecondaryButton(self.actions, text="Close", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        if invoice["status"] != "CANCELLED":
            if invoice["due_amount"] > 0:
                PrimaryButton(self.actions, text="Record Payment", command=lambda: self._record_payment(invoice)).pack(
                    side="right", padx=(theme.spacing.sm, 0)
                )
            if invoice["paid_amount"] == 0:
                DangerButton(self.actions, text="Cancel Invoice", command=lambda: self._confirm_cancel(invoice)).pack(
                    side="right"
                )

    def _record_payment(self, invoice: dict) -> None:
        from gui.billing.payment_form_modal import PaymentFormModal

        def after_recorded(_result):
            self._reload()
            if self._on_changed:
                self._on_changed()

        PaymentFormModal(
            self.master,
            invoice_id=invoice["id"],
            invoice_number=invoice["invoice_number"],
            grand_total=invoice["grand_total"],
            paid_amount=invoice["paid_amount"],
            due_amount=invoice["due_amount"],
            on_recorded=after_recorded,
        )

    def _confirm_cancel(self, invoice: dict) -> None:
        def do_cancel():
            success, message = invoice_controller.cancel_invoice(invoice["id"])
            root = self.master.winfo_toplevel()
            if success:
                show_toast(root, f"Invoice {invoice['invoice_number']} cancelled.", variant="success")
                self._reload()
                if self._on_changed:
                    self._on_changed()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self,
            title="Cancel Invoice",
            message=f"Are you sure you want to cancel invoice {invoice['invoice_number']}? This cannot be undone.",
            on_confirm=do_cancel,
            confirm_label="Cancel Invoice",
        )
