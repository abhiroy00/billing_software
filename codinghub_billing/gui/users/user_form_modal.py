"""Add/Edit User modal (Section 23)."""
from __future__ import annotations

from typing import Callable

from controllers import user_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme
from services import auth_service

STATUS_OPTIONS = ["Active", "Inactive"]


class UserFormModal(Modal):
    def __init__(self, master, user_id: int | None = None, on_saved: Callable[[dict], None] | None = None):
        title = "Edit User" if user_id else "New User"
        super().__init__(master, title=title, width=480, height=520, resizable=True, scrollable=True)
        self._user_id = user_id
        self._on_saved = on_saved
        self._editing_self = user_id is not None and user_id == auth_service.current_session.user_id

        roles = user_controller.list_roles()
        self._role_name_to_id = {r["name"]: r["id"] for r in roles}
        role_values = list(self._role_name_to_id.keys())

        self.scroll_body.grid_columnconfigure(0, weight=1)

        self._section_label("👤 Profile")
        self.full_name = self._field("Full Name", required=True)
        self.username = self._field("Username", required=True)
        self.email = self._field("Email")
        self._section_label("🛡️ Access & Security")
        self.role = self._field("Role", widget_factory=dropdown_factory(role_values))
        self.password = self._field(
            "Password" if not user_id else "New Password (leave blank to keep current)",
            required=not user_id, show="*",
        )
        self.confirm_password = self._field("Confirm Password", required=not user_id, show="*")

        if user_id:
            self.status = self._field("Status", widget_factory=dropdown_factory(STATUS_OPTIONS))
            if self._editing_self:
                self.status.input.configure(state="disabled")
        else:
            self.status = None

        if user_id:
            self._load_existing(user_id)

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Save User", command=self._save).pack(side="right")

    def _section_label(self, text: str) -> None:
        import customtkinter as ctk

        ctk.CTkLabel(
            self.scroll_body, text=text, font=theme.fonts.card_title,
            text_color=theme.colors.primary, anchor="w",
        ).pack(fill="x", pady=(theme.spacing.sm, theme.spacing.xs))

    def _field(self, label, required=False, show=None, widget_factory=None):
        field = FormField(self.scroll_body, label, required=required, show=show, widget_factory=widget_factory)
        field.pack(fill="x", pady=(0, theme.spacing.sm))
        return field

    def _load_existing(self, user_id: int) -> None:
        user = user_controller.get_user(user_id)
        if not user:
            return
        self.full_name.set(user["full_name"])
        self.username.set(user["username"])
        self.email.set(user["email"] or "")
        self.role.set(user["role_name"])
        if self.status:
            self.status.set("Active" if user["is_active"] else "Inactive")

    def _save(self) -> None:
        for field in (self.full_name, self.username, self.email, self.password, self.confirm_password):
            field.clear_error()

        password = self.password.get()
        confirm = self.confirm_password.get()
        password_error = None
        if not self._user_id and not password:
            password_error = "Password is required."
        elif password and len(password) < 6:
            password_error = "Password must be at least 6 characters."
        confirm_error = "Passwords do not match." if password and confirm != password else None

        if password_error:
            self.password.set_error(password_error)
        if confirm_error:
            self.confirm_password.set_error(confirm_error)
        if password_error or confirm_error:
            return

        data = {
            "full_name": self.full_name.get().strip(),
            "username": self.username.get().strip(),
            "email": self.email.get().strip(),
            "role_id": self._role_name_to_id.get(self.role.get()),
        }
        if password:
            data["password"] = password
        if self.status:
            data["is_active"] = self.status.get() == "Active"

        if self._user_id:
            success, message, user = user_controller.update_user(self._user_id, data)
        else:
            success, message, user = user_controller.create_user(data)

        if not success:
            self._apply_field_errors(message)
            return

        show_toast(self.master, "User saved successfully.", variant="success")
        if self._on_saved:
            self._on_saved(user)
        self.destroy()

    def _apply_field_errors(self, message: str) -> None:
        field_by_keyword = {
            "full name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "password": self.password,
        }
        unmatched = []
        for sentence in message.split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue
            lowered = sentence.lower()
            field = next((f for keyword, f in field_by_keyword.items() if keyword in lowered), None)
            if field:
                field.set_error(sentence if sentence.endswith(".") else f"{sentence}.")
            else:
                unmatched.append(sentence)
        if unmatched:
            show_toast(self.master, " ".join(unmatched), variant="error")
