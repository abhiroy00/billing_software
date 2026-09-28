"""Resolves the application's persistent data directory.

Per the product spec, user data must never live inside a temp folder or the
executable's own directory. On Windows this resolves to
``%LOCALAPPDATA%\\CodingHub``; on other platforms it falls back to a
``.codinghub`` folder under the user's home directory (useful for running the
test suite / GUI on non-Windows CI).
"""
from __future__ import annotations

import os
from pathlib import Path


APP_FOLDER_NAME = "CodingHub"

_SUBDIRS = ("data", "backups", "invoices", "exports", "logs", "config")


def get_app_root() -> Path:
    override = os.environ.get("CODINGHUB_APP_DATA_DIR")
    if override:
        return Path(override)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_FOLDER_NAME

    return Path.home() / f".{APP_FOLDER_NAME.lower()}"


def ensure_app_dirs() -> dict[str, Path]:
    root = get_app_root()
    paths = {"root": root}
    for name in _SUBDIRS:
        sub = root / name
        sub.mkdir(parents=True, exist_ok=True)
        paths[name] = sub
    return paths
