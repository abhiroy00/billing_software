"""Form input components with inline validation errors (Section 22/44)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from gui.theme import theme


class FormField(ctk.CTkFrame):
    """Label + entry (or custom widget) + inline error message."""

    def __init__(
        self,
        master,
        label: str,
        required: bool = False,
        show: str | None = None,
        placeholder: str = "",
        widget_factory: Callable[[ctk.CTkFrame], ctk.CTkBaseClass] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        label_text = f"{label} *" if required else label
        self.label_widget = ctk.CTkLabel(
            self, text=label_text, font=theme.fonts.small_bold, text_color=theme.colors.text, anchor="w"
        )
        self.label_widget.grid(row=0, column=0, sticky="w", pady=(0, 4))

        if widget_factory is not None:
            self.input = widget_factory(self)
        else:
            self.input = ctk.CTkEntry(
                self,
                placeholder_text=placeholder,
                show=show,
                font=theme.fonts.body,
                height=36,
                corner_radius=theme.spacing.radius // 2,
                border_color=theme.colors.border,
            )
        self.input.grid(row=1, column=0, sticky="ew")

        self.error_label = ctk.CTkLabel(
            self, text="", font=theme.fonts.small, text_color=theme.colors.danger, anchor="w"
        )
        self.error_label.grid(row=2, column=0, sticky="w", pady=(2, 0))

    def get(self) -> str:
        """Supports Entry, CTkTextbox, CTkOptionMenu and CTkComboBox."""
        widget = self.input
        if isinstance(widget, ctk.CTkTextbox):
            try:
                return widget.get("1.0", "end-1c")
            except Exception:
                return ""
        try:
            return widget.get()
        except TypeError:
            # CTkTextbox.get requires a start index (older fallback path).
            try:
                return widget.get("1.0", "end").rstrip("\n")
            except Exception:
                return ""
        except AttributeError:
            return ""

    def set(self, value: str) -> None:
        """Entry/Textbox/OptionMenu/ComboBox aware setter.

        Pehle widget type check hota hai — purana try/except sirf
        TypeError pakadta tha, jabki tkinter Text.delete(0, 'end')
        TclError deta hai. Isi wajah se Edit modal (Notes/Description
        wala) load hote hi crash ho jata tha aur Save button banta
        hi nahi tha — edit execute ho hi nahi pata tha.
        """
        widget = self.input
        value = "" if value is None else str(value)
        if isinstance(widget, ctk.CTkTextbox):
            try:
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
            except Exception:
                pass
            return
        if isinstance(widget, (ctk.CTkOptionMenu, ctk.CTkComboBox)):
            try:
                widget.set(value)
            except Exception:
                pass
            return
        try:
            widget.delete(0, "end")
            widget.insert(0, value)
        except AttributeError:
            try:
                widget.set(value)
            except Exception:
                pass
        except Exception:
            # Last-resort fallback for custom widgets.
            try:
                widget.set(value)
            except Exception:
                pass

    def set_error(self, message: str | None) -> None:
        self.error_label.configure(text=message or "")
        border_color = theme.colors.danger if message else theme.colors.border
        try:
            self.input.configure(border_color=border_color)
        except Exception:
            pass

    def clear_error(self) -> None:
        self.set_error(None)


def dropdown_factory(values: list[str]) -> Callable[[ctk.CTkFrame], ctk.CTkOptionMenu]:
    """Convenience widget_factory for FormField: a themed CTkOptionMenu."""

    def factory(master: ctk.CTkFrame) -> ctk.CTkOptionMenu:
        menu = ctk.CTkOptionMenu(
            master,
            values=values,
            font=theme.fonts.body,
            dropdown_font=theme.fonts.body,
            height=36,
            corner_radius=theme.spacing.radius // 2,
            fg_color=theme.colors.background,
            button_color=theme.colors.primary,
            button_hover_color=theme.colors.primary_hover,
            text_color=theme.colors.text,
        )
        if values:
            menu.set(values[0])
        return menu

    return factory


class SearchBox(ctk.CTkFrame):
    """Search input with a magnifier glyph and on-change callback."""

    def __init__(self, master, placeholder: str = "Search...", on_change: Callable[[str], None] | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._on_change = on_change
        self._var = ctk.StringVar()
        if on_change is not None:
            self._var.trace_add("write", self._handle_change)

        self.entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text=f"\U0001F50D  {placeholder}",
            font=theme.fonts.body,
            height=36,
            corner_radius=theme.spacing.radius,
            border_color=theme.colors.border,
        )
        self.entry.grid(row=0, column=0, sticky="ew")

    def _handle_change(self, *_args) -> None:
        if self._on_change:
            self._on_change(self._var.get())

    def get(self) -> str:
        return self._var.get()

    def clear(self) -> None:
        self._var.set("")
