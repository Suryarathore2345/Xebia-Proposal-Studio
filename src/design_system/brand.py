"""Xebia Design System loader — single source of truth for brand values."""

import json
from pathlib import Path
from datetime import datetime

DESIGN_SYSTEM_DIR = Path(__file__).resolve().parent.parent.parent / "xebia_design_system" / "brand"


def _load(name: str) -> dict:
    with open(DESIGN_SYSTEM_DIR / name, encoding="utf-8") as f:
        return json.load(f)


_colors = None
_typography = None
_spacing = None
_theme = None


def colors() -> dict:
    global _colors
    if _colors is None:
        _colors = _load("colors.json")
    return _colors


def typography() -> dict:
    global _typography
    if _typography is None:
        _typography = _load("typography.json")
    return _typography


def spacing() -> dict:
    global _spacing
    if _spacing is None:
        _spacing = _load("spacing.json")
    return _spacing


def theme() -> dict:
    global _theme
    if _theme is None:
        _theme = _load("theme.json")
    return _theme


def copyright_text() -> str:
    return theme()["copyright_template"].format(year=datetime.now().year)
