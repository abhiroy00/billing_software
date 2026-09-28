"""New Invoice creation screen (Section 13/47): customer -> items ->
discount -> tax -> payment -> save, computed live via invoice_controller
so the GUI never invents its own totals."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from controllers import course_controller, customer_controller, invoice_controller, payment_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import FormField, SearchBox, dropdown_factory
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from utils import validators
from utils.formatters import format_currency, format_date, parse_date

NO_COURSE_LABEL = "No active courses — add one in Courses first"


class InvoiceFormView(ctk.CTkFrame):
    def __init__(self, master, on_saved: Callable[[], None], on_cancel: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self._on_saved = on_saved
        self._on_cancel = on_cancel
        self._selected_customer: dict | None = None
        self._items: list[dict] = []
        self._courses = course_controller.list_active_courses_for_billing()
        self._course_by_name = {c["name"]: c for c in self._courses}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=theme.spacing.lg, pady=theme.spacing.lg)
        self.scroll.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_customer_section()
        self._build_items_section()
        self._build_summary_section()
        self._build_payment_section()
        self._build_actions()

        self._refresh_items_table()
        self._refresh_summary()

    # -------------------------------------------------------------- header
    def _build_header(self) -> None:
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", pady=(0, theme.spacing.md))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="New Invoice", font=theme.fonts.page_heading, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w"
        )
        preview_number = invoice_controller.peek_next_invoice_number()
        ctk.CTkLabel(
            row, text=f"Invoice No.  {preview_number}", font=theme.fonts.body_bold, text_color=theme.colors.primary
        ).grid(row=0, column=2, sticky="e")

        date_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        date_row.grid(row=1, column=0, sticky="w", pady=(0, theme.spacing.md))
        self.invoice_date = FormField(date_row, "Invoice Date (DD-MM-YYYY)")
        self.invoice_date.set(format_date(date.today()))
        self.invoice_date.pack()

    # ------------------------------------------------------------ customer
    def _build_customer_section(self) -> None:
        card = Card(self.scroll)
        card.grid(row=2, column=0, sticky="ew", pady=(0, theme.spacing.md))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Customer", font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )

        self.customer_search = SearchBox(card, placeholder="Search by name, mobile, email...", on_change=self._search_customers)
        self.customer_search.grid(row=1, column=0, sticky="ew", padx=theme.spacing.md)

        self.customer_results = ctk.CTkFrame(card, fg_color="transparent")
        self.customer_results.grid(row=2, column=0, sticky="ew", padx=theme.spacing.md, pady=(theme.spacing.xs, 0))

        self.customer_selected_frame = ctk.CTkFrame(card, fg_color=theme.colors.background, corner_radius=theme.spacing.radius)
        self.customer_selected_label = ctk.CTkLabel(
            self.customer_selected_frame, text="", font=theme.fonts.body, text_color=theme.colors.text, anchor="w"
        )
        self.customer_selected_label.pack(side="left", padx=theme.spacing.md, pady=theme.spacing.sm)
        SecondaryButton(self.customer_selected_frame, text="Change", command=self._clear_customer).pack(
            side="right", padx=theme.spacing.md, pady=theme.spacing.sm
        )

        ctk.CTkLabel(card, text="", height=theme.spacing.sm).grid(row=3, column=0)

    def _search_customers(self, query: str) -> None:
        for child in self.customer_results.winfo_children():
            child.destroy()
        if not query.strip():
            return
        matches = customer_controller.list_customers(query=query)[:6]
        if not matches:
            ctk.CTkLabel(
                self.customer_results, text="No matching customers.", font=theme.fonts.small, text_color=theme.colors.text_secondary
            ).pack(anchor="w", pady=(2, 4))
            return
        for row in matches:
            label = f"{row['name']}  •  {row['mobile']}  •  Outstanding: {format_currency(row['outstanding'])}"
            btn = ctk.CTkButton(
                self.customer_results, text=label, anchor="w", font=theme.fonts.small,
                fg_color="transparent", hover_color=theme.colors.background, text_color=theme.colors.text,
                command=lambda r=row: self._select_customer(r),
            )
            btn.pack(fill="x", pady=1)

    def _select_customer(self, row: dict) -> None:
        self._selected_customer = row
        for child in self.customer_results.winfo_children():
            child.destroy()
        self.customer_search.clear()
        self.customer_selected_label.configure(
            text=f"{row['name']}   •   {row['mobile']}   •   Outstanding balance: {format_currency(row['outstanding'])}"
        )
        self.customer_selected_frame.grid(row=1, column=0, sticky="ew", padx=theme.spacing.md, pady=(0, theme.spacing.sm))
        self.customer_search.grid_remove()
        self._refresh_summary()

    def _clear_customer(self) -> None:
        self._selected_customer = None
        self.customer_selected_frame.grid_remove()
        self.customer_search.grid()
        self._refresh_summary()

    # --------------------------------------------------------------- items
    def _build_items_section(self) -> None:
        card = Card(self.scroll)
        card.grid(row=3, column=0, sticky="ew", pady=(0, theme.spacing.md))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Items", font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.grid(row=1, column=0, sticky="ew", padx=theme.spacing.md)
        for col in range(5):
            add_row.grid_columnconfigure(col, weight=1)

        course_values = list(self._course_by_name.keys()) or [NO_COURSE_LABEL]
        self.course_field = FormField(add_row, "Course/Product", widget_factory=dropdown_factory(course_values))
        self.course_field.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))
        self.course_field.input.configure(command=self._on_course_selected)

        self.quantity_field = FormField(add_row, "Qty")
        self.quantity_field.set("1")
        self.quantity_field.grid(row=0, column=1, sticky="ew", padx=(0, theme.spacing.sm))

        self.rate_field = FormField(add_row, "Rate (₹)")
        self.rate_field.grid(row=0, column=2, sticky="ew", padx=(0, theme.spacing.sm))

        self.discount_field = FormField(add_row, "Discount (₹)")
        self.discount_field.set("0")
        self.discount_field.grid(row=0, column=3, sticky="ew", padx=(0, theme.spacing.sm))

        self.tax_field = FormField(add_row, "Tax %")
        self.tax_field.set("0")
        self.tax_field.grid(row=0, column=4, sticky="ew")

        if self._course_by_name:
            self._on_course_selected(course_values[0])

        PrimaryButton(card, text="Add Item", icon="+", command=self._add_item).grid(
            row=2, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.sm, 0)
        )

        self.items_table = DataTable(
            card,
            columns=[
                ("item_name", "Item", 180, "w"),
                ("quantity", "Qty", 60, "e"),
                ("rate", "Rate", 90, "e"),
                ("discount", "Discount", 90, "e"),
                ("tax_percentage", "Tax %", 70, "e"),
            ],
            on_row_context_menu=self._item_menu,
            empty_message="No items added yet",
        )
        self.items_table.grid(row=3, column=0, sticky="nsew", padx=theme.spacing.md, pady=theme.spacing.md)
        self.items_table.configure(height=160)

    def _on_course_selected(self, value: str) -> None:
        course = self._course_by_name.get(value)
        if not course:
            return
        self.rate_field.set(str(course["price"]))
        self.discount_field.set(str(course["discount"]))
        self.tax_field.set(str(course["gst_percentage"]))

    def _add_item(self) -> None:
        course_name = self.course_field.get()
        if course_name == NO_COURSE_LABEL or not course_name:
            show_toast(self.winfo_toplevel(), "Select a course/product first.", variant="error")
            return

        errors = validators.run_validators(
            validators.valid_numeric(self.quantity_field.get(), "Quantity"),
            validators.valid_numeric(self.rate_field.get(), "Rate"),
            validators.valid_numeric(self.discount_field.get(), "Discount"),
            validators.valid_numeric(self.tax_field.get(), "Tax %"),
        )
        if errors:
            show_toast(self.winfo_toplevel(), " ".join(errors), variant="error")
            return

        course = self._course_by_name.get(course_name)
        self._items.append(
            {
                "course_id": course["id"] if course else None,
                "item_name": course_name,
                "quantity": self.quantity_field.get().strip(),
                "rate": self.rate_field.get().strip(),
                "discount": self.discount_field.get().strip(),
                "tax_percentage": self.tax_field.get().strip(),
            }
        )
        self.quantity_field.set("1")
        self.rate_field.set("")
        self.discount_field.set("0")
        self.tax_field.set("0")
        self._refresh_items_table()
        self._refresh_summary()

    def _item_menu(self, row: dict) -> list[tuple[str, object]]:
        index = row["_index"]
        return [("Remove", lambda: self._remove_item(index))]

    def _remove_item(self, index: int) -> None:
        del self._items[index]
        self._refresh_items_table()
        self._refresh_summary()

    def _refresh_items_table(self) -> None:
        rows = [
            {
                "id": i,
                "_index": i,
                "item_name": item["item_name"],
                "quantity": item["quantity"],
                "rate": format_currency(Decimal(item["rate"] or 0)),
                "discount": format_currency(Decimal(item["discount"] or 0)),
                "tax_percentage": f"{item['tax_percentage']}%",
            }
            for i, item in enumerate(self._items)
        ]
        self.items_table.set_rows(rows)

    # ------------------------------------------------------------- summary
    def _build_summary_section(self) -> None:
        self.summary_card = Card(self.scroll)
        self.summary_card.grid(row=4, column=0, sticky="ew", pady=(0, theme.spacing.md))
        self.summary_card.grid_columnconfigure(1, weight=1)
        self.summary_labels: dict[str, ctk.CTkLabel] = {}

        rows = ["Subtotal", "Discount", "CGST", "SGST", "IGST", "Round Off", "Grand Total"]
        for i, label in enumerate(rows):
            is_total = label == "Grand Total"
            font = theme.fonts.body_bold if is_total else theme.fonts.body
            top_pad = theme.spacing.md if i == 0 else 2
            bottom_pad = theme.spacing.md if i == len(rows) - 1 else 2
            ctk.CTkLabel(self.summary_card, text=label, font=font, text_color=theme.colors.text_secondary).grid(
                row=i, column=0, sticky="w", padx=theme.spacing.md, pady=(top_pad, bottom_pad)
            )
            value_label = ctk.CTkLabel(self.summary_card, text="₹0.00", font=font, text_color=theme.colors.text)
            value_label.grid(row=i, column=1, sticky="e", padx=theme.spacing.md, pady=(top_pad, bottom_pad))
            self.summary_labels[label] = value_label

        self.summary_error_label = ctk.CTkLabel(
            self.summary_card, text="", font=theme.fonts.small, text_color=theme.colors.danger
        )
        self.summary_error_label.grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=theme.spacing.md, pady=(0, theme.spacing.sm))

    def _refresh_summary(self) -> None:
        if not self._items or not self._selected_customer:
            for widget in self.summary_labels.values():
                widget.configure(text=format_currency(Decimal("0")))
            return

        preview, error = invoice_controller.build_invoice_preview(self._selected_customer["id"], self._items)
        if preview is None:
            self.summary_error_label.configure(text=error)
            return

        self.summary_error_label.configure(text="")
        totals = preview["totals"]
        self.summary_labels["Subtotal"].configure(text=format_currency(totals.subtotal))
        self.summary_labels["Discount"].configure(text=format_currency(totals.discount_total))
        self.summary_labels["CGST"].configure(text=format_currency(totals.cgst_total))
        self.summary_labels["SGST"].configure(text=format_currency(totals.sgst_total))
        self.summary_labels["IGST"].configure(text=format_currency(totals.igst_total))
        self.summary_labels["Round Off"].configure(text=format_currency(totals.round_off))
        self.summary_labels["Grand Total"].configure(text=format_currency(totals.grand_total))

    # ------------------------------------------------------------- payment
    def _build_payment_section(self) -> None:
        card = Card(self.scroll)
        card.grid(row=5, column=0, sticky="ew", pady=(0, theme.spacing.md))
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(card, text="Initial Payment (optional)", font=theme.fonts.body_bold, text_color=theme.colors.text).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm)
        )
        self.payment_amount = FormField(card, "Amount Received Now (₹)")
        self.payment_amount.grid(row=1, column=0, sticky="ew", padx=(theme.spacing.md, theme.spacing.sm), pady=(0, theme.spacing.md))

        self.payment_mode = FormField(card, "Payment Mode", widget_factory=dropdown_factory(payment_controller.PAYMENT_MODES))
        self.payment_mode.grid(row=1, column=1, sticky="ew", padx=(0, theme.spacing.md), pady=(0, theme.spacing.md))

        self.notes_field = FormField(
            self.scroll, "Notes", widget_factory=lambda m: ctk.CTkTextbox(m, height=60, font=theme.fonts.body)
        )
        self.notes_field.grid(row=6, column=0, sticky="ew", pady=(0, theme.spacing.md))

    # ------------------------------------------------------------- actions
    def _build_actions(self) -> None:
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.grid(row=7, column=0, sticky="e", pady=(0, theme.spacing.lg))
        SecondaryButton(row, text="Cancel", command=self._confirm_cancel).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(row, text="Save Invoice", command=self._save).pack(side="right")

    def _confirm_cancel(self) -> None:
        if not self._items and not self._selected_customer:
            self._on_cancel()
            return
        ConfirmDialog(
            self.winfo_toplevel(),
            title="Discard Invoice",
            message="Discard this invoice? Any items you've added will be lost.",
            on_confirm=self._on_cancel,
            confirm_label="Discard",
        )

    def _save(self) -> None:
        if not self._selected_customer:
            show_toast(self.winfo_toplevel(), "Select a customer first.", variant="error")
            return
        if not self._items:
            show_toast(self.winfo_toplevel(), "Add at least one item.", variant="error")
            return

        date_error = validators.valid_date(self.invoice_date.get(), field_label="Invoice date")
        if date_error:
            show_toast(self.winfo_toplevel(), date_error, variant="error")
            return

        initial_payment = None
        amount_text = self.payment_amount.get().strip()
        if amount_text:
            try:
                amount = Decimal(amount_text)
            except InvalidOperation:
                show_toast(self.winfo_toplevel(), "Payment amount must be a number.", variant="error")
                return
            if amount > 0:
                initial_payment = {
                    "amount": amount_text,
                    "payment_mode": self.payment_mode.get(),
                    "payment_date": parse_date(self.invoice_date.get()),
                }

        success, message, _detail = invoice_controller.create_invoice(
            customer_id=self._selected_customer["id"],
            items=self._items,
            invoice_date=parse_date(self.invoice_date.get()),
            notes=self.notes_field.get().strip(),
            initial_payment=initial_payment,
        )
        if not success:
            show_toast(self.winfo_toplevel(), message, variant="error")
            return

        show_toast(self.winfo_toplevel(), "Invoice created successfully.", variant="success")
        self._on_saved()
