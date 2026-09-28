"""Preferences panel (Settings -> Preferences): default GST % + appearance."""
from __future__ import annotations

import customtkinter as ctk

from config import config
from controllers import settings_controller
from gui.components.buttons import PrimaryButton
from gui.components.cards import Card
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme
from services.settings_service import APPEARANCE_MODES


class PreferencesPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        card = Card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="🎛️  Preferences", font=theme.fonts.card_title,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            card, text="Tax 0% fixed hai. Appearance turant lagu hota hai.",
            font=theme.fonts.small, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w",
               padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        tax_values = ["0"]
        self.default_tax = FormField(
            card, "Default GST % (Fixed 0)", widget_factory=dropdown_factory(tax_values))
        self.default_tax.grid(row=2, column=0, sticky="ew",
                              padx=(theme.spacing.md, theme.spacing.sm),
                              pady=(0, theme.spacing.sm))

        self.appearance = FormField(
            card, "Appearance", widget_factory=dropdown_factory(list(APPEARANCE_MODES)))
        self.appearance.grid(row=2, column=1, sticky="ew",
                             padx=(0, theme.spacing.md), pady=(0, theme.spacing.sm))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e",
                     padx=theme.spacing.md, pady=theme.spacing.md)
        PrimaryButton(btn_row, text="Save Preferences", command=self._save).pack(side="right")

        self._load()
        try:
            self.default_tax.input.configure(state="disabled")
        except Exception:
            pass

    def _load(self) -> None:
        prefs = settings_controller.get_preferences()
        try:
            self.default_tax.set("0")
        except Exception:
            pass
        try:
            self.appearance.set(str(prefs.get("appearance_mode") or "Light"))
        except Exception:
            pass

    def _save(self) -> None:
        self.default_tax.clear_error()
        data = {
            "default_tax_rate": "0",
            "appearance_mode": self.appearance.get().strip(),
        }
        success, message, _saved = settings_controller.save_preferences(data)
        if not success:
            lowered = message.lower()
            if "gst" in lowered:
                self.default_tax.set_error(message)
            else:
                show_toast(self.winfo_toplevel(), message, variant="error")
            return
        show_toast(self.winfo_toplevel(), "Preferences saved.", variant="success")
