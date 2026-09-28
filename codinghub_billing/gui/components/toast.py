"""Transient success/error/warning/info notifications (Section 21/44)."""
from __future__ import annotations

import customtkinter as ctk

from gui.theme import theme

_VARIANTS = {
    "success": (theme.colors.success, "✔"),
    "error": (theme.colors.danger, "✖"),
    "warning": (theme.colors.warning, "⚠"),
    "info": (theme.colors.info, "ℹ"),
}


def show_toast(root, message: str, variant: str = "success", duration_ms: int = 2600) -> None:
    color, glyph = _VARIANTS.get(variant, _VARIANTS["info"])

    toast = ctk.CTkFrame(root, fg_color=color, corner_radius=theme.spacing.radius)
    label = ctk.CTkLabel(
        toast,
        text=f"{glyph}  {message}",
        font=theme.fonts.body_bold,
        text_color=theme.colors.white,
    )
    label.pack(padx=theme.spacing.md, pady=theme.spacing.sm)

    root.update_idletasks()
    toast.place(relx=0.5, rely=0.96, anchor="s")
    toast.lift()
    toast.after(duration_ms, toast.destroy)
