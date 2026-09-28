"""Login screen (Section 8) — modern split-screen design."""
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

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=0, column=0)
        wrapper.grid_columnconfigure((0, 1), weight=1)

        self._build_brand_panel(wrapper)
        self._build_form_card(wrapper)

        remembered = auth_controller.get_remembered_username()
        if remembered:
            self.username_entry.insert(0, remembered)
            self.remember_var.set(True)
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()

        try:
            self.after(30, self._entrance)
        except Exception:
            pass

    # ------------------------------------------------------------ left panel
    def _build_brand_panel(self, parent) -> None:
        panel = ctk.CTkFrame(
            parent, fg_color=theme.colors.secondary, corner_radius=theme.spacing.card_radius,
            width=380, height=560,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, theme.spacing.md))
        panel.grid_propagate(False)

        ctk.CTkLabel(
            panel, text="CH", font=("Segoe UI", 22, "bold"),
            text_color=theme.colors.white, fg_color=theme.colors.primary,
            corner_radius=14, width=56, height=56,
        ).pack(pady=(theme.spacing.xxl, theme.spacing.md))

        ctk.CTkLabel(
            panel, text="CodingHub", font=theme.fonts.hero, text_color=theme.colors.white
        ).pack()
        ctk.CTkLabel(
            panel, text="Billing & Business Management",
            font=theme.fonts.body, text_color="#94A3B8",
        ).pack(pady=(4, theme.spacing.xl))

        for bullet in ("🧾  GST-ready invoices in seconds", "💰  Payments, dues & expenses tracking", "📊  Reports that grow your business"):
            row = ctk.CTkFrame(panel, fg_color="#141D33", corner_radius=10)
            row.pack(fill="x", padx=theme.spacing.lg, pady=4)
            ctk.CTkLabel(
                row, text=bullet, font=theme.fonts.body, text_color="#E2E8F0", anchor="w"
            ).pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.sm)

        ctk.CTkLabel(
            panel, text=f"✨ Trusted billing suite  •  v{config.VERSION}",
            font=theme.fonts.small, text_color="#64748B",
        ).pack(side="bottom", pady=theme.spacing.lg)

    # ----------------------------------------------------------- right panel
    def _build_form_card(self, parent) -> None:
        card = ctk.CTkFrame(
            parent, fg_color=theme.colors.card, corner_radius=theme.spacing.card_radius,
            border_width=1, border_color=theme.colors.border, width=400, height=560,
        )
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        self._form_card = card

        ctk.CTkLabel(card, text="Welcome back 👋", font=theme.fonts.page_heading, text_color=theme.colors.text).grid(
            row=0, column=0, pady=(theme.spacing.xxl, 0)
        )
        ctk.CTkLabel(
            card, text="Login to continue to your dashboard", font=theme.fonts.small, text_color=theme.colors.text_secondary
        ).grid(row=1, column=0, pady=(4, theme.spacing.xl))

        self.username_entry = ctk.CTkEntry(
            card, placeholder_text="Username or email", width=300, height=42, font=theme.fonts.body,
            corner_radius=theme.spacing.radius, border_color=theme.colors.border,
        )
        self.username_entry.grid(row=2, column=0, pady=(0, theme.spacing.sm))

        password_frame = ctk.CTkFrame(card, fg_color="transparent", width=300)
        password_frame.grid(row=3, column=0, pady=(0, theme.spacing.xs))
        password_frame.grid_columnconfigure(0, weight=1)

        self.password_entry = ctk.CTkEntry(
            password_frame, placeholder_text="Password", show="*", width=250, height=42, font=theme.fonts.body,
            corner_radius=theme.spacing.radius, border_color=theme.colors.border,
        )
        self.password_entry.grid(row=0, column=0, sticky="ew")

        self._password_visible = False
        self.toggle_btn = ctk.CTkButton(
            password_frame, text="Show", width=48, height=42, font=theme.fonts.small,
            fg_color="transparent", text_color=theme.colors.primary, hover_color=theme.colors.primary_soft,
            command=self._toggle_password,
        )
        self.toggle_btn.grid(row=0, column=1, padx=(theme.spacing.xs, 0))

        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            card, text="Remember me", variable=self.remember_var, font=theme.fonts.small,
            text_color=theme.colors.text_secondary, fg_color=theme.colors.primary,
            hover_color=theme.colors.primary_hover,
        ).grid(row=4, column=0, sticky="w", padx=50, pady=(theme.spacing.xs, theme.spacing.md))

        self.error_label = ctk.CTkLabel(card, text="", font=theme.fonts.small, text_color=theme.colors.danger)
        self.error_label.grid(row=5, column=0)

        self.login_button = PrimaryButton(card, text="→  Login", command=self._handle_login, width=300, height=44)
        self.login_button.grid(row=6, column=0, pady=(theme.spacing.sm, theme.spacing.md))

        ctk.CTkLabel(
            card, text=f"🔒 Secure login  •  Version {config.VERSION}",
            font=theme.fonts.small, text_color=theme.colors.text_secondary,
        ).grid(row=7, column=0, pady=(0, theme.spacing.md))

        self.password_entry.bind("<Return>", lambda _e: self._handle_login())
        self.username_entry.bind("<Return>", lambda _e: self.password_entry.focus_set())

    def _entrance(self) -> None:
        try:
            from gui.components.animations import pulse

            pulse(self.login_button, theme.colors.primary, theme.colors.primary_hover, cycles=1)
        except Exception:
            pass

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
            try:
                self._form_card.after(60, lambda: self._form_card.configure(border_color=theme.colors.danger))
                self._form_card.after(600, lambda: self._form_card.configure(border_color=theme.colors.border))
            except Exception:
                pass
            return

        auth_controller.set_remembered_username(username if self.remember_var.get() else None)
        self.error_label.configure(text="")
        self._on_login_success()
