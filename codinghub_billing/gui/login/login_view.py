"""Login screen (Section 8)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from config import config
from controllers import auth_controller
from gui.components.buttons import PrimaryButton
from gui.theme import theme


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_login_success: Callable[[], None]):
        super().__init__(master, fg_color=theme.colors.background)
        self._on_login_success = on_login_success

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, fg_color=theme.colors.card, corner_radius=theme.spacing.radius + 4,
            border_width=1, border_color=theme.colors.border, width=400,
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(height=520)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="CodingHub", font=theme.fonts.logo, text_color=theme.colors.primary).grid(
            row=0, column=0, pady=(theme.spacing.xl, 0)
        )
        ctk.CTkLabel(
            card, text="Billing & Business Management", font=theme.fonts.small, text_color=theme.colors.text_secondary
        ).grid(row=1, column=0, pady=(2, theme.spacing.xl))

        self.username_entry = ctk.CTkEntry(
            card, placeholder_text="Username or email", width=300, height=38, font=theme.fonts.body
        )
        self.username_entry.grid(row=2, column=0, pady=(0, theme.spacing.sm))

        password_frame = ctk.CTkFrame(card, fg_color="transparent", width=300)
        password_frame.grid(row=3, column=0, pady=(0, theme.spacing.xs))
        password_frame.grid_columnconfigure(0, weight=1)

        self.password_entry = ctk.CTkEntry(
            password_frame, placeholder_text="Password", show="*", width=250, height=38, font=theme.fonts.body
        )
        self.password_entry.grid(row=0, column=0, sticky="ew")

        self._password_visible = False
        self.toggle_btn = ctk.CTkButton(
            password_frame, text="Show", width=48, height=38, font=theme.fonts.small,
            fg_color="transparent", text_color=theme.colors.primary, hover_color=theme.colors.background,
            command=self._toggle_password,
        )
        self.toggle_btn.grid(row=0, column=1, padx=(theme.spacing.xs, 0))

        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            card, text="Remember me", variable=self.remember_var, font=theme.fonts.small,
            text_color=theme.colors.text_secondary,
        ).grid(row=4, column=0, sticky="w", padx=50, pady=(theme.spacing.xs, theme.spacing.md))

        self.error_label = ctk.CTkLabel(card, text="", font=theme.fonts.small, text_color=theme.colors.danger)
        self.error_label.grid(row=5, column=0)

        self.login_button = PrimaryButton(card, text="Login", command=self._handle_login, width=300)
        self.login_button.grid(row=6, column=0, pady=(theme.spacing.sm, theme.spacing.lg))

        ctk.CTkLabel(
            card, text=f"Version {config.VERSION}", font=theme.fonts.small, text_color=theme.colors.text_secondary
        ).grid(row=7, column=0, pady=(0, theme.spacing.md))

        self.password_entry.bind("<Return>", lambda _e: self._handle_login())
        self.username_entry.bind("<Return>", lambda _e: self.password_entry.focus_set())

        remembered = auth_controller.get_remembered_username()
        if remembered:
            self.username_entry.insert(0, remembered)
            self.remember_var.set(True)
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()

    def _toggle_password(self) -> None:
        self._password_visible = not self._password_visible
        self.password_entry.configure(show="" if self._password_visible else "*")
        self.toggle_btn.configure(text="Hide" if self._password_visible else "Show")

    def _handle_login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Please enter both username and password.")
            return

        success, message = auth_controller.login(username, password)
        if not success:
            self.error_label.configure(text=message)
            return

        auth_controller.set_remembered_username(username if self.remember_var.get() else None)
        self.error_label.configure(text="")
        self._on_login_success()
