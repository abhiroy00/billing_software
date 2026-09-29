"""Main application shell: sidebar + topbar + routed content area
(Section 7). Modules not yet built in this phase route to an honest
"coming in a later phase" empty state rather than a broken/fake screen."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import auth_controller
from gui.backup.backup_view import BackupView
from gui.billing.billing_view import BillingView
from gui.components.empty_state import EmptyState
from gui.courses.course_list_view import CourseListView
from gui.customers.customer_list_view import CustomerListView
from gui.dashboard.dashboard_view import DashboardView
from gui.expenses.expense_list_view import ExpenseListView
from gui.payments.payments_list_view import PaymentsListView
from gui.reports.reports_view import ReportsView
from gui.settings.settings_view import SettingsView
from gui.theme import theme
from gui.users.user_list_view import UserListView
from services import auth_service

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "\U0001F3E0"),
    ("customers", "Customers", "\U0001F465"),
    ("courses", "Courses", "\U0001F4DA"),
    ("billing", "Billing", "\U0001F9FE"),
    ("payments", "Payments", "\U0001F4B3"),
    ("expenses", "Expenses", "\U0001F4B8"),
    ("reports", "Reports", "\U0001F4CA"),
    ("users", "Users", "\U0001F464"),
    ("settings", "Settings", "⚙"),
    ("backup", "Backup", "\U0001F5C4"),
]

# Section 23 RBAC: nav items map to the permission code required to see them.
# Items absent from this mapping are visible to any authenticated user.
NAV_PERMISSIONS: dict[str, str] = {
    "reports": "reports",
    "users": "users",
    "settings": "settings",
    "backup": "backup",
}

_STUB_MESSAGES: dict[str, str] = {}


class MainShell(ctk.CTkFrame):
    def __init__(self, master, on_logout: Callable[[], None]):
        super().__init__(master, fg_color=theme.colors.background)
        self._on_logout = on_logout
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._active_key = "dashboard"

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_area()

        self._dashboard_shortcut_id = self.master.bind("<Control-d>", lambda _e: self._navigate("dashboard"))
        self._new_invoice_shortcut_id = self.master.bind("<Control-n>", lambda _e: self._navigate("billing", new_invoice=True))
        self.bind("<Destroy>", self._unbind_shortcuts)
        self._navigate("dashboard")

    def _unbind_shortcuts(self, _event=None) -> None:
        try:
            self.master.unbind("<Control-d>", self._dashboard_shortcut_id)
            self.master.unbind("<Control-n>", self._new_invoice_shortcut_id)
        except Exception:
            pass

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self, fg_color=theme.colors.secondary, width=theme.spacing.sidebar_width, corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=theme.spacing.md, pady=(theme.spacing.lg, theme.spacing.md))
        brand.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            brand, text="CH", font=("Segoe UI", 18, "bold"),
            text_color=theme.colors.white, fg_color=theme.colors.primary,
            corner_radius=12, width=44, height=44,
        ).grid(row=0, column=0, rowspan=2, padx=(0, theme.spacing.sm))
        ctk.CTkLabel(
            brand, text="CodingHub", font=theme.fonts.logo, text_color=theme.colors.white, anchor="w"
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            brand, text="✨ Billing Suite  •  v1.0", font=theme.fonts.small, text_color="#94A3B8", anchor="w"
        ).grid(row=1, column=1, sticky="w")

        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="new", padx=theme.spacing.sm)

        menu_label = ctk.CTkLabel(
            nav_frame, text="MENU", font=("Segoe UI", 10, "bold"), text_color="#64748B", anchor="w"
        )
        menu_label.pack(fill="x", padx=theme.spacing.sm, pady=(0, 4))

        for key, label, icon in NAV_ITEMS:
            required_permission = NAV_PERMISSIONS.get(key)
            if required_permission and not auth_service.current_session.has_permission(required_permission):
                continue
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}   {label}",
                anchor="w",
                font=theme.fonts.body,
                fg_color="transparent",
                hover_color=theme.colors.sidebar_hover,
                text_color="#CBD5E1",
                corner_radius=theme.spacing.radius,
                height=42,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[key] = btn

        logout_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logout_frame.grid(row=2, column=0, sticky="sew", padx=theme.spacing.sm, pady=theme.spacing.lg)
        ctk.CTkLabel(
            logout_frame, text="Made for CodingHub 🚀", font=theme.fonts.small, text_color="#64748B"
        ).pack(pady=(0, theme.spacing.xs))
        ctk.CTkButton(
            logout_frame,
            text="⏻   Logout",
            anchor="w",
            font=theme.fonts.body,
            fg_color="transparent",
            hover_color=theme.colors.sidebar_hover,
            text_color="#CBD5E1",
            corner_radius=theme.spacing.radius,
            height=42,
            command=self._handle_logout,
        ).pack(fill="x")

    # ---------------------------------------------------------------- main area
    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(main, fg_color=theme.colors.card, height=76, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        self.page_title_label = ctk.CTkLabel(
            topbar, text="Dashboard", font=theme.fonts.section_heading, text_color=theme.colors.text
        )
        self.page_title_label.grid(row=0, column=0, sticky="w", padx=theme.spacing.lg)

        from datetime import datetime

        self.date_label = ctk.CTkLabel(
            topbar, text=datetime.now().strftime("%A, %d %b %Y"),
            font=theme.fonts.small, text_color=theme.colors.text_secondary,
        )
        self.date_label.grid(row=1, column=0, sticky="w", padx=theme.spacing.lg)

        user_box = ctk.CTkFrame(topbar, fg_color="transparent")
        user_box.grid(row=0, column=1, rowspan=2, sticky="e", padx=theme.spacing.lg)
        full_name = auth_service.current_session.full_name or ""
        role_name = auth_service.current_session.role_name or ""
        initials = "".join(part[:1] for part in full_name.split()[:2]).upper() or "U"
        ctk.CTkLabel(
            user_box, text=initials, font=theme.fonts.body_bold,
            text_color=theme.colors.white, fg_color=theme.colors.primary,
            corner_radius=18, width=36, height=36,
        ).pack(side="left", padx=(0, theme.spacing.sm))
        name_col = ctk.CTkFrame(user_box, fg_color="transparent")
        name_col.pack(side="left")
        ctk.CTkLabel(
            name_col, text=f"👋 {full_name}", font=theme.fonts.body_bold, text_color=theme.colors.text, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            name_col, text=f"● {role_name}", font=theme.fonts.small,
            text_color=theme.colors.primary, anchor="w",
        ).pack(anchor="w")

        self.content = ctk.CTkFrame(main, fg_color=theme.colors.background)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    # -------------------------------------------------------------------- nav
    def _navigate(self, key: str, new_invoice: bool = False) -> None:
        self._active_key = key
        for nav_key, btn in self._nav_buttons.items():
            is_active = nav_key == key
            btn.configure(
                fg_color=theme.colors.sidebar_active if is_active else "transparent",
                hover_color=theme.colors.primary_hover if is_active else theme.colors.sidebar_hover,
                text_color=theme.colors.white if is_active else "#CBD5E1",
                font=theme.fonts.body_bold if is_active else theme.fonts.body,
            )

        label = next(label for k, label, _icon in NAV_ITEMS if k == key)
        self.page_title_label.configure(text=label)

        for child in self.content.winfo_children():
            child.destroy()

        if key == "dashboard":
            page = DashboardView(
                self.content,
                on_new_invoice=lambda: self._navigate("billing", new_invoice=True),
                on_add_customer=lambda: self._navigate("customers"),
                on_view_reports=lambda: self._navigate("reports"),
            )
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "customers":
            page = CustomerListView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "courses":
            page = CourseListView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "billing":
            page = BillingView(self.content, start_with_new_invoice=new_invoice)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "payments":
            page = PaymentsListView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "expenses":
            page = ExpenseListView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "reports":
            page = ReportsView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "settings":
            page = SettingsView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "backup":
            page = BackupView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        elif key == "users":
            page = UserListView(self.content)
            page.grid(row=0, column=0, sticky="nsew")
        else:
            page = EmptyState(
                self.content, message=_STUB_MESSAGES.get(key, "This module is coming soon."), icon="\U0001F6E0"
            )
            page.place(relx=0.5, rely=0.42, anchor="center")

    def _handle_logout(self) -> None:
        auth_controller.logout()
        self._on_logout()
