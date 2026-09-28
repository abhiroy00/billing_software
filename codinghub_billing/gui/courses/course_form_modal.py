"""Add/Edit Course modal (Section 12)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from config import config
from controllers import course_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme

STATUS_OPTIONS = ["Active", "Inactive"]


class CourseFormModal(Modal):
    def __init__(self, master, course_id: int | None = None, on_saved: Callable[[dict], None] | None = None):
        title = "Edit Course" if course_id else "New Course"
        super().__init__(master, title=title, width=560, height=560, resizable=True, scrollable=True)
        self._course_id = course_id
        self._on_saved = on_saved

        self.scroll_body.grid_columnconfigure(0, weight=1)
        self.scroll_body.grid_columnconfigure(1, weight=1)

        self.name = self._field("Course / Product Name", 0, 0, colspan=2, required=True)
        self.category = self._field("Category", 1, 0)
        self.duration = self._field("Duration (e.g. 3 months)", 1, 1)
        self.price = self._field("Price (₹)", 2, 0, required=True)
        self.gst_percentage = self._field(
            "GST %", 2, 1,
            widget_factory=lambda m: ctk.CTkComboBox(
                m, values=[str(r) for r in config.DEFAULT_TAX_RATES], font=theme.fonts.body, height=36,
                corner_radius=theme.spacing.radius // 2, border_color=theme.colors.border,
                button_color=theme.colors.primary, button_hover_color=theme.colors.primary_hover,
            ),
        )
        self.discount = self._field("Discount (₹)", 3, 0)
        self.status = self._field("Status", 3, 1, widget_factory=dropdown_factory(STATUS_OPTIONS))
        self.description = self._field(
            "Description", 4, 0, colspan=2, widget_factory=lambda m: ctk.CTkTextbox(m, height=80, font=theme.fonts.body)
        )

        self.gst_percentage.set(str(config.DEFAULT_TAX_RATE))
        self.discount.set("0")

        if course_id:
            self._load_existing(course_id)

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Save Course", command=self._save).pack(side="right")

    def _field(self, label, row, col, required=False, colspan=1, widget_factory=None):
        field = FormField(self.scroll_body, label, required=required, widget_factory=widget_factory)
        field.grid(
            row=row, column=col, columnspan=colspan, sticky="ew",
            padx=(0, theme.spacing.sm) if col == 0 and colspan == 1 else 0,
            pady=(0, theme.spacing.sm),
        )
        return field

    def _load_existing(self, course_id: int) -> None:
        course = course_controller.get_course(course_id)
        if not course:
            return
        self.name.set(course["name"])
        self.category.set(course["category"])
        self.duration.set(course["duration"])
        self.price.set(str(course["price"]))
        self.gst_percentage.set(str(course["gst_percentage"]))
        self.discount.set(str(course["discount"]))
        self.status.set(course["status"])
        self.description.set(course["description"])

    def _collect(self) -> dict:
        return {
            "name": self.name.get().strip(),
            "category": self.category.get().strip(),
            "description": self.description.get().strip(),
            "price": self.price.get().strip(),
            "gst_percentage": self.gst_percentage.get().strip(),
            "discount": self.discount.get().strip() or "0",
            "duration": self.duration.get().strip(),
            "status": self.status.get().strip(),
        }

    def _save(self) -> None:
        for field in (self.name, self.price, self.gst_percentage, self.discount):
            field.clear_error()

        data = self._collect()
        if self._course_id:
            success, message, course = course_controller.update_course(self._course_id, data)
        else:
            success, message, course = course_controller.create_course(data)

        if not success:
            self._apply_field_errors(message)
            return

        show_toast(self.master, "Course saved successfully.", variant="success")
        if self._on_saved:
            self._on_saved(course)
        self.destroy()

    def _apply_field_errors(self, message: str) -> None:
        field_by_keyword = {
            "name": self.name,
            "price": self.price,
            "gst": self.gst_percentage,
            "discount": self.discount,
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
