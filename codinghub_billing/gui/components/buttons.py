"""Reusable button variants (Section 44). Buttons should use icon + text,
never an icon alone (Section 34/35)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from gui.theme import theme


class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable | None = None, icon: str = "", **kwargs):
        label = f"{icon}  {text}".strip() if icon else text
        defaults = dict(
            fg_color=theme.colors.primary,
            hover_color=theme.colors.primary_hover,
            text_color=theme.colors.white,
            font=theme.fonts.button,
            corner_radius=theme.spacing.radius,
            height=38,
        )
        defaults.update(kwargs)
        super().__init__(master, text=label, command=command, **defaults)


class SecondaryButton(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable | None = None, icon: str = "", **kwargs):
        label = f"{icon}  {text}".strip() if icon else text
        defaults = dict(
            fg_color="transparent",
            hover_color=theme.colors.background,
            text_color=theme.colors.text,
            border_width=1,
            border_color=theme.colors.border,
            font=theme.fonts.button,
            corner_radius=theme.spacing.radius,
            height=38,
        )
        defaults.update(kwargs)
        super().__init__(master, text=label, command=command, **defaults)


class DangerButton(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable | None = None, icon: str = "", **kwargs):
        label = f"{icon}  {text}".strip() if icon else text
        defaults = dict(
            fg_color=theme.colors.danger,
            hover_color=theme.colors.danger_hover,
            text_color=theme.colors.white,
            font=theme.fonts.button,
            corner_radius=theme.spacing.radius,
            height=38,
        )
        defaults.update(kwargs)
        super().__init__(master, text=label, command=command, **defaults)
