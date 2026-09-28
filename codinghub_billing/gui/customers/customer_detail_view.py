"""Customer detail modal (Section 11): Profile, Invoices, Payments,
Outstanding, Course, Activity."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import customer_controller
from gui.components.badges import StatusBadge
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.dialogs import Modal
from gui.components.table import DataTable
from gui.theme import theme
from utils.formatters import format_currency, format_date


class CustomerDetailModal(Modal):
    def __init__(self, master, customer_id: int, on_changed: Callable[[], None] | None = None):
        super().__init__(master, title="Customer Details", width=760, height=680, resizable=True, scrollable=True)
        self._customer_id = customer_id
        self._on_changed = on_changed

        self.scroll_body.grid_columnconfigure(0, weight=1)

        detail, error = customer_controller.get_customer_detail(customer_id)
        if detail is None:
            ctk.CTkLabel(self.scroll_body, text=error or "Customer not found.", text_color=theme.colors.danger).grid(
                row=0, column=0, pady=theme.spacing.lg
            )
            SecondaryButton(self.actions, text="Close", command=self.destroy).pack(side="right")
            return

        self._render(detail)

        SecondaryButton(self.actions, text="Close", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Edit Customer", command=self._edit).pack(side="right")

    def _render(self, detail: dict) -> None:
        customer = detail["customer"]

        header = Card(self.scroll_body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, theme.spacing.md))
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            title_row, text=customer["name"], font=theme.fonts.section_heading, text_color=theme.colors.text
        ).pack(side="left")
        StatusBadge(title_row, status=customer["status"]).pack(side="left", padx=(theme.spacing.sm, 0))

        meta_text = "  •  ".join(
            filter(
                None,
                [
                    customer["customer_code"],
                    customer["mobile"],
                    customer.get("email") or "",
                    customer.get("course_name") or "",
                ],
            )
        )
        ctk.CTkLabel(
            header, text=meta_text, font=theme.fonts.body, text_color=theme.colors.text_secondary, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        outstanding_color = theme.colors.danger if detail["outstanding"] > 0 else theme.colors.success
        ctk.CTkLabel(
            header,
            text=f"Outstanding Balance:  {format_currency(detail['outstanding'])}",
            font=theme.fonts.body_bold,
            text_color=outstanding_color,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        self._section(
            row=1,
            title="Invoices",
            columns=[
                ("invoice_number", "Invoice No", 110, "w"),
                ("invoice_date", "Date", 90, "w"),
                ("grand_total", "Amount", 100, "e"),
                ("due_amount", "Due", 100, "e"),
                ("status", "Status", 90, "w"),
            ],
            rows=[
                {
                    **inv,
                    "invoice_date": format_date(inv["invoice_date"]),
                    "grand_total": format_currency(inv["grand_total"]),
                    "due_amount": format_currency(inv["due_amount"]),
                }
                for inv in detail["invoices"]
            ],
            empty_message="No invoices yet.",
        )

        self._section(
            row=2,
            title="Payments",
            columns=[
                ("payment_date", "Date", 90, "w"),
                ("amount", "Amount", 100, "e"),
                ("payment_mode", "Mode", 100, "w"),
            ],
            rows=[
                {**p, "payment_date": format_date(p["payment_date"]), "amount": format_currency(p["amount"])}
                for p in detail["payments"]
            ],
            empty_message="No payments yet.",
        )

        self._section(
            row=3,
            title="Activity",
            columns=[
                ("timestamp", "When", 140, "w"),
                ("action", "Action", 90, "w"),
                ("description", "Description", 260, "w"),
            ],
            rows=[
                {**a, "timestamp": a["timestamp"].strftime("%d-%m-%Y %H:%M")}
                for a in detail["activity"]
            ],
            empty_message="No recent activity.",
        )

    def _section(self, row: int, title: str, columns, rows, empty_message: str) -> None:
        card = Card(self.scroll_body)
        card.grid(row=row, column=0, sticky="ew", pady=(0, theme.spacing.md))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        table = DataTable(card, columns=columns, empty_message=empty_message)
        table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        table.configure(height=150)
        table.set_rows(rows)

    def _edit(self) -> None:
        from gui.customers.customer_form_modal import CustomerFormModal

        def after_save(_customer):
            if self._on_changed:
                self._on_changed()
            self.destroy()

        CustomerFormModal(self.master, customer_id=self._customer_id, on_saved=after_save)
        self.destroy()
