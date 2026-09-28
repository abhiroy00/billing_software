"""Backup folder panel (Settings -> Backup)."""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from controllers import settings_controller
from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.cards import Card
from gui.components.toast import show_toast
from gui.theme import theme


class BackupPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._pending_dir: str | None = None

        card = Card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="💾  Backup Folder", font=theme.fonts.card_title,
            text_color=theme.colors.text, anchor="w",
        ).grid(row=0, column=0, sticky="w",
               padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        ctk.CTkLabel(
            card, text="Database backup isi folder me store hoga. Folder save karna na bhoolo.",
            font=theme.fonts.small, text_color=theme.colors.text_secondary, anchor="w",
        ).grid(row=1, column=0, sticky="w",
               padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        self.path_label = ctk.CTkLabel(
            card, text="", font=theme.fonts.body, text_color=theme.colors.text,
            anchor="w", fg_color=theme.colors.background,
            corner_radius=theme.spacing.radius // 2,
        )
        self.path_label.grid(row=2, column=0, sticky="ew",
                             padx=theme.spacing.md, pady=(0, theme.spacing.sm), ipady=8)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="w",
                     padx=theme.spacing.md, pady=(0, theme.spacing.md))
        SecondaryButton(btn_row, text="Choose Folder", icon="📁", command=self._choose).pack(
            side="left", padx=(0, theme.spacing.sm))
        SecondaryButton(btn_row, text="Open Folder", icon="🔍", command=self._open).pack(
            side="left", padx=(0, theme.spacing.sm))
        PrimaryButton(btn_row, text="Save Folder", command=self._save).pack(side="left")

        self._load()

    def _load(self) -> None:
        current = settings_controller.get_backup_dir()
        self._pending_dir = current
        self.path_label.configure(text=f"  {current}  ")

    def _choose(self) -> None:
        chosen = filedialog.askdirectory(title="Select backup folder", initialdir=self._pending_dir)
        if chosen:
            self._pending_dir = chosen
            self.path_label.configure(text=f"  {chosen}  ")

    def _open(self) -> None:
        success, message = settings_controller.open_backup_folder()
        if not success:
            show_toast(self.winfo_toplevel(), message, variant="error")

    def _save(self) -> None:
        if not self._pending_dir:
            show_toast(self.winfo_toplevel(), "Pehle Choose Folder se ek folder select karo.",
                       variant="error")
            return
        success, message, saved = settings_controller.set_backup_dir(self._pending_dir)
        if not success:
            show_toast(self.winfo_toplevel(), message, variant="error")
            return
        self._pending_dir = saved
        self.path_label.configure(text=f"  {saved}  ")
        show_toast(self.winfo_toplevel(), "Backup folder saved.", variant="success")
