"""Modal dialog base + ConfirmDialog (Section 21/36/44)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from gui.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from gui.theme import theme


class Modal(ctk.CTkToplevel):
    def __init__(
        self, master, title: str, width: int = 420, height: int = 220, resizable: bool = False, scrollable: bool = False
    ):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(resizable, resizable)
        self.configure(fg_color=theme.colors.card)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkLabel(self, text=title, font=theme.fonts.section_heading, text_color=theme.colors.text)
        self.header.grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        if scrollable:
            self.scroll_body = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
            self.scroll_body.grid(row=0, column=0, sticky="nsew")
        else:
            self.scroll_body = self.body

        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=2, column=0, sticky="e", padx=theme.spacing.lg, pady=theme.spacing.lg)

        self._center_over(master)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _center_over(self, master) -> None:
        self.update_idletasks()
        try:
            mx, my = master.winfo_rootx(), master.winfo_rooty()
            mw, mh = master.winfo_width(), master.winfo_height()
            w, h = self.winfo_width(), self.winfo_height()
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass


class ConfirmDialog(Modal):
    def __init__(
        self,
        master,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
        confirm_label: str = "Delete",
        danger: bool = True,
    ):
        super().__init__(master, title=title, width=420, height=200)

        message_label = ctk.CTkLabel(
            self.body,
            text=message,
            font=theme.fonts.body,
            text_color=theme.colors.text_secondary,
            wraplength=360,
            justify="left",
        )
        message_label.pack(anchor="w")

        def confirm_and_close():
            self.destroy()
            on_confirm()

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        button_cls = DangerButton if danger else PrimaryButton
        button_cls(self.actions, text=confirm_label, command=confirm_and_close).pack(side="right")
