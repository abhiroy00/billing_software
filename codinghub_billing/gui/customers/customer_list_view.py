"""Customer list screen (Section 11): search, filter, sort, export, and
row actions (view/edit/delete) via double-click or right-click."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import customer_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.customers.customer_detail_view import CustomerDetailModal
from gui.customers.customer_form_modal import CustomerFormModal
from gui.theme import theme
from utils.formatters import format_currency

STATUS_FILTERS = ["All", "Active", "Inactive"]


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class CustomerListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._status_filter = "All"

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_summary()
        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("customer_code", "Code", 90, "w"),
                ("name", "Name", 180, "w"),
                ("mobile", "Mobile", 110, "w"),
                ("course_name", "Course", 150, "w"),
                ("status", "Status", 90, "w"),
                ("outstanding_display", "Outstanding", 110, "e"),
            ],
            on_row_double_click=self._open_detail,
            on_row_context_menu=self._row_menu,
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={"active": theme.colors.success, "inactive": theme.colors.text_secondary},
            empty_message="No customers found",
            empty_action_label="Add Customer",
            on_empty_action=self._open_add_form,
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="cust")

        self._sum_cards: list[Card] = []
        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("👥", "TOTAL CUSTOMERS", theme.colors.primary),
             ("✅", "ACTIVE", theme.colors.success),
             ("⏳", "TOTAL OUTSTANDING", theme.colors.danger)]
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
            self._sum_cards.append(card)
            self._sum_values.append(value_label)

    def _refresh_summary(self, rows: list[dict]) -> None:
        from decimal import Decimal

        total = len(rows)
        active = sum(1 for r in rows if str(r.get("status", "")).lower() == "active")
        outstanding = sum((r.get("outstanding") or Decimal("0")) for r in rows)
        texts = [f"{total:,}", f"{active:,}", format_currency(outstanding)]
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

        self.search_box = SearchBox(bar, placeholder="Search by name, mobile, email, ID...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        self.status_menu = ctk.CTkOptionMenu(
            bar,
            values=STATUS_FILTERS,
            command=self._on_status_change,
            width=130,
            font=theme.fonts.body,
            fg_color=theme.colors.background,
            button_color=theme.colors.primary,
            button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.status_menu.set("All")
        self.status_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        SecondaryButton(bar, text="Export", icon="\U0001F4E4", command=self._export).grid(
            row=0, column=2, padx=(0, theme.spacing.sm)
        )
        PrimaryButton(bar, text="New Customer", icon="+", command=self._open_add_form).grid(row=0, column=3)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_status_change(self, value: str) -> None:
        self._status_filter = value
        self._load()

    def _load(self) -> None:
        rows = customer_controller.list_customers(query=self._query, status=self._status_filter)
        display_rows = [{**row, "outstanding_display": format_currency(row["outstanding"])} for row in rows]
        self.table.set_rows(display_rows)
        self._refresh_summary(rows)

    def _open_add_form(self) -> None:
        CustomerFormModal(self, on_saved=lambda _c: self._load())

    def _open_edit_form(self, row: dict) -> None:
        CustomerFormModal(self, customer_id=row["id"], on_saved=lambda _c: self._load())

    def _open_detail(self, row: dict) -> None:
        CustomerDetailModal(self, customer_id=row["id"], on_changed=self._load)

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        return [
            ("View", lambda: self._open_detail(row)),
            ("Edit", lambda: self._open_edit_form(row)),
            ("Delete", lambda: self._confirm_delete(row)),
        ]

    def _confirm_delete(self, row: dict) -> None:
        def do_delete():
            success, message = customer_controller.delete_customer(row["id"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, f"Customer {row['name']} deleted.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Customer",
            message=f"Are you sure you want to delete {row['name']}? This cannot be undone.",
            on_confirm=do_delete,
        )

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export customers", defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not path:
            return
        success, message = customer_controller.export_customers_to_excel(
            path, query=self._query, status=self._status_filter
        )
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Customers exported successfully.", variant="success")
        else:
            show_toast(root, message, variant="error")
