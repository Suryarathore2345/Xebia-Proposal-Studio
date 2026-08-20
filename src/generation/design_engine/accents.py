"""Accent elements — decorative shapes applied on top of backgrounds.

Each accent adds visual interest without competing with content.
1-2 accents per slide, applied after background, before content.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from generation.design_engine.palette import PURPLE, NEUTRALS
from generation.design_engine.primitives import (
    add_rectangle, add_gradient_rectangle, add_circle, add_right_triangle,
    add_dot_pattern, add_floating_circles, set_fill_opacity,
    SLIDE_W, SLIDE_H,
)

if TYPE_CHECKING:
    from generation.design_engine.theme_generator import DesignTheme


# ── Accent Element Functions ────────────────────────────────────

def acc_none(slide, theme: DesignTheme, is_dark: bool = False):
    pass


def acc_top_bar(slide, theme: DesignTheme, is_dark: bool = False):
    """Thin colored bar across the top of the slide."""
    color = theme.primary_accent
    add_rectangle(slide, 0, 0, SLIDE_W, 0.35, fill_color=color)


def acc_top_bar_gradient(slide, theme: DesignTheme, is_dark: bool = False):
    """Gradient bar across the top."""
    gd = theme.gradient_pair
    c1 = gd.color1 if hasattr(gd, "color1") else gd[0]
    c2 = gd.color2 if hasattr(gd, "color2") else gd[1]
    add_gradient_rectangle(slide, 0, 0, SLIDE_W, 0.35, c1, c2, angle=0)


def acc_side_stripe(slide, theme: DesignTheme, is_dark: bool = False):
    """Vertical accent stripe on the left edge."""
    color = theme.primary_accent
    add_rectangle(slide, 0, 0, 0.18, SLIDE_H, fill_color=color)


def acc_side_stripe_gradient(slide, theme: DesignTheme, is_dark: bool = False):
    """Gradient vertical stripe on the left."""
    gd = theme.gradient_pair
    c1 = gd.color1 if hasattr(gd, "color1") else gd[0]
    c2 = gd.color2 if hasattr(gd, "color2") else gd[1]
    add_gradient_rectangle(slide, 0, 0, 0.18, SLIDE_H, c1, c2, angle=270)


def acc_corner_triangle(slide, theme: DesignTheme, is_dark: bool = False):
    """Right triangle in the top-right corner."""
    color = theme.secondary_accent if not is_dark else PURPLE.MUTED
    tri = add_right_triangle(slide, SLIDE_W - 2.0, 0, 2.0, 2.0,
                              fill_color=color, rotation=90)
    set_fill_opacity(tri, 0.12)


def acc_corner_circle(slide, theme: DesignTheme, is_dark: bool = False):
    """Large quarter-circle arc in the bottom-right corner."""
    color = theme.secondary_accent if not is_dark else PURPLE.MUTED
    circle = add_circle(slide, SLIDE_W + 0.3, SLIDE_H + 0.3, 1.8,
                        fill_color=color)
    set_fill_opacity(circle, 0.10 if not is_dark else 0.15)


def acc_diagonal_stripe(slide, theme: DesignTheme, is_dark: bool = False):
    """Diagonal accent stripe in the top-right area."""
    color = theme.primary_accent
    tri = add_right_triangle(slide, SLIDE_W - 3.5, 0, 3.5, 1.2,
                              fill_color=color, rotation=90)
    set_fill_opacity(tri, 0.08)


def acc_bottom_band(slide, theme: DesignTheme, is_dark: bool = False):
    """Colored band at the bottom of the slide."""
    color = theme.primary_accent
    add_rectangle(slide, 0, SLIDE_H - 0.35, SLIDE_W, 0.35, fill_color=color)


def acc_bottom_band_gradient(slide, theme: DesignTheme, is_dark: bool = False):
    """Gradient band at the bottom."""
    gd = theme.gradient_pair
    c1 = gd.color1 if hasattr(gd, "color1") else gd[0]
    c2 = gd.color2 if hasattr(gd, "color2") else gd[1]
    add_gradient_rectangle(slide, 0, SLIDE_H - 0.35, SLIDE_W, 0.35,
                           c1, c2, angle=0)


def acc_dot_pattern_element(slide, theme: DesignTheme, is_dark: bool = False):
    """Small dot grid as texture in the top-right area."""
    color = theme.secondary_accent if not is_dark else PURPLE.SOFT
    opacity = 0.06 if not is_dark else 0.10
    add_dot_pattern(slide, SLIDE_W - 3.0, 0.5, 2.5, 2.5,
                    dot_size=0.03, spacing=0.30, color=color, opacity=opacity)


def acc_floating_circles_element(slide, theme: DesignTheme,
                                  is_dark: bool = False):
    """2-3 overlapping circles as decorative accent in bottom-right."""
    color = theme.secondary_accent if not is_dark else PURPLE.MUTED
    opacity = 0.06 if not is_dark else 0.12
    add_floating_circles(slide, SLIDE_W - 1.5, SLIDE_H - 1.5,
                         color=color, opacity=opacity, count=3)


def acc_accent_line(slide, theme: DesignTheme, is_dark: bool = False):
    """Thin accent line under the title area."""
    color = theme.primary_accent
    add_rectangle(slide, 0.61, 1.92, 12.13, 0.03, fill_color=color)


# ── Registry ────────────────────────────────────────────────────

ACCENT_REGISTRY: dict[str, callable] = {
    "acc_none": acc_none,
    "acc_top_bar": acc_top_bar,
    "acc_top_bar_gradient": acc_top_bar_gradient,
    "acc_side_stripe": acc_side_stripe,
    "acc_side_stripe_gradient": acc_side_stripe_gradient,
    "acc_corner_triangle": acc_corner_triangle,
    "acc_corner_circle": acc_corner_circle,
    "acc_diagonal_stripe": acc_diagonal_stripe,
    "acc_bottom_band": acc_bottom_band,
    "acc_bottom_band_gradient": acc_bottom_band_gradient,
    "acc_dot_pattern": acc_dot_pattern_element,
    "acc_floating_circles": acc_floating_circles_element,
    "acc_accent_line": acc_accent_line,
}


def apply_accent(accent_id: str, slide, theme: DesignTheme,
                 is_dark: bool = False):
    fn = ACCENT_REGISTRY.get(accent_id, acc_none)
    fn(slide, theme, is_dark=is_dark)
