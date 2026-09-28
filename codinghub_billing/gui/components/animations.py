"""Lightweight UI animation helpers (Section 5/45).

CustomTkinter widgets don't support window alpha, so "dynamic" feel comes
from count-up numbers, staggered card entrances, hover highlights and
progress-bar easing — all implemented with plain ``after()`` callbacks so
they never block the mainloop or break headless imports.
"""
from __future__ import annotations

import re
from typing import Callable

_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _extract_number(text: str) -> tuple[str, float, str]:
    """Split '₹12,500.00' -> (prefix '₹', 12500.0, suffix '')."""
    match = _NUM_RE.search(text)
    if not match:
        return text, 0.0, ""
    prefix = text[: match.start()]
    suffix = text[match.end():]
    try:
        value = float(match.group(0).replace(",", ""))
    except ValueError:
        return text, 0.0, ""
    return prefix, value, suffix


def count_up(label, target_text: str, duration_ms: int = 700, steps: int = 24) -> None:
    """Animate a label from 0 to the numeric value in ``target_text``."""
    prefix, target, suffix = _extract_number(target_text)
    if steps <= 0 or target == 0:
        try:
            label.configure(text=target_text)
        except Exception:
            pass
        return

    decimals = 2 if "." in target_text else 0
    delay = max(1, duration_ms // steps)

    def _tick(step: int = 0) -> None:
        try:
            progress = min(1.0, (step + 1) / steps)
            eased = 1 - (1 - progress) ** 3  # ease-out cubic
            current = target * eased
            if decimals:
                rendered = f"{current:,.{decimals}f}"
            else:
                rendered = f"{int(round(current)):,}"
            label.configure(text=f"{prefix}{rendered}{suffix}")
            if progress < 1.0:
                label.after(delay, lambda: _tick(step + 1))
        except Exception:
            try:
                label.configure(text=target_text)
            except Exception:
                pass

    _tick()


def stagger_in(widgets: list, delay_ms: int = 60) -> None:
    """Reveal widgets one after another for a cascading entrance effect.

    Works by briefly hiding each widget with ``grid_remove`` and re-showing
    it on a timer. Widgets must already be gridded.
    """

    def _show(index: int) -> None:
        if index >= len(widgets):
            return
        try:
            widgets[index].grid()
        except Exception:
            pass
        try:
            widgets[index].after(delay_ms, lambda: _show(index + 1))
        except Exception:
            pass

    for widget in widgets:
        try:
            widget.grid_remove()
        except Exception:
            pass
    if widgets:
        try:
            widgets[0].after(delay_ms, lambda: _show(0))
        except Exception:
            for widget in widgets:
                try:
                    widget.grid()
                except Exception:
                    pass


def bind_hover(widget, hover_color: str, normal_color: str) -> None:
    """Swap a widget's fg_color on mouse enter/leave (sidebar buttons)."""

    def _enter(_event=None) -> None:
        try:
            widget.configure(fg_color=hover_color)
        except Exception:
            pass

    def _leave(_event=None) -> None:
        try:
            # Active button keeps its highlight — caller re-applies it.
            widget.configure(fg_color=normal_color)
        except Exception:
            pass

    try:
        widget.bind("<Enter>", _enter, add="+")
        widget.bind("<Leave>", _leave, add="+")
    except Exception:
        pass


def pulse(widget, color_a: str, color_b: str, cycles: int = 2, delay_ms: int = 180) -> None:
    """Briefly alternate a widget color (e.g. freshly-saved toast target)."""

    def _tick(step: int = 0) -> None:
        try:
            widget.configure(fg_color=color_a if step % 2 == 0 else color_b)
            if step + 1 < cycles * 2:
                widget.after(delay_ms, lambda: _tick(step + 1))
        except Exception:
            pass

    _tick()


def on_click(widget, callback: Callable[[], None]) -> None:
    """Make any widget clickable with a hand cursor."""
    try:
        widget.configure(cursor="hand2")
        widget.bind("<Button-1>", lambda _e: callback(), add="+")
    except Exception:
        pass
