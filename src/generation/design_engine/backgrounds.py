"""Background treatments for slides.

Each treatment applies a full-slide or partial-slide background.
Called before content zones and accent elements.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from generation.design_engine.palette import PURPLE, NEUTRALS, GRADIENTS
from generation.design_engine.primitives import (
    add_rectangle, add_full_slide_background, add_gradient_rectangle,
    set_fill_opacity, SLIDE_W, SLIDE_H,
)

if TYPE_CHECKING:
    from generation.design_engine.theme_generator import DesignTheme


@dataclass
class BackgroundResult:
    """Metadata about the applied background, for downstream decisions."""
    is_dark: bool = False
    has_gradient: bool = False
    has_split: bool = False
    has_photo: bool = False


# ── Background Treatment Functions ──────────────────────────────

def bg_white(slide, theme: DesignTheme) -> BackgroundResult:
    return BackgroundResult()


def bg_off_white(slide, theme: DesignTheme) -> BackgroundResult:
    add_full_slide_background(slide, fill_color=NEUTRALS.OFF_WHITE)
    return BackgroundResult()


def bg_lavender(slide, theme: DesignTheme) -> BackgroundResult:
    add_full_slide_background(slide, fill_color=PURPLE.BG)
    return BackgroundResult()


def bg_cool_gray(slide, theme: DesignTheme) -> BackgroundResult:
    add_full_slide_background(slide, fill_color=NEUTRALS.COOL_GRAY)
    return BackgroundResult()


def bg_dark(slide, theme: DesignTheme) -> BackgroundResult:
    add_full_slide_background(slide, fill_color=NEUTRALS.BLACK)
    return BackgroundResult(is_dark=True)


def bg_gradient_whisper(slide, theme: DesignTheme) -> BackgroundResult:
    gd = GRADIENTS.WHISPER
    add_full_slide_background(slide, gradient_colors=(gd.color1, gd.color2))
    return BackgroundResult(has_gradient=True)


def bg_gradient_purple(slide, theme: DesignTheme) -> BackgroundResult:
    gd = theme.gradient_pair if theme.gradient_pair else GRADIENTS.MEDIUM
    c1 = gd.color1 if hasattr(gd, "color1") else gd[0]
    c2 = gd.color2 if hasattr(gd, "color2") else gd[1]
    add_full_slide_background(slide, gradient_colors=(c1, c2))
    return BackgroundResult(is_dark=True, has_gradient=True)


def bg_gradient_dark(slide, theme: DesignTheme) -> BackgroundResult:
    gd = GRADIENTS.PURPLE_TO_BLACK
    add_full_slide_background(slide, gradient_colors=(gd.color1, gd.color2))
    return BackgroundResult(is_dark=True, has_gradient=True)


def bg_split_left(slide, theme: DesignTheme) -> BackgroundResult:
    """Left 35% colored, right 65% white."""
    split_w = SLIDE_W * 0.35
    add_rectangle(slide, 0, 0, split_w, SLIDE_H, fill_color=PURPLE.BG)
    return BackgroundResult(has_split=True)


def bg_split_top(slide, theme: DesignTheme) -> BackgroundResult:
    """Top 40% dark/accent, bottom 60% white."""
    split_h = SLIDE_H * 0.40
    bg = add_rectangle(slide, 0, 0, SLIDE_W, split_h, fill_color=NEUTRALS.BLACK)
    return BackgroundResult(has_split=True, is_dark=False)


def bg_photo_wash(slide, theme: DesignTheme) -> BackgroundResult:
    """Semi-transparent purple overlay for photo backgrounds."""
    overlay = add_rectangle(slide, 0, 0, SLIDE_W, SLIDE_H,
                            fill_color=PURPLE.DARK)
    set_fill_opacity(overlay, 0.65)
    return BackgroundResult(is_dark=True, has_photo=True)


# ── Registry ────────────────────────────────────────────────────

BACKGROUND_REGISTRY: dict[str, callable] = {
    "bg_white": bg_white,
    "bg_off_white": bg_off_white,
    "bg_lavender": bg_lavender,
    "bg_cool_gray": bg_cool_gray,
    "bg_dark": bg_dark,
    "bg_gradient_whisper": bg_gradient_whisper,
    "bg_gradient_purple": bg_gradient_purple,
    "bg_gradient_dark": bg_gradient_dark,
    "bg_split_left": bg_split_left,
    "bg_split_top": bg_split_top,
    "bg_photo_wash": bg_photo_wash,
}

LIGHT_BACKGROUNDS = {"bg_white", "bg_off_white", "bg_lavender", "bg_cool_gray",
                     "bg_gradient_whisper"}
DARK_BACKGROUNDS = {"bg_dark", "bg_gradient_purple", "bg_gradient_dark",
                    "bg_photo_wash"}


def apply_background(bg_id: str, slide, theme: DesignTheme) -> BackgroundResult:
    fn = BACKGROUND_REGISTRY.get(bg_id, bg_white)
    return fn(slide, theme)
