"""Professional data table (Section 20/44): ttk.Treeview wrapper with
sortable columns, row double-click, a right-click context menu, and a
built-in empty state."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Sequence

import customtkinter as ctk

from gui.components.empty_state import EmptyState
from gui.theme import theme

_STYLE_CONFIGURED = False


def _configure_treeview_style() -> str:
    global _STYLE_CONFIGURED
    style_name = "CodingHub.Treeview"
    if _STYLE_CONFIGURED:
        return style_name

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        style_name,
        background=theme.colors.card,
        fieldbackground=theme.colors.card,
        foreground=theme.colors.text,
        rowheight=34,
        borderwidth=0,
        font=theme.fonts.table,
    )
    style.map(style_name, background=[("selected", theme.colors.primary)], foreground=[("selected", theme.colors.white)])

    style.configure(
        f"{style_name}.Heading",
        background=theme.colors.background,
        foreground=theme.colors.text_secondary,
        font=theme.fonts.small_bold,
        borderwidth=0,
        relief="flat",
    )
    style.map(f"{style_name}.Heading", background=[("active", theme.colors.background)])
    style.layout(style_name, [("Treeview.treearea", {"sticky": "nswe"})])

    _STYLE_CONFIGURED = True
    return style_name


class DataTable(ctk.CTkFrame):
    """columns: sequence of (key, heading, width, anchor)."""

    def __init__(
        self,
        master,
        columns: Sequence[tuple[str, str, int, str]],
        on_row_double_click: Callable[[dict], None] | None = None,
        on_row_context_menu: Callable[[dict], list[tuple[str, Callable[[], None]]]] | None = None,
        row_tag_fn: Callable[[dict], str] | None = None,
        tag_colors: dict[str, str] | None = None,
        empty_message: str = "No records found",
        empty_action_label: str | None = None,
        on_empty_action: Callable[[], None] | None = None,
        **kwargs,
    ):
        defaults = dict(fg_color=theme.colors.card, corner_radius=theme.spacing.radius, border_width=1, border_color=theme.colors.border)
        defaults.update(kwargs)
        super().__init__(master, **defaults)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._columns = columns
        self._on_row_double_click = on_row_double_click
        self._on_row_context_menu = on_row_context_menu
        self._row_tag_fn = row_tag_fn
        self._rows: list[dict[str, Any]] = []
        self._iid_to_row: dict[str, dict[str, Any]] = {}
        self._sort_key: str | None = None
        self._sort_reverse = False

        style_name = _configure_treeview_style()
        keys = [c[0] for c in columns]

        self.tree = ttk.Treeview(self, columns=keys, show="headings", style=style_name, selectmode="browse")
        for key, heading, width, anchor in columns:
            self.tree.heading(key, text=heading, command=lambda k=key: self._sort_by(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=True)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        vsb.grid(row=0, column=1, sticky="ns", pady=1)

        if tag_colors:
            for tag, color in tag_colors.items():
                self.tree.tag_configure(tag, foreground=color)

        if on_row_double_click:
            self.tree.bind("<Double-1>", self._handle_double_click)
        if on_row_context_menu:
            self.tree.bind("<Button-3>", self._handle_right_click)

        self._empty_state = EmptyState(
            self, message=empty_message, action_label=empty_action_label, on_action=on_empty_action
        )

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._render()

    def get_selected(self) -> dict[str, Any] | None:
        """Currently highlighted row (for toolbar Edit/Delete buttons)."""
        try:
            selection = self.tree.selection()
        except Exception:
            return None
        if not selection:
            return None
        return self._iid_to_row.get(selection[0])

    def _render(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self._rows
        if self._sort_key:
            rows = sorted(
                rows, key=lambda r: (r.get(self._sort_key) is None, r.get(self._sort_key)), reverse=self._sort_reverse
            )

        if not rows:
            self._iid_to_row = {}
            self.tree.grid_remove()
            self._empty_state.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._empty_state.place_forget()
            self.tree.grid()
            self._iid_to_row = {}
            for idx, row in enumerate(rows):
                values = [row.get(key, "") for key, *_ in self._columns]
                tags = (self._row_tag_fn(row),) if self._row_tag_fn else ()
                row_id = row.get("id")
                iid = str(row_id) if row_id is not None else f"row-{idx}"
                self._iid_to_row[iid] = row
                self.tree.insert(
                    "", "end", iid=iid, values=values, tags=tags
                )

    def _sort_by(self, key: str) -> None:
        if self._sort_key == key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = False
        self._render()

    def _handle_double_click(self, _event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        row = self._iid_to_row.get(selection[0])
        if row and self._on_row_double_click:
            self._on_row_double_click(row)

    def _handle_right_click(self, event) -> None:
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        row = self._iid_to_row.get(iid)
        if not row or not self._on_row_context_menu:
            return
        items = self._on_row_context_menu(row)
        if not items:
            return
        menu = tk.Menu(self, tearoff=0)
        for label, callback in items:
            menu.add_command(label=label, command=callback)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
