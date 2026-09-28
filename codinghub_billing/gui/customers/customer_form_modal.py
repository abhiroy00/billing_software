"""Add/Edit Customer modal (Section 11)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from controllers import customer_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.dialogs import Modal
from gui.components.inputs import FormField, dropdown_factory
from gui.components.toast import show_toast
from gui.theme import theme
from utils import validators
from utils.formatters import format_date, parse_date

GENDER_OPTIONS = ["", "Male", "Female", "Other"]
STATUS_OPTIONS = ["Active", "Inactive"]
NO_COURSE_LABEL = "None"


class CustomerFormModal(Modal):
    def __init__(self, master, customer_id: int | None = None, on_saved: Callable[[dict], None] | None = None):
        title = "Edit Customer" if customer_id else "New Customer"
        super().__init__(master, title=title, width=680, height=640, resizable=True, scrollable=True)
        self._customer_id = customer_id
        self._on_saved = on_saved

        self.scroll_body.grid_columnconfigure(0, weight=1)
        self.scroll_body.grid_columnconfigure(1, weight=1)

        course_options = customer_controller.list_course_options()
        self._course_name_to_id = {name: cid for cid, name in course_options}
        course_values = [NO_COURSE_LABEL] + [name for _cid, name in course_options]

        self.student_id = self._field("Student ID", 0, 0)
        self.name = self._field("Name", 0, 1, required=True)
        self.mobile = self._field("Mobile", 1, 0, required=True)
        self.email = self._field("Email", 1, 1)
        self.gender = self._field("Gender", 2, 0, widget_factory=dropdown_factory(GENDER_OPTIONS))
        self.date_of_birth = self._field("Date of Birth (DD-MM-YYYY)", 2, 1)
        self.address = self._field("Address", 3, 0, colspan=2)
        self.city = self._field("City", 4, 0)
        self.state_field = self._field("State", 4, 1)
        self.pincode = self._field("Pincode", 5, 0)
        self.gstin = self._field("GSTIN", 5, 1)
        self.pan = self._field("PAN", 6, 0)
        self.course = self._field("Course", 6, 1, widget_factory=dropdown_factory(course_values))
        self.enrollment_date = self._field("Enrollment Date (DD-MM-YYYY)", 7, 0)
        self.status = self._field("Status", 7, 1, widget_factory=dropdown_factory(STATUS_OPTIONS))
        self.notes = self._field(
            "Notes", 8, 0, colspan=2, widget_factory=lambda m: ctk.CTkTextbox(m, height=70, font=theme.fonts.body)
        )

        if customer_id:
            self._load_existing(customer_id)

        SecondaryButton(self.actions, text="Cancel", command=self.destroy).pack(side="right", padx=(theme.spacing.sm, 0))
        PrimaryButton(self.actions, text="Save Customer", command=self._save).pack(side="right")

    def _field(self, label, row, col, required=False, colspan=1, widget_factory=None):
        field = FormField(self.scroll_body, label, required=required, widget_factory=widget_factory)
        field.grid(
            row=row, column=col, columnspan=colspan, sticky="ew",
            padx=(0, theme.spacing.sm) if col == 0 and colspan == 1 else 0,
            pady=(0, theme.spacing.sm),
        )
        return field

    def _load_existing(self, customer_id: int) -> None:
        customer = customer_controller.get_customer(customer_id)
        if not customer:
            return
        self.student_id.set(customer.get("student_id") or "")
        self.name.set(customer.get("name") or "")
        self.mobile.set(customer.get("mobile") or "")
        self.email.set(customer.get("email") or "")
        self.gender.set(customer.get("gender") or "")
        self.date_of_birth.set(format_date(customer.get("date_of_birth")))
        self.address.set(customer.get("address") or "")
        self.city.set(customer.get("city") or "")
        self.state_field.set(customer.get("state") or "")
        self.pincode.set(customer.get("pincode") or "")
        self.gstin.set(customer.get("gstin") or "")
        self.pan.set(customer.get("pan") or "")
        course_id = customer.get("course_id")
        course_name = next((n for n, cid in self._course_name_to_id.items() if cid == course_id), NO_COURSE_LABEL)
        self.course.set(course_name)
        self.enrollment_date.set(format_date(customer.get("enrollment_date")))
        self.status.set(customer.get("status") or "Active")
        self.notes.set(customer.get("notes") or "")

    def _collect(self) -> dict | None:
        dob_error = validators.valid_date(self.date_of_birth.get(), field_label="Date of birth")
        enroll_error = validators.valid_date(self.enrollment_date.get(), field_label="Enrollment date")
        self.date_of_birth.set_error(dob_error)
        self.enrollment_date.set_error(enroll_error)
        if dob_error or enroll_error:
            return None

        course_name = self.course.get()
        course_id = self._course_name_to_id.get(course_name) if course_name != NO_COURSE_LABEL else None

        return {
            "student_id": self.student_id.get().strip(),
            "name": self.name.get().strip(),
            "mobile": self.mobile.get().strip(),
            "email": self.email.get().strip(),
            "gender": self.gender.get().strip(),
            "date_of_birth": parse_date(self.date_of_birth.get()) if self.date_of_birth.get().strip() else None,
            "address": self.address.get().strip(),
            "city": self.city.get().strip(),
            "state": self.state_field.get().strip(),
            "pincode": self.pincode.get().strip(),
            "gstin": self.gstin.get().strip(),
            "pan": self.pan.get().strip(),
            "course_id": course_id,
            "enrollment_date": parse_date(self.enrollment_date.get()) if self.enrollment_date.get().strip() else None,
            "status": self.status.get().strip(),
            "notes": self.notes.get().strip(),
        }

    def _save(self) -> None:
        for field in (self.name, self.mobile, self.email, self.gstin, self.pan):
            field.clear_error()

        data = self._collect()
        if data is None:
            return

        if self._customer_id:
            success, message, customer = customer_controller.update_customer(self._customer_id, data)
        else:
            success, message, customer = customer_controller.create_customer(data)

        if not success:
            self._apply_field_errors(message)
            return

        show_toast(self.master, "Customer saved successfully.", variant="success")
        if self._on_saved:
            self._on_saved(customer)
        self.destroy()

    def _apply_field_errors(self, message: str) -> None:
        field_by_keyword = {
            "name": self.name,
            "mobile": self.mobile,
            "email": self.email,
            "gstin": self.gstin,
            "pan": self.pan,
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
