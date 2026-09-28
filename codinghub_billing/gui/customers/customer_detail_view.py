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


_AVATAR_PALETTE = ("#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6")


def _avatar_color(name: str) -> str:
    return _AVATAR_PALETTE[sum(ord(ch) for ch in name) % len(_AVATAR_PALETTE)]


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
        from decimal import Decimal

        customer = detail["customer"]
        outstanding = detail["outstanding"] or Decimal("0")
        invoices = detail["invoices"]
        payments = detail["payments"]

        header = Card(self.scroll_body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, theme.spacing.md))
        header.grid_columnconfigure(1, weight=1)

        initials = "".join(part[:1] for part in (customer["name"] or "U").split()[:2]).upper()
        avatar_color = _avatar_color(customer["name"] or "")
        ctk.CTkLabel(
            header, text=initials, font=("Segoe UI", 22, "bold"),
            text_color=theme.colors.white, fg_color=avatar_color,
            corner_radius=28, width=56, height=56,
        ).grid(row=0, column=0, rowspan=2, padx=theme.spacing.md, pady=theme.spacing.md)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=1, sticky="ew", padx=(0, theme.spacing.md), pady=(theme.spacing.md, 0))
        ctk.CTkLabel(
            title_row, text=customer["name"], font=("Segoe UI", 19, "bold"), text_color=theme.colors.text
        ).pack(side="left")
        StatusBadge(title_row, status=customer["status"]).pack(side="left", padx=(theme.spacing.sm, 0))
        ctk.CTkLabel(
            title_row, text=customer["customer_code"], font=theme.fonts.small_bold,
            text_color=theme.colors.primary, fg_color=theme.colors.primary_soft,
            corner_radius=8, padx=8, pady=2,
        ).pack(side="left", padx=(theme.spacing.sm, 0))

        contact_bits = [
            ("📱", customer["mobile"]),
            ("✉️", customer.get("email") or ""),
            ("📚", customer.get("course_name") or ""),
            ("📍", "  ".join(filter(None, [customer.get("city") or "", customer.get("state") or ""]))),
        ]
        contact_row = ctk.CTkFrame(header, fg_color="transparent")
        contact_row.grid(row=1, column=1, sticky="ew", padx=(0, theme.spacing.md), pady=(2, theme.spacing.sm))
        shown = 0
        for icon, value in contact_bits:
            if not value:
                continue
            ctk.CTkLabel(
                contact_row, text=f"{icon}  {value}", font=theme.fonts.small,
                text_color=theme.colors.text_secondary,
            ).pack(side="left", padx=(0, theme.spacing.md))
            shown += 1
        if shown == 0:
            ctk.CTkLabel(
                contact_row, text="No contact details added yet.",
                font=theme.fonts.small, text_color=theme.colors.text_secondary,
            ).pack(side="left")

        banner_bg = theme.colors.danger_soft if outstanding > 0 else theme.colors.success_soft
        banner_fg = theme.colors.danger if outstanding > 0 else theme.colors.success
        banner_icon = "⏳" if outstanding > 0 else "✅"
        banner_text = (
            f"{banner_icon}  Outstanding Balance:  {format_currency(outstanding)}"
            if outstanding > 0 else f"{banner_icon}  All clear — no outstanding balance"
        )
        banner = ctk.CTkFrame(self.scroll_body, fg_color=banner_bg, corner_radius=theme.spacing.radius)
        banner.grid(row=1, column=0, sticky="ew", pady=(0, theme.spacing.md))
        banner.grid_columnconfigure((0, 1, 2), weight=1, uniform="mini")
        paid_total = sum((p.get("amount") or Decimal("0")) for p in payments)
        for i, (label, value) in enumerate(
            [(f"🧾 INVOICES", str(len(invoices))),
             (f"💰 PAID", format_currency(paid_total)),
             (f"⏳ DUE", format_currency(outstanding))]
        ):
            cell = ctk.CTkFrame(banner, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="nsew", padx=theme.spacing.sm, pady=theme.spacing.sm)
            ctk.CTkLabel(cell, text=label, font=theme.fonts.kpi_label, text_color=banner_fg).pack()
            ctk.CTkLabel(cell, text=value, font=("Segoe UI", 17, "bold"), text_color=theme.colors.text).pack()
        ctk.CTkLabel(
            self.scroll_body, text=banner_text, font=theme.fonts.body_bold, text_color=banner_fg, anchor="w"
        ).grid(row=2, column=0, sticky="w", pady=(0, theme.spacing.md))

        self._section(
            row=3,
            title=f"🧾 Invoices  ({len(invoices)})",
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
            tag_fn=lambda r: str(r.get("status", "")).upper(),
        )

        self._section(
            row=4,
            title=f"💰 Payments  ({len(payments)})",
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
            row=5,
            title=f"📜 Activity  ({len(detail['activity'])})",
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

    def _section(self, row: int, title: str, columns, rows, empty_message: str,
                 tag_fn=None) -> None:
        card = Card(self.scroll_body)
        card.grid(row=row, column=0, sticky="ew", pady=(0, theme.spacing.md))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=theme.fonts.card_title, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        kwargs: dict = {}
        if tag_fn is not None:
            kwargs = {
                "row_tag_fn": tag_fn,
                "tag_colors": {status: colors[0] for status, colors in theme.STATUS_COLORS.items()},
            }
        table = DataTable(card, columns=columns, empty_message=empty_message, **kwargs)
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
