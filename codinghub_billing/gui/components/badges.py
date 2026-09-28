"""Status badge component (Section 20/44)."""
from __future__ import annotations

import customtkinter as ctk

from gui.theme import theme


class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, status: str, **kwargs):
        text_color, bg_color = theme.STATUS_COLORS.get(
            status.upper(), (theme.colors.text_secondary, theme.colors.background)
        )
        defaults = dict(
            text=f"  {status.upper()}  ",
            font=theme.fonts.small_bold,
            text_color=text_color,
            fg_color=bg_color,
            corner_radius=theme.spacing.radius,
            height=24,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)
