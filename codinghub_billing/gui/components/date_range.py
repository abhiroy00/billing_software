"""Free-form date-range filter (Section 50): From/To fields + Apply,
defaulting to the current month. Reused across all Report panels."""
from __future__ import annotations

from datetime import date
from typing import Callable

import customtkinter as ctk

from gui.components.buttons import PrimaryButton
from gui.components.inputs import FormField
from gui.theme import theme
from utils import validators
from utils.formatters import format_date, parse_date


class DateRangeFilter(ctk.CTkFrame):
    def __init__(self, master, on_apply: Callable[[date, date], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_apply = on_apply

        today = date.today()
        month_start = today.replace(day=1)

        self.date_from = FormField(self, "From (DD-MM-YYYY)")
        self.date_from.set(format_date(month_start))
        self.date_from.pack(side="left", padx=(0, theme.spacing.sm))

        self.date_to = FormField(self, "To (DD-MM-YYYY)")
        self.date_to.set(format_date(today))
        self.date_to.pack(side="left", padx=(0, theme.spacing.sm))

        apply_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        apply_wrapper.pack(side="left", padx=(0, theme.spacing.sm))
        ctk.CTkLabel(apply_wrapper, text="", height=18).pack()
        PrimaryButton(apply_wrapper, text="Apply", command=self._apply).pack()

    def _apply(self) -> None:
        from_error = validators.valid_date(self.date_from.get(), field_label="From date")
        to_error = validators.valid_date(self.date_to.get(), field_label="To date")
        self.date_from.set_error(from_error)
        self.date_to.set_error(to_error)
        if from_error or to_error:
            return
        self._on_apply(parse_date(self.date_from.get()), parse_date(self.date_to.get()))

    def get_range(self) -> tuple[date, date]:
        return parse_date(self.date_from.get()), parse_date(self.date_to.get())

    def trigger_initial_load(self) -> None:
        self._apply()
