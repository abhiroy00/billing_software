"""User list screen (Section 23): search, filter by role, activate/
deactivate — no export (never export credentials, per Section 55)."""
from __future__ import annotations

import customtkinter as ctk

from controllers import user_controller
from gui.components.buttons import PrimaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme
from gui.users.user_form_modal import UserFormModal
from services import auth_service
from utils.formatters import format_date

ROLE_FILTER_ALL = "All Roles"

_ROLE_ICONS = {"Admin": "👑", "Manager": "💼", "Accountant": "🧾", "Operator": "🖥️"}


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class UserListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._role_id: int | None = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._roles = user_controller.list_roles()
        self._role_id_by_name = {r["name"]: r["id"] for r in self._roles}

        self._build_summary()
        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("username", "Username", 120, "w"),
                ("full_name", "Full Name", 160, "w"),
                ("email", "Email", 180, "w"),
                ("role_name", "Role", 110, "w"),
                ("status_display", "Status", 90, "w"),
                ("last_login_display", "Last Login", 140, "w"),
            ],
            on_row_double_click=self._open_edit_form,
            on_row_context_menu=self._row_menu,
            row_tag_fn=lambda r: "active" if r["is_active"] else "inactive",
            tag_colors={"active": theme.colors.success, "inactive": theme.colors.text_secondary},
            empty_message="No users found",
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="users")

        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("👥", "TOTAL USERS", theme.colors.primary),
             ("✅", "ACTIVE", theme.colors.success),
             ("👑", "ADMINS", theme.colors.warning)]
        ):
            card = Card(strip)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, theme.spacing.sm) if i < 2 else (theme.spacing.sm, 0))
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card, text=icon, font=("Segoe UI", 22), text_color=accent,
                fg_color=_soft(accent), corner_radius=10, width=46, height=46,
            ).grid(row=0, column=0, rowspan=2, padx=theme.spacing.sm, pady=theme.spacing.sm)
            ctk.CTkLabel(
                card, text=label, font=theme.fonts.kpi_label, text_color=theme.colors.text_secondary, anchor="w"
            ).grid(row=0, column=1, sticky="w", padx=(0, theme.spacing.sm), pady=(theme.spacing.sm, 0))
            value_label = ctk.CTkLabel(
                card, text="—", font=("Segoe UI", 20, "bold"), text_color=theme.colors.text, anchor="w"
            )
            value_label.grid(row=1, column=1, sticky="w", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
            self._sum_values.append(value_label)

    def _refresh_summary(self, rows: list[dict]) -> None:
        total = len(rows)
        active = sum(1 for r in rows if r.get("is_active"))
        admins = sum(1 for r in rows if str(r.get("role_name", "")).lower() == "admin")
        texts = [f"{total:,}", f"{active:,}", f"{admins:,}"]
        try:
            from gui.components.animations import count_up

            for label, text in zip(self._sum_values, texts):
                count_up(label, text, duration_ms=500)
        except Exception:
            for label, text in zip(self._sum_values, texts):
                try:
                    label.configure(text=text)
                except Exception:
                    pass

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.md)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search by name, username, email...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        role_values = [ROLE_FILTER_ALL] + [r["name"] for r in self._roles]
        self.role_menu = ctk.CTkOptionMenu(
            bar, values=role_values, command=self._on_role_change, width=150,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.role_menu.set(ROLE_FILTER_ALL)
        self.role_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        PrimaryButton(bar, text="New User", icon="+", command=self._open_add_form).grid(row=0, column=2)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_role_change(self, value: str) -> None:
        self._role_id = None if value == ROLE_FILTER_ALL else self._role_id_by_name.get(value)
        self._load()

    def _load(self) -> None:
        rows = user_controller.list_users(query=self._query, role_id=self._role_id)
        display_rows = [
            {
                **row,
                "role_name": f"{_ROLE_ICONS.get(row['role_name'], '👤')} {row['role_name']}",
                "status_display": "Active" if row["is_active"] else "Inactive",
                "last_login_display": format_date(row["last_login_at"]) if row["last_login_at"] else "Never",
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)
        self._refresh_summary(rows)

    def _open_add_form(self) -> None:
        UserFormModal(self, on_saved=lambda _u: self._load())

    def _open_edit_form(self, row: dict) -> None:
        UserFormModal(self, user_id=row["id"], on_saved=lambda _u: self._load())

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        is_self = row["id"] == auth_service.current_session.user_id
        items = [("Edit", lambda: self._open_edit_form(row))]
        if not is_self:
            toggle_label = "Deactivate" if row["is_active"] else "Activate"
            items.append((toggle_label, lambda: self._confirm_toggle(row)))
        return items

    def _confirm_toggle(self, row: dict) -> None:
        new_active = not row["is_active"]
        action_label = "Activate" if new_active else "Deactivate"

        def do_toggle():
            success, message = user_controller.set_user_active(row["id"], new_active)
            root = self.winfo_toplevel()
            if success:
                show_toast(root, f"User {row['username']} {'activated' if new_active else 'deactivated'}.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title=f"{action_label} User",
            message=f"Are you sure you want to {action_label.lower()} {row['full_name']} ({row['username']})?",
            on_confirm=do_toggle,
            confirm_label=action_label,
            danger=not new_active,
        )
