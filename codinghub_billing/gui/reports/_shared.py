"""Small helpers shared by every report panel (Section 50)."""
from __future__ import annotations

from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from gui.components.buttons import SecondaryButton
from gui.components.toast import show_toast
from gui.theme import theme


def build_export_row(
    master,
    get_data: Callable[[], dict],
    export_excel_fn: Callable[[str, str, dict], tuple[bool, str]],
    filename_prefix: str,
) -> ctk.CTkFrame:
    row = ctk.CTkFrame(master, fg_color="transparent")

    def _export(fmt: str) -> None:
        ext = "xlsx" if fmt == "excel" else "csv"
        filetypes = [("Excel Workbook", "*.xlsx")] if fmt == "excel" else [("CSV file", "*.csv")]
        path = filedialog.asksaveasfilename(
            title=f"Export {filename_prefix}", defaultextension=f".{ext}", filetypes=filetypes
        )
        if not path:
            return
        success, message = export_excel_fn(path, fmt, get_data())
        root = master.winfo_toplevel()
        if success:
            show_toast(root, f"{filename_prefix} exported successfully.", variant="success")
        else:
            show_toast(root, message, variant="error")

    SecondaryButton(row, text="Export Excel", icon="\U0001F4E4", command=lambda: _export("excel")).pack(
        side="left", padx=(0, theme.spacing.sm)
    )
    SecondaryButton(row, text="Export CSV", icon="\U0001F4C4", command=lambda: _export("csv")).pack(side="left")
    return row


def build_summary_row(master, cards: list[tuple[str, str, str]]) -> ctk.CTkFrame:
    """cards: list of (label, value, accent_color). Icons auto-attached."""
    from gui.components.cards import StatCard

    row = ctk.CTkFrame(master, fg_color="transparent")
    row.grid_columnconfigure(tuple(range(len(cards))), weight=1, uniform="report_stat")
    widgets = []
    for i, (label, value, accent) in enumerate(cards):
        pad_left = 0 if i == 0 else theme.spacing.sm
        pad_right = 0 if i == len(cards) - 1 else theme.spacing.sm
        card = StatCard(row, f"{_icon_for(label)} {label}", value, accent=accent)
        card.grid(row=0, column=i, sticky="nsew", padx=(pad_left, pad_right))
        widgets.append(card)
    try:
        from gui.components.animations import stagger_in

        stagger_in(widgets, delay_ms=70)
    except Exception:
        pass
    return row


def _icon_for(label: str) -> str:
    upper = label.upper()
    for keyword, icon in _LABEL_ICONS:
        if keyword in upper:
            return icon
    return "📊"


_LABEL_ICONS = (
    ("INVOICE", "🧾"),
    ("SALES", "💰"),
    ("COLLECTED", "✅"),
    ("REVENUE", "💰"),
    ("OUTSTANDING", "⏳"),
    ("DUE", "⏳"),
    ("PENDING", "⏳"),
    ("TAXABLE", "📊"),
    ("CGST", "🏛️"),
    ("SGST", "🏛️"),
    ("IGST", "🏛️"),
    ("TAX", "🏛️"),
    ("EXPENSE", "🧮"),
    ("PAYMENT", "💳"),
    ("CUSTOMER", "👥"),
    ("PROFIT", "📈"),
    ("LOSS", "📉"),
    ("COURSE", "📚"),
)
