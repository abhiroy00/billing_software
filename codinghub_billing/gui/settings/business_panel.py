"""Business profile panel (Settings -> Business)."""
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


class BusinessPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._logo_path: str | None = None

        card = Card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="🏢  Business Profile", font=theme.fonts.card_title,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            card, text="Ye details har invoice aur receipt pe print hongi.",
            font=theme.fonts.small, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        self.business_name = self._field(card, "Business Name", 2, 0, colspan=2, required=True)
        self.phone = self._field(card, "Phone", 3, 0)
        self.email = self._field(card, "Email", 3, 1)
        self.gstin = self._field(card, "GSTIN", 4, 0)
        self.pan = self._field(card, "PAN", 4, 1)
        self.address = self._field(card, "Address", 5, 0, colspan=2)
        self.state = self._field(card, "State", 6, 0)
        self.state_code = self._field(card, "State Code", 6, 1)

        logo_row = ctk.CTkFrame(card, fg_color="transparent")
        logo_row.grid(row=7, column=0, columnspan=2, sticky="ew",
                      padx=theme.spacing.md, pady=(theme.spacing.sm, 0))
        self.logo_status = ctk.CTkLabel(
            logo_row, text="No logo selected", font=theme.fonts.small,
            text_color=theme.colors.text_secondary,
        )
        self.logo_status.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(logo_row, text="Upload Logo", icon="🖼", command=self._pick_logo).pack(side="left")
        SecondaryButton(logo_row, text="Remove", command=self._remove_logo).pack(
            side="left", padx=(theme.spacing.sm, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=8, column=0, columnspan=2, sticky="e",
                     padx=theme.spacing.md, pady=theme.spacing.md)
        PrimaryButton(btn_row, text="Save Business Profile", command=self._save).pack(side="right")

        self._load()

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

    def _load(self) -> None:
        data = settings_controller.get_business()
        self.business_name.set(data.get("business_name") or "")
        self.phone.set(data.get("phone") or "")
        self.email.set(data.get("email") or "")
        self.gstin.set(data.get("gstin") or "")
        self.pan.set(data.get("pan") or "")
        self.address.set(data.get("address") or "")
        self.state.set(data.get("state") or "")
        self.state_code.set(data.get("state_code") or "")
        self._logo_path = data.get("logo_path")
        self._refresh_logo_status()

    def _refresh_logo_status(self) -> None:
        if self._logo_path and Path(self._logo_path).is_file():
            self.logo_status.configure(
                text=f"✔ {Path(self._logo_path).name}", text_color=theme.colors.success)
        elif self._logo_path:
            self.logo_status.configure(
                text="Saved logo file missing — re-upload karo.",
                text_color=theme.colors.warning)
        else:
            self.logo_status.configure(
                text="No logo selected", text_color=theme.colors.text_secondary)

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Select business logo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")],
        )
        if not path:
            return
        try:
            self._logo_path = save_uploaded_image(path, config.config_dir, "logo.png")
            self._refresh_logo_status()
        except ValueError as exc:
            show_toast(self.winfo_toplevel(), str(exc), variant="error")

    def _remove_logo(self) -> None:
        self._logo_path = None
        self._refresh_logo_status()

    def _save(self) -> None:
        for field in (self.business_name, self.email, self.gstin, self.pan):
            field.clear_error()
        data = {
            "business_name": self.business_name.get().strip(),
            "phone": self.phone.get().strip(),
            "email": self.email.get().strip(),
            "gstin": self.gstin.get().strip(),
            "pan": self.pan.get().strip(),
            "address": self.address.get().strip(),
            "state": self.state.get().strip(),
            "state_code": self.state_code.get().strip(),
            "logo_path": self._logo_path,
        }
        success, message, saved = settings_controller.save_business(data)
        if not success:
            self._apply_field_errors(message)
            return
        self._logo_path = (saved or {}).get("logo_path", self._logo_path)
        self._refresh_logo_status()
        show_toast(self.winfo_toplevel(), "Business profile saved.", variant="success")

    def _apply_field_errors(self, message: str) -> None:
        field_by_keyword = {
            "business name": self.business_name,
            "email": self.email,
            "gstin": self.gstin,
            "pan": self.pan,
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
