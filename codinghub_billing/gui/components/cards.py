"""Card + StatCard components (Section 10/44)."""
from __future__ import annotations

import customtkinter as ctk

from gui.theme import theme


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=theme.colors.card,
            corner_radius=theme.spacing.radius,
            border_width=1,
            border_color=theme.colors.border,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class StatCard(Card):
    """A single KPI tile: label, big value, optional accent color + subtext."""

    def __init__(
        self,
        master,
        label: str,
        value: str,
        accent: str | None = None,
        subtext: str | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        accent = accent or theme.colors.primary

        self.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(self, fg_color=accent, width=4, corner_radius=2, height=1)
        bar.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(0, 0), pady=theme.spacing.sm)

        self.label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=theme.fonts.small_bold,
            text_color=theme.colors.text_secondary,
            anchor="w",
        )
        self.label_widget.grid(
            row=0, column=1, sticky="w", padx=(theme.spacing.md, theme.spacing.md), pady=(theme.spacing.md, 0)
        )

        self.value_widget = ctk.CTkLabel(
            self, text=value, font=theme.fonts.kpi_value, text_color=theme.colors.text, anchor="w"
        )
        self.value_widget.grid(row=1, column=1, sticky="w", padx=(theme.spacing.md, theme.spacing.md))

        if subtext:
            self.subtext_widget = ctk.CTkLabel(
                self, text=subtext, font=theme.fonts.small, text_color=theme.colors.text_secondary, anchor="w"
            )
            self.subtext_widget.grid(
                row=2, column=1, sticky="w", padx=(theme.spacing.md, theme.spacing.md), pady=(0, theme.spacing.md)
            )
        else:
            ctk.CTkLabel(self, text="", height=theme.spacing.md).grid(row=2, column=1)

    def set_value(self, value: str) -> None:
        self.value_widget.configure(text=value)
