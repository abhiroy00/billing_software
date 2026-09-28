"""Reusable Excel/CSV import dialog: template download + file pick +
result summary with per-row errors. One dialog serves every list view."""
from __future__ import annotations

from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.toast import show_toast
from gui.theme import theme


class ImportDialog(Modal):
    """template_fn(path) -> (ok, msg); import_fn(path) -> (count, errors[, warnings])."""

    def __init__(
        self,
        master,
        title: str,
        entity_name: str,
        template_filename: str,
        template_fn: Callable[[str], tuple[bool, str]],
        import_fn: Callable[[str], tuple],
        on_done: Callable[[], None] | None = None,
    ):
        super().__init__(master, title=title, width=520, height=480, resizable=True, scrollable=True)
        self._template_fn = template_fn
        self._import_fn = import_fn
        self._on_done = on_done
        self._template_filename = template_filename

        ctk.CTkLabel(
            self.scroll_body,
            text=f"1️⃣  Download the {entity_name} template\n2️⃣  Fill one row per {entity_name.lower()} (keep the header)\n3️⃣  Choose the file below to import",
            font=theme.fonts.body, text_color=theme.colors.text, anchor="w", justify="left",
        ).pack(fill="x", pady=(0, theme.spacing.md))

        btn_row = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, theme.spacing.md))
        SecondaryButton(btn_row, text="📥  Download Template", command=self._download_template).pack(
            side="left", padx=(0, theme.spacing.sm)
        )
        PrimaryButton(btn_row, text="📂  Choose File & Import", command=self._choose_and_import).pack(side="left")

        self.result_box = ctk.CTkTextbox(self.scroll_body, height=180, font=theme.fonts.body)
        self.result_box.pack(fill="both", expand=True)
        self.result_box.insert("1.0", "Result will appear here…")
        self.result_box.configure(state="disabled")

        SecondaryButton(self.actions, text="Close", command=self.destroy).pack(side="right")

    def _download_template(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save import template", initialfile=self._template_filename,
            defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not path:
            return
        success, message = self._template_fn(path)
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Template downloaded. Fill it and import.", variant="success")
        else:
            show_toast(root, message, variant="error")

    def _choose_and_import(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose file to import",
            filetypes=[("Excel / CSV", "*.xlsx *.csv"), ("Excel Workbook", "*.xlsx"), ("CSV file", "*.csv")],
        )
        if not path:
            return
        result = self._import_fn(path)
        count, errors = result[0], result[1]
        warnings = list(result[2]) if len(result) > 2 else []
        lines = [f"✅ Imported {count} record(s)."]
        for warn in warnings:
            lines.append(f"ℹ️ {warn}")
        if errors:
            lines.append(f"⚠️ {len(errors)} problem(s):")
            lines.extend(f"• {err}" for err in errors)
        elif not warnings:
            lines.append("No errors — clean import! 🎉")
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "\n".join(lines))
        self.result_box.configure(state="disabled")

        root = self.winfo_toplevel()
        if count and not errors:
            show_toast(root, f"{count} record(s) imported successfully.", variant="success")
        elif count:
            show_toast(root, f"{count} imported, {len(errors)} skipped — see details.", variant="error")
        else:
            show_toast(root, "Nothing imported — fix the errors and retry.", variant="error")
        if count and self._on_done:
            self._on_done()
