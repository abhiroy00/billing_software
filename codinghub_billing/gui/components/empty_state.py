"""Empty state component (Section 33). Every empty table/list should show
this instead of a blank screen."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from gui.theme import theme


class EmptyState(ctk.CTkFrame):
    def __init__(
        self,
        master,
        message: str,
        icon: str = "\U0001F4C4",
        action_label: str | None = None,
        on_action: Callable[[], None] | None = None,
        **kwargs,
    ):
        defaults = dict(fg_color="transparent")
        defaults.update(kwargs)
        super().__init__(master, **defaults)

        self.icon_label = ctk.CTkLabel(self, text=icon, font=("Segoe UI", 40), text_color=theme.colors.text_secondary)
        self.icon_label.pack(pady=(theme.spacing.md, theme.spacing.sm))

        self.message_label = ctk.CTkLabel(
            self, text=message, font=theme.fonts.body, text_color=theme.colors.text_secondary
        )
        self.message_label.pack(pady=(0, theme.spacing.md))

        if action_label and on_action:
            from gui.components.buttons import PrimaryButton

            self.action_button = PrimaryButton(self, text=action_label, command=on_action, icon="+")
            self.action_button.pack()
