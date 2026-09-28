"""Settings module container (Section 26): Business | Invoice | Backup |
Preferences tabs, same segmented-selector pattern as Reports."""
from __future__ import annotations

import customtkinter as ctk

from gui.settings.backup_panel import BackupPanel
from gui.settings.business_panel import BusinessPanel
from gui.settings.invoice_panel import InvoicePanel
from gui.settings.preferences_panel import PreferencesPanel
from gui.theme import theme

SETTING_PANELS: dict[str, type[ctk.CTkFrame]] = {
    "Business": BusinessPanel,
    "Invoice": InvoicePanel,
    "Backup": BackupPanel,
    "Preferences": PreferencesPanel,
}


class SettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._current: ctk.CTkFrame | None = None

        ctk.CTkLabel(
            self, text="⚙️  Settings", font=theme.fonts.page_heading,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        ctk.CTkLabel(
            self, text="Business, invoice, backup aur preferences — sab ek jagah.",
            font=theme.fonts.body, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=theme.spacing.lg, pady=(2, theme.spacing.sm))

        self.selector = ctk.CTkSegmentedButton(
            self, values=list(SETTING_PANELS.keys()), command=self._show, font=theme.fonts.body
        )
        self.selector.grid(row=2, column=0, sticky="w", padx=theme.spacing.lg, pady=(0, theme.spacing.sm))

        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=3, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        self.content.grid_columnconfigure(0, weight=1)

        first_key = next(iter(SETTING_PANELS))
        self.selector.set(first_key)
        self._show(first_key)

    def _show(self, key: str) -> None:
        if self._current is not None:
            self._current.destroy()
        panel_cls = SETTING_PANELS[key]
        self._current = panel_cls(self.content)
        self._current.grid(row=0, column=0, sticky="nsew")
