"""Centralized design system (Section 5/6/45). Every screen and component
must pull colors/fonts/spacing from here — never hard-code a hex color or
font tuple inline elsewhere in the GUI layer."""
from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk


@dataclass(frozen=True)
class Colors:
    primary: str = "#4F46E5"
    primary_hover: str = "#4338CA"
    primary_soft: str = "#EEF2FF"
    secondary: str = "#0B1220"
    sidebar_hover: str = "#1A2440"
    sidebar_active: str = "#4F46E5"
    background: str = "#F1F5F9"
    card: str = "#FFFFFF"
    text: str = "#0F172A"
    text_secondary: str = "#64748B"
    border: str = "#E2E8F0"
    success: str = "#10B981"
    success_soft: str = "#D1FAE5"
    warning: str = "#F59E0B"
    warning_soft: str = "#FEF3C7"
    danger: str = "#EF4444"
    danger_hover: str = "#DC2626"
    danger_soft: str = "#FEE2E2"
    info: str = "#06B6D4"
    info_soft: str = "#CFFAFE"
    white: str = "#FFFFFF"
    gold: str = "#F59E0B"


@dataclass(frozen=True)
class Fonts:
    family: str = "Segoe UI"
    page_heading: tuple = ("Segoe UI", 26, "bold")
    section_heading: tuple = ("Segoe UI", 17, "bold")
    card_title: tuple = ("Segoe UI", 14, "bold")
    body: tuple = ("Segoe UI", 13)
    body_bold: tuple = ("Segoe UI", 13, "bold")
    table: tuple = ("Segoe UI", 12)
    small: tuple = ("Segoe UI", 11)
    small_bold: tuple = ("Segoe UI", 11, "bold")
    button: tuple = ("Segoe UI", 13, "bold")
    kpi_value: tuple = ("Segoe UI", 28, "bold")
    kpi_label: tuple = ("Segoe UI", 11, "bold")
    logo: tuple = ("Segoe UI", 20, "bold")
    hero: tuple = ("Segoe UI", 30, "bold")


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48

    radius: int = 12
    card_radius: int = 14
    sidebar_width: int = 248


class Theme:
    colors = Colors()
    fonts = Fonts()
    spacing = Spacing()

    STATUS_COLORS = {
        "PAID": ("#10B981", "#D1FAE5"),
        "PARTIAL": ("#F59E0B", "#FEF3C7"),
        "PENDING": ("#EF4444", "#FEE2E2"),
        "CANCELLED": ("#64748B", "#F1F5F9"),
        "ACTIVE": ("#10B981", "#D1FAE5"),
        "INACTIVE": ("#64748B", "#F1F5F9"),
    }

    CHART_PALETTE = ("#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6")


def apply_ctk_defaults() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


theme = Theme()
