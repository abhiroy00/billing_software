"""Invoice settings panel (Settings -> Invoice)."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from config import config
from controllers import settings_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.inputs import FormField
from gui.components.toast import show_toast
from gui.theme import theme
from utils.image_utils import save_uploaded_image


class InvoicePanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._signature_path: str | None = None

        card = Card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="🧾  Invoice Settings", font=theme.fonts.card_title,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            card, text="Prefix aur numbering yahin se control hote hain — naye invoice pe turant lagu.",
            font=theme.fonts.small, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        self.prefix = self._field(card, "Invoice Prefix", 2, 0, required=True)
        self.starting_number = self._field(card, "Starting Number", 2, 1, required=True)
        self.next_number = self._field(card, "Next Invoice Number", 3, 0, required=True)

        self.preview_label = ctk.CTkLabel(
            card, text="", font=theme.fonts.body_bold, text_color=theme.colors.primary,
            fg_color=theme.colors.primary_soft, corner_radius=8, anchor="w",
        )
        self.preview_label.grid(row=3, column=1, sticky="ew",
                                padx=(0, theme.spacing.md), pady=(0, theme.spacing.sm))

        self.terms = self._field_textbox(card, "Terms & Conditions", 4)
        self.footer_text = self._field(card, "Invoice Footer Text", 5, 0, colspan=2)

        sig_row = ctk.CTkFrame(card, fg_color="transparent")
        sig_row.grid(row=6, column=0, columnspan=2, sticky="ew",
                     padx=theme.spacing.md, pady=(theme.spacing.sm, 0))
        self.signature_status = ctk.CTkLabel(
            sig_row, text="No signature selected", font=theme.fonts.small,
            text_color=theme.colors.text_secondary,
        )
        self.signature_status.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(sig_row, text="Upload Signature", icon="✍", command=self._pick_signature).pack(side="left")
        SecondaryButton(sig_row, text="Remove", command=self._remove_signature).pack(
            side="left", padx=(theme.spacing.sm, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=7, column=0, columnspan=2, sticky="e",
                     padx=theme.spacing.md, pady=theme.spacing.md)
        PrimaryButton(btn_row, text="Save Invoice Settings", command=self._save).pack(side="right")

        self._load()
        for entry_field in (self.prefix, self.starting_number, self.next_number):
            try:
                entry_field.input.bind("<KeyRelease>", lambda _e: self._refresh_preview())
            except Exception:
                pass

    def _field(self, master, label, row, col, required=False, colspan=1):
        field = FormField(master, label, required=required)
        if colspan == 2:
            padx = (theme.spacing.md, theme.spacing.md)
        elif col == 0:
            padx = (theme.spacing.md, theme.spacing.sm)
        else:
            padx = (0, theme.spacing.md)
        field.grid(row=row, column=col, columnspan=colspan, sticky="ew",
                   padx=padx, pady=(0, theme.spacing.sm))
        return field

    def _field_textbox(self, master, label, row):
        field = FormField(
            master, label,
            widget_factory=lambda m: ctk.CTkTextbox(m, height=70, font=theme.fonts.body),
        )
        field.grid(row=row, column=0, columnspan=2, sticky="ew",
                   padx=(theme.spacing.md, theme.spacing.md), pady=(0, theme.spacing.sm))
        return field

    def _load(self) -> None:
        data = settings_controller.get_invoice()
        self.prefix.set(data.get("prefix") or "")
        self.starting_number.set(str(data.get("starting_number") or 1))
        self.next_number.set(str(data.get("next_number") or 1))
        self.terms.set(data.get("terms") or "")
        self.footer_text.set(data.get("footer_text") or "")
        self._signature_path = data.get("signature_path")
        self._refresh_signature_status()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        try:
            nxt = int(float(self.next_number.get() or 1))
        except (TypeError, ValueError):
            nxt = 1
        preview = settings_controller.preview_next_invoice_number(self.prefix.get(), nxt)
        self.preview_label.configure(text=f"  Next invoice: {preview}  ")

    def _refresh_signature_status(self) -> None:
        if self._signature_path and Path(self._signature_path).is_file():
            self.signature_status.configure(
                text=f"✔ {Path(self._signature_path).name}", text_color=theme.colors.success)
        elif self._signature_path:
            self.signature_status.configure(
                text="Saved signature file missing — re-upload karo.",
                text_color=theme.colors.warning)
        else:
            self.signature_status.configure(
                text="No signature selected", text_color=theme.colors.text_secondary)

    def _pick_signature(self) -> None:
        path = filedialog.askopenfilename(
            title="Select authorized signature image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")],
        )
        if not path:
            return
        try:
            self._signature_path = save_uploaded_image(
                path, config.config_dir, "signature.png", max_size=(300, 150))
            self._refresh_signature_status()
        except ValueError as exc:
            show_toast(self.winfo_toplevel(), str(exc), variant="error")

    def _remove_signature(self) -> None:
        self._signature_path = None
        self._refresh_signature_status()

    def _save(self) -> None:
        for field in (self.prefix, self.starting_number, self.next_number):
            field.clear_error()
        data = {
            "prefix": self.prefix.get().strip(),
            "starting_number": self.starting_number.get().strip(),
            "next_number": self.next_number.get().strip(),
            "terms": self.terms.get(),
            "footer_text": self.footer_text.get().strip(),
            "signature_path": self._signature_path,
        }
        success, message, saved = settings_controller.save_invoice(data)
        if not success:
            self._apply_field_errors(message)
            return
        self.prefix.set((saved or {}).get("prefix", ""))
        self.starting_number.set(str((saved or {}).get("starting_number", 1)))
        self.next_number.set(str((saved or {}).get("next_number", 1)))
        self._refresh_preview()
        show_toast(self.winfo_toplevel(), "Invoice settings saved.", variant="success")

    def _apply_field_errors(self, message: str) -> None:
        field_by_keyword = {
            "prefix": self.prefix,
            "starting": self.starting_number,
            "next invoice": self.next_number,
            "next": self.next_number,
        }
        unmatched = []
        for sentence in message.split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue
            lowered = sentence.lower()
            field = next((f for keyword, f in field_by_keyword.items() if keyword in lowered), None)
            if field:
                field.set_error(sentence if sentence.endswith(".") else f"{sentence}.")
            else:
                unmatched.append(sentence)
        if unmatched:
            show_toast(self.winfo_toplevel(), " ".join(unmatched), variant="error")
