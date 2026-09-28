"""CodingHub Billing & Business Management — application entry point.

Boot sequence: initialize the database -> route to the first-run Setup
Wizard or straight to Login -> Main Shell after a successful login.
"""
from __future__ import annotations

import sys
import traceback

if sys.platform == "win32":
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import customtkinter as ctk

from config import config
from controllers import auth_controller
from database.connection import init_db
from gui.app_shell import MainShell
from gui.login.login_view import LoginView
from gui.setup_wizard.setup_wizard_view import SetupWizardView
from gui.theme import apply_ctk_defaults
from utils.logger import USER_FRIENDLY_MESSAGE, install_global_exception_hook, setup_logging


class CodingHubApp:
    def __init__(self) -> None:
        init_db(config.database_url)
        self.logger = setup_logging(config.log_file)
        install_global_exception_hook(self.logger, on_unhandled=self._notify_fatal_error)

        apply_ctk_defaults()
        self.root = ctk.CTk()
        self.root.title(config.APP_NAME)
        self.root.geometry("1280x800")
        self.root.minsize(1024, 700)
        self.root.report_callback_exception = self._handle_tk_callback_exception

        self._current_screen: ctk.CTkFrame | None = None
        self._route_initial_screen()

    def _handle_tk_callback_exception(self, exc_type, exc_value, exc_tb) -> None:
        self.logger.error(
            "Unhandled GUI exception:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        )
        self._notify_fatal_error(exc_value)

    def _notify_fatal_error(self, _exc: BaseException) -> None:
        try:
            from gui.components.toast import show_toast

            show_toast(self.root, USER_FRIENDLY_MESSAGE, variant="error")
        except Exception:
            pass

    def _route_initial_screen(self) -> None:
        if auth_controller.is_first_run():
            self._show_setup_wizard()
        else:
            self._show_login()

    def _swap_screen(self, screen: ctk.CTkFrame) -> None:
        if self._current_screen is not None:
            self._current_screen.destroy()
        self._current_screen = screen
        screen.pack(fill="both", expand=True)

    def _show_setup_wizard(self) -> None:
        self._swap_screen(SetupWizardView(self.root, on_setup_complete=self._show_login))

    def _show_login(self) -> None:
        self._swap_screen(LoginView(self.root, on_login_success=self._show_main_shell))

    def _show_main_shell(self) -> None:
        self._swap_screen(MainShell(self.root, on_logout=self._show_login))

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    CodingHubApp().run()


if __name__ == "__main__":
    main()
