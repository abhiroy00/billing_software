"""Card + StatCard components (Section 10/44)."""
from __future__ import annotations

import customtkinter as ctk

from gui.theme import theme


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=theme.colors.card,
            corner_radius=theme.spacing.card_radius,
            border_width=1,
            border_color=theme.colors.border,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        try:
            self.bind("<Enter>", lambda _e: self.configure(border_color=theme.colors.primary), add="+")
            self.bind("<Leave>", lambda _e: self.configure(border_color=theme.colors.border), add="+")
        except Exception:
            pass


class StatCard(Card):
    """A single KPI tile: icon badge, label, animated big value, trend row."""

    def __init__(
        self,
        master,
        label: str,
        value: str,
        accent: str | None = None,
        subtext: str | None = None,
        icon: str = "📊",
        trend: str | None = None,
        animate: bool = True,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        accent = accent or theme.colors.primary

        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=theme.spacing.md, pady=(theme.spacing.md, 0))
        top.grid_columnconfigure(0, weight=1)

        badge = ctk.CTkLabel(
            top, text=icon, font=("Segoe UI", 20), text_color=accent,
            fg_color=_soft_for(accent), corner_radius=10, width=44, height=44,
        )
        badge.grid(row=0, column=0, sticky="w")

        trend_text = trend if trend is not None else (subtext or "")
        if trend_text:
            trend_color = accent if trend is None else _trend_color(trend_text, accent)
            ctk.CTkLabel(
                top, text=trend_text, font=theme.fonts.small_bold,
                text_color=trend_color, fg_color=_soft_for(trend_color),
                corner_radius=8, padx=8, pady=2,
            ).grid(row=0, column=1, sticky="e")

        self.label_widget = ctk.CTkLabel(
            self, text=label, font=theme.fonts.kpi_label,
            text_color=theme.colors.text_secondary, anchor="w",
        )
        self.label_widget.grid(row=1, column=0, sticky="w", padx=theme.spacing.md, pady=(theme.spacing.sm, 0))

        self.value_widget = ctk.CTkLabel(
            self, text=value, font=theme.fonts.kpi_value, text_color=theme.colors.text, anchor="w"
        )
        self.value_widget.grid(row=2, column=0, sticky="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        bar = ctk.CTkFrame(self, fg_color=accent, height=4, corner_radius=2)
        bar.grid(row=3, column=0, sticky="ew", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        if animate and value:
            try:
                from gui.components.animations import count_up

                count_up(self.value_widget, value)
            except Exception:
                pass

    def set_value(self, value: str) -> None:
        try:
            from gui.components.animations import count_up

            count_up(self.value_widget, value)
        except Exception:
            self.value_widget.configure(text=value)


def _soft_for(color: str) -> str:
    mapping = {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.warning: theme.colors.warning_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.primary: theme.colors.primary_soft,
    }
    return mapping.get(color, theme.colors.primary_soft)


def _trend_color(trend_text: str, fallback: str) -> str:
    lowered = trend_text.lower()
    if any(word in lowered for word in ("up", "▲", "+", "growth", "paid")):
        return theme.colors.success
    if any(word in lowered for word in ("down", "▼", "-", "due", "pending")):
        return theme.colors.danger
    return fallback
