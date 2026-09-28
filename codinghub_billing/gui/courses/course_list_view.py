"""Course / Product list screen (Section 12)."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import course_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import ConfirmDialog
from gui.components.inputs import SearchBox
from gui.components.table import DataTable
from gui.components.toast import show_toast
from gui.courses.course_form_modal import CourseFormModal
from gui.theme import theme
from utils.formatters import format_currency

STATUS_FILTERS = ["All", "Active", "Inactive"]


class CourseListView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._query = ""
        self._status_filter = "All"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()

        self.table = DataTable(
            self,
            columns=[
                ("name", "Name", 220, "w"),
                ("category", "Category", 130, "w"),
                ("price_display", "Price", 100, "e"),
                ("gst_display", "GST", 70, "e"),
                ("duration", "Duration", 110, "w"),
                ("status", "Status", 90, "w"),
            ],
            on_row_double_click=self._open_edit_form,
            on_row_context_menu=self._row_menu,
            row_tag_fn=lambda r: r["status"].lower(),
            tag_colors={"active": theme.colors.success, "inactive": theme.colors.text_secondary},
            empty_message="No courses found",
            empty_action_label="Add Course",
            on_empty_action=self._open_add_form,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self._load()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=theme.spacing.lg, pady=theme.spacing.lg)
        bar.grid_columnconfigure(0, weight=1)

        self.search_box = SearchBox(bar, placeholder="Search by name or category...", on_change=self._on_search)
        self.search_box.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm))

        self.status_menu = ctk.CTkOptionMenu(
            bar,
            values=STATUS_FILTERS,
            command=self._on_status_change,
            width=130,
            font=theme.fonts.body,
            fg_color=theme.colors.background,
            button_color=theme.colors.primary,
            button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        self.status_menu.set("All")
        self.status_menu.grid(row=0, column=1, padx=(0, theme.spacing.sm))

        SecondaryButton(bar, text="Export", icon="\U0001F4E4", command=self._export).grid(
            row=0, column=2, padx=(0, theme.spacing.sm)
        )
        PrimaryButton(bar, text="New Course", icon="+", command=self._open_add_form).grid(row=0, column=3)

    def _on_search(self, value: str) -> None:
        self._query = value
        self._load()

    def _on_status_change(self, value: str) -> None:
        self._status_filter = value
        self._load()

    def _load(self) -> None:
        rows = course_controller.list_courses(query=self._query, status=self._status_filter)
        display_rows = [
            {
                **row,
                "price_display": format_currency(row["price"]),
                "gst_display": f"{row['gst_percentage']}%",
            }
            for row in rows
        ]
        self.table.set_rows(display_rows)

    def _open_add_form(self) -> None:
        CourseFormModal(self, on_saved=lambda _c: self._load())

    def _open_edit_form(self, row: dict) -> None:
        CourseFormModal(self, course_id=row["id"], on_saved=lambda _c: self._load())

    def _row_menu(self, row: dict) -> list[tuple[str, object]]:
        toggle_label = "Deactivate" if row["status"] == "Active" else "Activate"
        return [
            ("Edit", lambda: self._open_edit_form(row)),
            (toggle_label, lambda: self._toggle_status(row)),
            ("Delete", lambda: self._confirm_delete(row)),
        ]

    def _toggle_status(self, row: dict) -> None:
        new_status = "Inactive" if row["status"] == "Active" else "Active"
        success, message = course_controller.set_course_status(row["id"], new_status)
        root = self.winfo_toplevel()
        if success:
            show_toast(root, f"{row['name']} marked as {new_status}.", variant="success")
            self._load()
        else:
            show_toast(root, message, variant="error")

    def _confirm_delete(self, row: dict) -> None:
        def do_delete():
            success, message = course_controller.delete_course(row["id"])
            root = self.winfo_toplevel()
            if success:
                show_toast(root, f"Course {row['name']} deleted.", variant="success")
                self._load()
            else:
                show_toast(root, message, variant="error")

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Course",
            message=f"Are you sure you want to delete {row['name']}? This cannot be undone.",
            on_confirm=do_delete,
        )

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export courses", defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not path:
            return
        success, message = course_controller.export_courses_to_excel(path, query=self._query, status=self._status_filter)
        root = self.winfo_toplevel()
        if success:
            show_toast(root, "Courses exported successfully.", variant="success")
        else:
            show_toast(root, message, variant="error")
