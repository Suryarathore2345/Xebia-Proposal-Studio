"""Content zone layouts — define where content goes on a slide.

Each zone layout computes named rectangular regions (in inches) that
slide builders fill with content. Zones account for margins, title area,
and footer clearance.
"""

from __future__ import annotations
from dataclasses import dataclass


# ── Slide geometry constants ────────────────────────────────────

SLIDE_W = 13.333
SLIDE_H = 7.500
MARGIN_L = 0.61
MARGIN_R = 0.60
TITLE_TOP = 0.60
TITLE_H = 1.24
CONTENT_TOP = 2.00
CONTENT_BOTTOM = 6.90
FOOTER_Y = 6.90

CONTENT_L = MARGIN_L
CONTENT_W = SLIDE_W - MARGIN_L - MARGIN_R
CONTENT_H = CONTENT_BOTTOM - CONTENT_TOP


@dataclass(frozen=True)
class Zone:
    """A rectangular region on a slide where content can be placed."""
    left: float
    top: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2


@dataclass
class ZoneLayout:
    """Named zones produced by a content zone layout."""
    title: Zone
    zones: dict[str, Zone]


# ── Zone Layout Functions ───────────────────────────────────────

def zone_full() -> ZoneLayout:
    """Full width content area with standard margins."""
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "main": Zone(CONTENT_L, CONTENT_TOP, CONTENT_W, CONTENT_H),
        },
    )


def zone_60_40() -> ZoneLayout:
    """60% left, 40% right split."""
    gap = 0.30
    left_w = (CONTENT_W - gap) * 0.60
    right_w = (CONTENT_W - gap) * 0.40
    right_x = CONTENT_L + left_w + gap
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "left": Zone(CONTENT_L, CONTENT_TOP, left_w, CONTENT_H),
            "right": Zone(right_x, CONTENT_TOP, right_w, CONTENT_H),
        },
    )


def zone_40_60() -> ZoneLayout:
    """40% left, 60% right split."""
    gap = 0.30
    left_w = (CONTENT_W - gap) * 0.40
    right_w = (CONTENT_W - gap) * 0.60
    right_x = CONTENT_L + left_w + gap
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "left": Zone(CONTENT_L, CONTENT_TOP, left_w, CONTENT_H),
            "right": Zone(right_x, CONTENT_TOP, right_w, CONTENT_H),
        },
    )


def zone_thirds() -> ZoneLayout:
    """Three equal columns."""
    gap = 0.20
    col_w = (CONTENT_W - 2 * gap) / 3
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "col1": Zone(CONTENT_L, CONTENT_TOP, col_w, CONTENT_H),
            "col2": Zone(CONTENT_L + col_w + gap, CONTENT_TOP, col_w, CONTENT_H),
            "col3": Zone(CONTENT_L + 2 * (col_w + gap), CONTENT_TOP, col_w, CONTENT_H),
        },
    )


def zone_center_narrow() -> ZoneLayout:
    """60% width centered content."""
    narrow_w = CONTENT_W * 0.60
    narrow_l = CONTENT_L + (CONTENT_W - narrow_w) / 2
    return ZoneLayout(
        title=Zone(narrow_l, TITLE_TOP, narrow_w, TITLE_H),
        zones={
            "main": Zone(narrow_l, CONTENT_TOP, narrow_w, CONTENT_H),
        },
    )


def zone_offset_left() -> ZoneLayout:
    """Content pushed left (~70%), decorative space on right (~30%)."""
    content_w = CONTENT_W * 0.68
    deco_w = CONTENT_W * 0.28
    deco_x = CONTENT_L + content_w + CONTENT_W * 0.04
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "main": Zone(CONTENT_L, CONTENT_TOP, content_w, CONTENT_H),
            "decoration": Zone(deco_x, CONTENT_TOP, deco_w, CONTENT_H),
        },
    )


def zone_offset_right() -> ZoneLayout:
    """Content pushed right (~70%), decorative space on left (~30%)."""
    deco_w = CONTENT_W * 0.28
    content_w = CONTENT_W * 0.68
    content_x = CONTENT_L + deco_w + CONTENT_W * 0.04
    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones={
            "decoration": Zone(CONTENT_L, CONTENT_TOP, deco_w, CONTENT_H),
            "main": Zone(content_x, CONTENT_TOP, content_w, CONTENT_H),
        },
    )


def zone_grid(cols: int = 2, rows: int = 2) -> ZoneLayout:
    """NxM card grid with automatic sizing."""
    gap_x = 0.20
    gap_y = 0.15
    card_w = (CONTENT_W - (cols - 1) * gap_x) / cols
    card_h = (CONTENT_H - (rows - 1) * gap_y) / rows

    zones = {}
    for r in range(rows):
        for c in range(cols):
            x = CONTENT_L + c * (card_w + gap_x)
            y = CONTENT_TOP + r * (card_h + gap_y)
            zones[f"cell_{r}_{c}"] = Zone(x, y, card_w, card_h)

    return ZoneLayout(
        title=Zone(CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H),
        zones=zones,
    )


def zone_grid_2x2() -> ZoneLayout:
    return zone_grid(2, 2)


def zone_grid_2x3() -> ZoneLayout:
    return zone_grid(3, 2)


def zone_grid_3x2() -> ZoneLayout:
    return zone_grid(2, 3)


# ── Registry ────────────────────────────────────────────────────

ZONE_REGISTRY: dict[str, callable] = {
    "zone_full": zone_full,
    "zone_60_40": zone_60_40,
    "zone_40_60": zone_40_60,
    "zone_thirds": zone_thirds,
    "zone_center_narrow": zone_center_narrow,
    "zone_offset_left": zone_offset_left,
    "zone_offset_right": zone_offset_right,
    "zone_grid_2x2": zone_grid_2x2,
    "zone_grid_2x3": zone_grid_2x3,
    "zone_grid_3x2": zone_grid_3x2,
}


def compute_zones(zone_id: str) -> ZoneLayout:
    fn = ZONE_REGISTRY.get(zone_id, zone_full)
    return fn()
