"""Centralized logging + uncaught-exception handling (Section 29).

Technical errors go to logs/app.log with full tracebacks. GUI code should
catch expected exceptions and show a friendly message; anything unexpected
that reaches the Tk/sys excepthook is logged here and shown as a generic
"Something went wrong" notice instead of crashing the app.
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from typing import Callable

_configured = False

USER_FRIENDLY_MESSAGE = "Something went wrong. Please try again."


def setup_logging(log_file: Path) -> logging.Logger:
    global _configured
    logger = logging.getLogger("codinghub")
    if _configured:
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    _configured = True
    return logger


def install_global_exception_hook(
    logger: logging.Logger, on_unhandled: Callable[[BaseException], None] | None = None
) -> None:
    def handle(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error(
            "Unhandled exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        if on_unhandled is not None:
            on_unhandled(exc_value)

    sys.excepthook = handle
