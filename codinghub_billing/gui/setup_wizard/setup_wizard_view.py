"""First-time Setup Wizard (Section 9): Business Info -> Admin Account ->
Invoice Settings -> Backup Settings -> Finish."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from config import config
from controllers import auth_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.inputs import FormField
from gui.theme import theme
from utils import validators
from utils.image_utils import save_uploaded_image


class _WizardStep(ctk.CTkFrame):
    title = ""
    subtitle = ""

    def __init__(self, master, data: dict):
        super().__init__(master, fg_color="transparent")
        self.data = data
        ctk.CTkLabel(self, text=self.title, font=theme.fonts.page_heading, text_color=theme.colors.text).pack(
            anchor="w", pady=(0, 2)
        )
        if self.subtitle:
            ctk.CTkLabel(
                self, text=self.subtitle, font=theme.fonts.body, text_color=theme.colors.text_secondary
            ).pack(anchor="w", pady=(0, theme.spacing.lg))
        else:
            ctk.CTkLabel(self, text="", height=theme.spacing.md).pack()

        self.fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.fields_frame.pack(fill="x")
        self.fields_frame.grid_columnconfigure(0, weight=1)
        self.fields_frame.grid_columnconfigure(1, weight=1)

    def validate(self) -> list[str]:
        return []

    def collect(self) -> dict:
        return {}


class BusinessInfoStep(_WizardStep):
    title = "Business Information"
    subtitle = "Tell us about your business — this appears on every invoice."

    def __init__(self, master, data: dict):
        super().__init__(master, data)

        self.business_name = FormField(self.fields_frame, "Business Name", required=True)
        self.business_name.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, theme.spacing.sm))

        self.phone = FormField(self.fields_frame, "Phone")
        self.phone.grid(row=1, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
        self.email = FormField(self.fields_frame, "Email")
        self.email.grid(row=1, column=1, sticky="ew", pady=(0, theme.spacing.sm))

        self.gstin = FormField(self.fields_frame, "GSTIN")
        self.gstin.grid(row=2, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
        self.pan = FormField(self.fields_frame, "PAN")
        self.pan.grid(row=2, column=1, sticky="ew", pady=(0, theme.spacing.sm))

        self.address = FormField(self.fields_frame, "Address")
        self.address.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, theme.spacing.sm))

        self.state = FormField(self.fields_frame, "State")
        self.state.grid(row=4, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
        self.state_code = FormField(self.fields_frame, "State Code")
        self.state_code.grid(row=4, column=1, sticky="ew", pady=(0, theme.spacing.sm))

        logo_row = ctk.CTkFrame(self.fields_frame, fg_color="transparent")
        logo_row.grid(row=5, column=0, columnspan=2, sticky="w", pady=(theme.spacing.sm, 0))
        self._logo_path: str | None = None
        self.logo_status = ctk.CTkLabel(
            logo_row, text="No logo selected", font=theme.fonts.small, text_color=theme.colors.text_secondary
        )
        self.logo_status.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(logo_row, text="Upload Logo", icon="\U0001F5BC", command=self._pick_logo).pack(side="left")

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Select business logo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")],
        )
        if not path:
            return
        try:
            saved_path = save_uploaded_image(path, config.config_dir, "logo.png")
            self._logo_path = saved_path
            self.logo_status.configure(text=Path(path).name, text_color=theme.colors.success)
        except ValueError as exc:
            self.logo_status.configure(text=str(exc), text_color=theme.colors.danger)

    def validate(self) -> list[str]:
        errors = validators.run_validators(
            validators.required(self.business_name.get(), "Business name"),
            validators.valid_email(self.email.get()),
            validators.valid_gstin(self.gstin.get()),
            validators.valid_pan(self.pan.get()),
        )
        self.business_name.set_error(next((e for e in errors if "Business name" in e), None))
        self.email.set_error(next((e for e in errors if "Email" in e), None))
        self.gstin.set_error(next((e for e in errors if "GSTIN" in e), None))
        self.pan.set_error(next((e for e in errors if "PAN" in e), None))
        return errors

    def collect(self) -> dict:
        return {
            "business_info": {
                "business_name": self.business_name.get().strip(),
                "phone": self.phone.get().strip(),
                "email": self.email.get().strip(),
                "gstin": self.gstin.get().strip().upper(),
                "pan": self.pan.get().strip().upper(),
                "address": self.address.get().strip(),
                "state": self.state.get().strip(),
                "state_code": self.state_code.get().strip(),
                "logo_path": self._logo_path,
            }
        }


class AdminAccountStep(_WizardStep):
    title = "Admin Account"
    subtitle = "Create the first administrator account for this installation."

    def __init__(self, master, data: dict):
        super().__init__(master, data)

        self.full_name = FormField(self.fields_frame, "Full Name", required=True)
        self.full_name.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, theme.spacing.sm))

        self.username = FormField(self.fields_frame, "Username", required=True)
        self.username.grid(row=1, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
        self.email = FormField(self.fields_frame, "Email (optional)")
        self.email.grid(row=1, column=1, sticky="ew", pady=(0, theme.spacing.sm))

        self.password = FormField(self.fields_frame, "Password", required=True, show="*")
        self.password.grid(row=2, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))
        self.confirm_password = FormField(self.fields_frame, "Confirm Password", required=True, show="*")
        self.confirm_password.grid(row=2, column=1, sticky="ew", pady=(0, theme.spacing.sm))

    def validate(self) -> list[str]:
        password = self.password.get()
        confirm = self.confirm_password.get()

        password_error = None
        if not password:
            password_error = "Password is required."
        elif len(password) < 6:
            password_error = "Password must be at least 6 characters."

        confirm_error = None
        if password and confirm != password:
            confirm_error = "Passwords do not match."

        errors = validators.run_validators(
            validators.required(self.full_name.get(), "Full name"),
            validators.required(self.username.get(), "Username"),
            validators.valid_email(self.email.get()),
            password_error,
            confirm_error,
        )
        self.full_name.set_error(next((e for e in errors if "Full name" in e), None))
        self.username.set_error(next((e for e in errors if "Username" in e), None))
        self.email.set_error(next((e for e in errors if "Email" in e), None))
        self.password.set_error(password_error)
        self.confirm_password.set_error(confirm_error)
        return errors

    def collect(self) -> dict:
        return {
            "admin_info": {
                "full_name": self.full_name.get().strip(),
                "username": self.username.get().strip(),
                "email": self.email.get().strip() or None,
                "password": self.password.get(),
            }
        }


class InvoiceSettingsStep(_WizardStep):
    title = "Invoice Settings"
    subtitle = "Configure how your invoice numbers, terms, and signature look."

    def __init__(self, master, data: dict):
        super().__init__(master, data)

        self.prefix = FormField(self.fields_frame, "Invoice Prefix", required=True)
        self.prefix.set("CH")
        self.prefix.grid(row=0, column=0, sticky="ew", padx=(0, theme.spacing.sm), pady=(0, theme.spacing.sm))

        self.starting_number = FormField(self.fields_frame, "Starting Number", required=True)
        self.starting_number.set("1")
        self.starting_number.grid(row=0, column=1, sticky="ew", pady=(0, theme.spacing.sm))

        self.terms = FormField(
            self.fields_frame, "Terms & Conditions",
            widget_factory=lambda m: ctk.CTkTextbox(m, height=70, font=theme.fonts.body),
        )
        self.terms.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, theme.spacing.sm))

        self.footer_text = FormField(self.fields_frame, "Invoice Footer Text")
        self.footer_text.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, theme.spacing.sm))

        sig_row = ctk.CTkFrame(self.fields_frame, fg_color="transparent")
        sig_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(theme.spacing.sm, 0))
        self._signature_path: str | None = None
        self.signature_status = ctk.CTkLabel(
            sig_row, text="No signature selected", font=theme.fonts.small, text_color=theme.colors.text_secondary
        )
        self.signature_status.pack(side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(sig_row, text="Upload Signature", icon="✍", command=self._pick_signature).pack(side="left")

    def _pick_signature(self) -> None:
        path = filedialog.askopenfilename(
            title="Select authorized signature image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")],
        )
        if not path:
            return
        try:
            saved_path = save_uploaded_image(path, config.config_dir, "signature.png", max_size=(300, 150))
            self._signature_path = saved_path
            self.signature_status.configure(text=Path(path).name, text_color=theme.colors.success)
        except ValueError as exc:
            self.signature_status.configure(text=str(exc), text_color=theme.colors.danger)

    def validate(self) -> list[str]:
        errors = validators.run_validators(
            validators.required(self.prefix.get(), "Invoice prefix"),
            validators.valid_numeric(self.starting_number.get(), "Starting number"),
        )
        self.prefix.set_error(next((e for e in errors if "prefix" in e), None))
        self.starting_number.set_error(next((e for e in errors if "Starting number" in e), None))
        return errors

    def collect(self) -> dict:
        starting = int(float(self.starting_number.get() or 1))
        return {
            "invoice_info": {
                "prefix": self.prefix.get().strip().upper(),
                "starting_number": starting,
                "next_number": starting,
                "terms": self.terms.get(),
                "footer_text": self.footer_text.get().strip(),
                "signature_path": self._signature_path,
            }
        }


class BackupSettingsStep(_WizardStep):
    title = "Backup Settings"
    subtitle = "Choose where CodingHub should store database backups."

    def __init__(self, master, data: dict):
        super().__init__(master, data)
        self._backup_dir = str(config.backup_dir)

        row = ctk.CTkFrame(self.fields_frame, fg_color="transparent")
        row.grid(row=0, column=0, columnspan=2, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.path_label = ctk.CTkLabel(
            row, text=self._backup_dir, font=theme.fonts.body, text_color=theme.colors.text,
            anchor="w", fg_color=theme.colors.background, corner_radius=theme.spacing.radius // 2,
        )
        self.path_label.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, theme.spacing.sm))
        SecondaryButton(row, text="Change Folder", icon="\U0001F4C1", command=self._pick_folder).grid(row=0, column=1)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Select backup folder", initialdir=self._backup_dir)
        if chosen:
            self._backup_dir = chosen
            self.path_label.configure(text=self._backup_dir)

    def collect(self) -> dict:
        return {"backup_dir": self._backup_dir}


class FinishStep(_WizardStep):
    title = "Finish"
    subtitle = "Review your setup and complete installation."

    def __init__(self, master, data: dict):
        super().__init__(master, data)
        business = data.get("business_info", {})
        admin = data.get("admin_info", {})
        invoice = data.get("invoice_info", {})
        backup_dir = data.get("backup_dir", str(config.backup_dir))

        summary_lines = [
            f"Business Name:  {business.get('business_name', '')}",
            f"Admin Username:  {admin.get('full_name', '')} ({admin.get('username', '')})",
            f"Invoice Prefix:  {invoice.get('prefix', '')}-{invoice.get('starting_number', '')}",
            f"Backup Folder:  {backup_dir}",
        ]
        summary = ctk.CTkFrame(self.fields_frame, fg_color=theme.colors.background, corner_radius=theme.spacing.radius)
        summary.grid(row=0, column=0, columnspan=2, sticky="ew")
        for i, line in enumerate(summary_lines):
            ctk.CTkLabel(summary, text=line, font=theme.fonts.body, text_color=theme.colors.text, anchor="w").pack(
                anchor="w", padx=theme.spacing.md, pady=(theme.spacing.sm if i else theme.spacing.md, 2 if i < len(summary_lines) - 1 else theme.spacing.md)
            )
        self.result_label = ctk.CTkLabel(self, text="", font=theme.fonts.body, text_color=theme.colors.danger)
        self.result_label.pack(anchor="w", pady=(theme.spacing.md, 0))


STEP_CLASSES = [BusinessInfoStep, AdminAccountStep, InvoiceSettingsStep, BackupSettingsStep, FinishStep]


class SetupWizardView(ctk.CTkFrame):
    def __init__(self, master, on_setup_complete: Callable[[], None]):
        super().__init__(master, fg_color=theme.colors.background)
        self._on_setup_complete = on_setup_complete
        self._data: dict = {}
        self._index = 0
        self._current_step: _WizardStep | None = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.step_indicator = ctk.CTkLabel(self, text="", font=theme.fonts.small_bold, text_color=theme.colors.primary)
        self.step_indicator.grid(row=0, column=0, sticky="w", padx=theme.spacing.xxl, pady=(theme.spacing.xl, 0))

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=theme.spacing.xxl, pady=theme.spacing.md)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="e", padx=theme.spacing.xxl, pady=(0, theme.spacing.xl))

        self.back_button = SecondaryButton(nav, text="Back", command=self._go_back)
        self.back_button.pack(side="left", padx=(0, theme.spacing.sm))
        self.next_button = PrimaryButton(nav, text="Next", command=self._go_next)
        self.next_button.pack(side="left")

        self._show_step(0)

    def _show_step(self, index: int) -> None:
        for child in self.content.winfo_children():
            child.destroy()

        self._index = index
        step_cls = STEP_CLASSES[index]
        self._current_step = step_cls(self.content, self._data)
        self._current_step.pack(fill="both", expand=True)

        self.step_indicator.configure(text=f"STEP {index + 1} OF {len(STEP_CLASSES)}")
        self.back_button.configure(state="disabled" if index == 0 else "normal")
        self.next_button.configure(text="Complete Setup" if index == len(STEP_CLASSES) - 1 else "Next")

    def _go_back(self) -> None:
        if self._index > 0:
            self._show_step(self._index - 1)

    def _go_next(self) -> None:
        assert self._current_step is not None
        if self._current_step.validate():
            return
        self._data.update(self._current_step.collect())

        if self._index < len(STEP_CLASSES) - 1:
            self._show_step(self._index + 1)
        else:
            self._finish()

    def _finish(self) -> None:
        success, message = auth_controller.complete_first_run_setup(
            business_info=self._data.get("business_info", {}),
            admin_info=self._data.get("admin_info", {}),
            invoice_info=self._data.get("invoice_info", {}),
        )
        if not success:
            assert self._current_step is not None
            self._current_step.result_label.configure(text=message)
            return

        backup_dir = self._data.get("backup_dir")
        if backup_dir:
            auth_controller.set_backup_dir_override(backup_dir)

        self._on_setup_complete()
