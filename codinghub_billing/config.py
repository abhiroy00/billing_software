"""Centralized application configuration.

Every path, constant, and default used across services/gui must be read from
here rather than hard-coded inline, so behavior (currency, tax defaults, data
locations) can change in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from utils.app_paths import ensure_app_dirs


@dataclass(frozen=True)
class AppConfig:
    APP_NAME: str = "CodingHub Billing"
    VERSION: str = "1.0.0"
    CURRENCY_SYMBOL: str = "₹"
    CURRENCY_CODE: str = "INR"
    TIMEZONE: str = "Asia/Kolkata"
    DATE_FORMAT: str = "%d-%m-%Y"
    DEFAULT_TAX_RATES: tuple = (0, 5, 12, 18, 28)
    DEFAULT_TAX_RATE: int = 18
    INVOICE_NUMBER_PREFIX: str = "CH"

    root_dir: Path = field(default_factory=lambda: ensure_app_dirs()["root"])
    data_dir: Path = field(default_factory=lambda: ensure_app_dirs()["data"])
    backup_dir: Path = field(default_factory=lambda: ensure_app_dirs()["backups"])
    invoice_dir: Path = field(default_factory=lambda: ensure_app_dirs()["invoices"])
    export_dir: Path = field(default_factory=lambda: ensure_app_dirs()["exports"])
    log_dir: Path = field(default_factory=lambda: ensure_app_dirs()["logs"])
    config_dir: Path = field(default_factory=lambda: ensure_app_dirs()["config"])

    @property
    def database_path(self) -> Path:
        return self.data_dir / "codinghub.db"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def log_file(self) -> Path:
        return self.log_dir / "app.log"


config = AppConfig()
