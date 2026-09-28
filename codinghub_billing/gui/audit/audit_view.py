"""Audit Log screen (Section 24): date range + search + action/entity
filters -> summary -> table -> export. Append-only history — no edit,
no delete, sirf dekhna aur export."""
from __future__ import annotations

from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from controllers import audit_controller
from gui.components.buttons import SecondaryButton
from gui.components.cards import Card
from gui.components.date_range import DateRangeFilter
from gui.components.dialogs import Modal
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme

FILTER_ALL = "All"

_ACTION_ICONS = {
    "create": "➕", "update": "✏️", "delete": "🗑️", "login": "🔑",
    "backup": "💾", "restore": "♻️",
}


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class AuditDetailModal(Modal):
    """Full event detail — table me lambi description kat jaati hai."""

    def __init__(self, master, row: dict):
        super().__init__(master, title="Activity Detail", width=520, height=380,
                         resizable=True, scrollable=True)
        from gui.components.buttons import SecondaryButton as CloseButton

        when = row.get("timestamp")
        when_text = when.strftime("%d-%m-%Y %H:%M") if when else "—"
        lines = [
            ("When", when_text),
            ("User", row.get("username", "—")),
            ("Action", row.get("action", "—")),
            ("Entity", f"{row.get('entity_type', '—')}  {row.get('entity_id', '')}".strip()),
        ]
        for label, value in lines:
            ctk.CTkLabel(
                self.scroll_body, text=f"{label}:  {value}",
                font=theme.fonts.body, text_color=theme.colors.text, anchor="w",
                justify="left", wraplength=440,
            ).pack(fill="x", pady=(0, theme.spacing.xs))
        ctk.CTkLabel(
            self.scroll_body, text="Description:", font=theme.fonts.body_bold,
            text_color=theme.colors.text, anchor="w",
        ).pack(fill="x", pady=(theme.spacing.sm, theme.spacing.xs))
        ctk.CTkLabel(
            self.scroll_body, text=row.get("description") or "—",
            font=theme.fonts.body, text_color=theme.colors.text_secondary,
            anchor="w", justify="left", wraplength=440,
        ).pack(fill="x")
        CloseButton(self.actions, text="Close", command=self.destroy).pack(side="right")


class AuditView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._action = FILTER_ALL
        self._entity_type = FILTER_ALL
        self._date_from: date | None = None
        self._date_to: date | None = None
        self._rows: list[dict] = []

        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="📜  Audit Log", font=theme.fonts.page_heading,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        ctk.CTkLabel(
            self, text="Kaun-kya-kab — har change ka hisaab. Double-click pe full detail.",
            font=theme.fonts.body, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=theme.spacing.lg, pady=(2, 0))

        self._build_summary()

        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.grid(row=3, column=0, sticky="ew",
                        padx=theme.spacing.lg, pady=(theme.spacing.sm, 0))
        filter_bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(
            filter_bar, placeholder="Search user, action, description...",
            on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        options = audit_controller.filter_options()
        self.action_menu = self._dropdown(
            filter_bar, [FILTER_ALL] + options["actions"], self._on_action, row=0, col=1)
        self.entity_menu = self._dropdown(
            filter_bar, [FILTER_ALL] + options["entity_types"], self._on_entity, row=0, col=2)

        btn_row = ctk.CTkFrame(filter_bar, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=3, sticky="w", pady=(theme.spacing.sm, 0))
        self.date_range = DateRangeFilter(btn_row, on_apply=self._on_dates)
        self.date_range.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(btn_row, text="Export", icon="📤", command=self._export).pack(side="left")

        self.table = DataTable(
            self,
            columns=[
                ("when_display", "When", 130, "w"),
                ("username", "User", 110, "w"),
                ("action_display", "Action", 100, "w"),
                ("entity_display", "Entity", 140, "w"),
                ("description", "Description", 320, "w"),
            ],
            on_row_double_click=self._open_detail,
            row_tag_fn=lambda r: str(r.get("action", "")).lower(),
            tag_colors={
                "create": theme.colors.success, "update": theme.colors.info,
                "delete": theme.colors.danger, "login": theme.colors.primary,
                "backup": theme.colors.warning, "restore": theme.colors.warning,
            },
            empty_message="No activity in this period",
        )
        self.table.grid(row=4, column=0, sticky="nsew",
                        padx=theme.spacing.lg, pady=(theme.spacing.md, theme.spacing.lg))

        self.date_range.trigger_initial_load()

    # ------------------------------------------------------------------ layout
    def _dropdown(self, master, values, command, row, col):
        menu = ctk.CTkOptionMenu(
            master, values=values or [FILTER_ALL], command=command, width=140,
            font=theme.fonts.body, fg_color=theme.colors.background,
            button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        menu.set(FILTER_ALL)
        menu.grid(row=row, column=col, padx=(0, theme.spacing.sm))
        return menu

    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=2, column=0, sticky="ew",
                   padx=theme.spacing.lg, pady=(theme.spacing.md, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="audit")

        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("📜", "TOTAL EVENTS", theme.colors.primary),
             ("👥", "ACTIVE USERS", theme.colors.info),
             ("⚡", "TOP ACTION", theme.colors.success)]
        ):
            card = Card(strip)
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0, theme.spacing.sm) if i < 2 else (theme.spacing.sm, 0))
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card, text=icon, font=("Segoe UI", 22), text_color=accent,
                fg_color=_soft(accent), corner_radius=10, width=46, height=46,
            ).grid(row=0, column=0, rowspan=2, padx=theme.spacing.sm, pady=theme.spacing.sm)
            ctk.CTkLabel(
                card, text=label, font=theme.fonts.kpi_label,
                text_color=theme.colors.text_secondary, anchor="w",
            ).grid(row=0, column=1, sticky="w",
                   padx=(0, theme.spacing.sm), pady=(theme.spacing.sm, 0))
            value_label = ctk.CTkLabel(
                card, text="—", font=("Segoe UI", 16, "bold"),
                text_color=theme.colors.text, anchor="w",
            )
            value_label.grid(row=1, column=1, sticky="w",
                             padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
            self._sum_values.append(value_label)

    def _refresh_summary(self) -> None:
        from collections import Counter

        total = len(self._rows)
        users = {r.get("username") for r in self._rows if r.get("username") not in (None, "", "—")}
        top = Counter(r.get("action", "") for r in self._rows).most_common(1)
        top_text = f"{_ACTION_ICONS.get(top[0][0], '•')} {top[0][0]} ({top[0][1]})" if top else "—"
        for label, text in zip(self._sum_values, [f"{total:,}", f"{len(users):,}", top_text]):
            try:
                label.configure(text=text)
            except Exception:
                pass

    # ------------------------------------------------------------------ data
    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_action(self, value: str) -> None:
        self._action = value
        self._load()

    def _on_entity(self, value: str) -> None:
        self._entity_type = value
        self._load()

    def _on_dates(self, date_from: date, date_to: date) -> None:
        self._date_from = date_from
        self._date_to = date_to
        self._load()

    def _load(self) -> None:
        rows = audit_controller.list_logs(
            query=self._query, action=self._action, entity_type=self._entity_type,
            date_from=self._date_from, date_to=self._date_to,
        )
        self._rows = rows
        display = [
            {
                **r,
                "when_display": r["timestamp"].strftime("%d-%m-%Y %H:%M") if r.get("timestamp") else "—",
                "action_display": f"{_ACTION_ICONS.get(str(r.get('action', '')), '•')} {r.get('action', '')}",
                "entity_display": f"{r.get('entity_type', '')} {r.get('entity_id', '')}".strip(),
            }
            for r in rows
        ]
        self.table.set_rows(display)
        self._refresh_summary()

    def _open_detail(self, row: dict) -> None:
        AuditDetailModal(self, row)

    def _export(self) -> None:
        if not self._rows:
            show_toast(self.winfo_toplevel(), "Export ke liye koi rows nahi hain.",
                       variant="error")
            return
        path = filedialog.asksaveasfilename(
            title="Export audit log", defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("CSV file", "*.csv")],
        )
        if not path:
            return
        fmt = "csv" if path.lower().endswith(".csv") else "excel"
        success, message = audit_controller.export_logs_to_file(path, fmt, self._rows)
        if success:
            show_toast(self.winfo_toplevel(), "Audit log exported.", variant="success")
        else:
            show_toast(self.winfo_toplevel(), message, variant="error")
