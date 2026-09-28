"""Backup & Restore screen (Section 27): manual backup, backup list,
restore with safety copy, delete, and folder shortcut."""
from __future__ import annotations

import customtkinter as ctk

from controllers import backup_controller, settings_controller
from gui.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.theme import theme


def _soft(color: str) -> str:
    return {
        theme.colors.success: theme.colors.success_soft,
        theme.colors.danger: theme.colors.danger_soft,
        theme.colors.primary: theme.colors.primary_soft,
        theme.colors.info: theme.colors.info_soft,
        theme.colors.warning: theme.colors.warning_soft,
    }.get(color, theme.colors.primary_soft)


class BackupView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="🗄️  Backup & Restore", font=theme.fonts.page_heading,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, 0))
        ctk.CTkLabel(
            self, text="Regular backup lo — restore se pehle safety copy auto-banegi.",
            font=theme.fonts.body, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=theme.spacing.lg, pady=(2, 0))

        folder_row = ctk.CTkFrame(self, fg_color="transparent")
        folder_row.grid(row=2, column=0, sticky="ew",
                        padx=theme.spacing.lg, pady=(theme.spacing.sm, 0))
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_label = ctk.CTkLabel(
            folder_row, text="", font=theme.fonts.small, text_color=theme.colors.text_secondary,
            anchor="w",
        )
        self.folder_label.grid(row=0, column=0, sticky="w")
        SecondaryButton(folder_row, text="Open Folder", icon="📁",
                        command=self._open_folder).grid(row=0, column=1)

        self._build_summary()
        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("name", "Backup File", 260, "w"),
                ("modified_display", "Taken On", 150, "w"),
                ("size_display", "Size", 90, "e"),
            ],
            on_row_double_click=self._confirm_restore,
            on_row_context_menu=self._row_menu,
            empty_message="No backups yet — pehla backup abhi lo",
            empty_action_label="Backup Now",
            on_empty_action=self._take_backup,
        )
        self.table.grid(row=5, column=0, sticky="nsew",
                        padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    # ------------------------------------------------------------------ layout
    def _build_summary(self) -> None:
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=3, column=0, sticky="ew",
                   padx=theme.spacing.lg, pady=(theme.spacing.md, 0))
        strip.grid_columnconfigure((0, 1, 2), weight=1, uniform="backup")

        self._sum_values: list = []
        for i, (icon, label, accent) in enumerate(
            [("🗄️", "TOTAL BACKUPS", theme.colors.primary),
             ("💾", "TOTAL SIZE", theme.colors.info),
             ("🕒", "LATEST BACKUP", theme.colors.success)]
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

    def _refresh_summary(self, rows: list[dict]) -> None:
        from services.backup_service import format_file_size

        total = len(rows)
        total_size = sum(r.get("size_bytes", 0) for r in rows)
        latest = rows[0]["modified_display"] if rows else "—"
        for label, text in zip(
            self._sum_values, [f"{total:,}", format_file_size(total_size), latest]
        ):
            try:
                label.configure(text=text)
            except Exception:
                pass

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=4, column=0, sticky="ew",
                 padx=theme.spacing.lg, pady=theme.spacing.md)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search backups...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        SecondaryButton(bar, text="Refresh", icon="🔄", command=self._load).grid(
            row=0, column=1, padx=(0, theme.spacing.sm))
        DangerButton(bar, text="Delete", icon="🗑", command=self._delete_selected).grid(
            row=0, column=2, padx=(0, theme.spacing.sm))
        SecondaryButton(bar, text="Restore", icon="♻", command=self._restore_selected).grid(
            row=0, column=3, padx=(0, theme.spacing.sm))
        PrimaryButton(bar, text="Backup Now", icon="💾", command=self._take_backup).grid(
            row=0, column=4)

    # ------------------------------------------------------------------ actions
    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _load(self) -> None:
        try:
            self.folder_label.configure(
                text=f"📁  Backup folder: {backup_controller.get_backup_dir()}")
        except Exception:
            pass
        rows = backup_controller.list_backups()
        if self._query.strip():
            q = self._query.strip().lower()
            rows = [r for r in rows if q in r["name"].lower()]
        self.table.set_rows(rows)
        self._refresh_summary(backup_controller.list_backups())

    def _take_backup(self) -> None:
        success, message, _info = backup_controller.create_backup()
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Backup le liya gaya.", variant="success")
            self._load()
        else:
            show_toast(root, message, variant="error")

    def _selected_or_warn(self) -> dict | None:
        row = self.table.get_selected()
        if row is None:
            show_toast(self.winfo_toplevel(), "Pehle list me se ek backup select karo.",
                       variant="error")
        return row

    def _restore_selected(self) -> None:
        row = self._selected_or_warn()
        if row is not None:
            self._confirm_restore(row)

    def _delete_selected(self) -> None:
        row = self._selected_or_warn()
        if row is not None:
            self._confirm_delete(row)

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        return [
            ("Restore", lambda: self._confirm_restore(row)),
            ("Delete", lambda: self._confirm_delete(row)),
        ]

    def _confirm_restore(self, row: dict) -> None:
        def do_restore():
            success, message = backup_controller.restore_backup(row["path"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, message, variant="success", duration_ms=6000)
                self._load()
            else:
                show_toast(root, message, variant="error", duration_ms=6000)

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Restore Database?",
            message=(
                f"{row['name']} se pura data replace ho jayega.\n"
                f"Current data ki safety copy auto-banegi.\n"
                f"Restore ke baad APP RESTART karna zaroori hai.\n\n"
                f"Pakka restore karna hai?"
            ),
            on_confirm=do_restore,
            confirm_label="Restore",
        )

    def _confirm_delete(self, row: dict) -> None:
        def do_delete():
            success, message = backup_controller.delete_backup(row["path"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, f"Backup {row['name']} deleted.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Backup",
            message=f"Kya {row['name']} hamesha ke liye delete karna hai?",
            on_confirm=do_delete,
        )

    def _open_folder(self) -> None:
        success, message = settings_controller.open_backup_folder()
        if not success:
            show_toast(self.winfo_toplevel(), message, variant="error")
