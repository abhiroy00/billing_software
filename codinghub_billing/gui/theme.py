"""Centralized design system (Section 5/6/45). Every screen and component
must pull colors/fonts/spacing from here — never hard-code a hex color or
font tuple inline elsewhere in the GUI layer."""
from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk


@dataclass(frozen=True)
class Colors:
    primary: str = "#2563EB"
    primary_hover: str = "#1D4ED8"
    secondary: str = "#0F172A"
    background: str = "#F8FAFC"
    card: str = "#FFFFFF"
    text: str = "#0F172A"
    text_secondary: str = "#64748B"
    border: str = "#E2E8F0"
    success: str = "#16A34A"
    warning: str = "#F59E0B"
    danger: str = "#DC2626"
    danger_hover: str = "#B91C1C"
    info: str = "#0EA5E9"
    white: str = "#FFFFFF"


@dataclass(frozen=True)
class Fonts:
    family: str = "Segoe UI"
    page_heading: tuple = ("Segoe UI", 24, "bold")
    section_heading: tuple = ("Segoe UI", 17, "bold")
    body: tuple = ("Segoe UI", 13)
    body_bold: tuple = ("Segoe UI", 13, "bold")
    table: tuple = ("Segoe UI", 12)
    small: tuple = ("Segoe UI", 11)
    small_bold: tuple = ("Segoe UI", 11, "bold")
    button: tuple = ("Segoe UI", 13, "bold")
    kpi_value: tuple = ("Segoe UI", 26, "bold")
    logo: tuple = ("Segoe UI", 20, "bold")


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48

    radius: int = 10
    sidebar_width: int = 232


class Theme:
    colors = Colors()
    fonts = Fonts()
    spacing = Spacing()

    STATUS_COLORS = {
        "PAID": ("#16A34A", "#E7F7EE"),
        "PARTIAL": ("#F59E0B", "#FEF3E2"),
        "PENDING": ("#DC2626", "#FDEAEA"),
        "CANCELLED": ("#64748B", "#F1F5F9"),
        "ACTIVE": ("#16A34A", "#E7F7EE"),
        "INACTIVE": ("#64748B", "#F1F5F9"),
    }


def apply_ctk_defaults() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


theme = Theme()
