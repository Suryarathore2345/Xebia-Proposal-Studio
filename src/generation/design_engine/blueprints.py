"""Slide Blueprints — curated combinations of background + zone + accents.

Each blueprint produces a distinct visual layout. Claude selects from
this library rather than inventing layouts from scratch.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from generation.design_engine.backgrounds import (
    apply_background, BackgroundResult, LIGHT_BACKGROUNDS, DARK_BACKGROUNDS,
)
from generation.design_engine.content_zones import compute_zones, ZoneLayout
from generation.design_engine.accents import apply_accent

if TYPE_CHECKING:
    from generation.design_engine.theme_generator import DesignTheme


@dataclass
class SlideBlueprint:
    id: str
    background: str                # bg_* key
    content_zone: str              # zone_* key
    accents: list[str]             # list of acc_* keys
    suitable_for: list[str]        # content types this works well with
    mood: str                      # "professional", "bold", "minimal", "calm", "premium"

    @property
    def is_dark(self) -> bool:
        return self.background in DARK_BACKGROUNDS

    @property
    def is_light(self) -> bool:
        return self.background in LIGHT_BACKGROUNDS

    @property
    def bg_family(self) -> str:
        if "white" in self.background or self.background == "bg_white":
            return "white"
        if "off_white" in self.background or "cool_gray" in self.background:
            return "off_white"
        if "lavender" in self.background:
            return "lavender"
        if "dark" in self.background:
            return "dark"
        if "gradient" in self.background:
            return "gradient"
        if "split" in self.background:
            return "split"
        if "photo" in self.background:
            return "photo"
        return "white"


@dataclass
class RenderedBlueprint:
    """Result of rendering a blueprint onto a slide."""
    zones: ZoneLayout
    bg_result: BackgroundResult


def render_blueprint(slide, blueprint: SlideBlueprint,
                     theme: DesignTheme) -> RenderedBlueprint:
    """Apply background, compute zones, apply accents. Returns zones for content filling."""
    bg_result = apply_background(blueprint.background, slide, theme)
    zones = compute_zones(blueprint.content_zone)
    for accent_id in blueprint.accents:
        apply_accent(accent_id, slide, theme, is_dark=bg_result.is_dark)
    return RenderedBlueprint(zones=zones, bg_result=bg_result)


# ── Blueprint Definitions ───────────────────────────────────────

_BLUEPRINTS: list[SlideBlueprint] = [
    # ── White backgrounds (professional, clean) ──────────────
    SlideBlueprint(
        id="white_full_topbar",
        background="bg_white",
        content_zone="zone_full",
        accents=["acc_top_bar"],
        suitable_for=["content", "key_value", "stats_highlight", "challenges"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_full_accent_line",
        background="bg_white",
        content_zone="zone_full",
        accents=["acc_accent_line"],
        suitable_for=["content", "executive_summary", "key_value", "comparison_table"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_full_sidebar",
        background="bg_white",
        content_zone="zone_full",
        accents=["acc_side_stripe"],
        suitable_for=["content", "icon_grid", "process_flow"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_full_sidebar_gradient",
        background="bg_white",
        content_zone="zone_full",
        accents=["acc_side_stripe_gradient"],
        suitable_for=["content", "technology", "icon_grid"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_60_40_diagonal",
        background="bg_white",
        content_zone="zone_60_40",
        accents=["acc_diagonal_stripe"],
        suitable_for=["two_column", "key_value", "content"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_60_40_accent_line",
        background="bg_white",
        content_zone="zone_60_40",
        accents=["acc_accent_line"],
        suitable_for=["two_column", "content"],
        mood="calm",
    ),
    SlideBlueprint(
        id="white_40_60_topbar",
        background="bg_white",
        content_zone="zone_40_60",
        accents=["acc_top_bar"],
        suitable_for=["two_column", "content"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_thirds_topbar",
        background="bg_white",
        content_zone="zone_thirds",
        accents=["acc_top_bar"],
        suitable_for=["comparison_table", "icon_grid", "team"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_offset_left_circles",
        background="bg_white",
        content_zone="zone_offset_left",
        accents=["acc_floating_circles"],
        suitable_for=["architecture", "content", "technology"],
        mood="calm",
    ),
    SlideBlueprint(
        id="white_offset_right_dots",
        background="bg_white",
        content_zone="zone_offset_right",
        accents=["acc_dot_pattern"],
        suitable_for=["timeline", "content", "process_flow"],
        mood="calm",
    ),
    SlideBlueprint(
        id="white_grid_bottom",
        background="bg_white",
        content_zone="zone_grid_2x2",
        accents=["acc_bottom_band_gradient"],
        suitable_for=["process_flow", "icon_grid", "challenges"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_grid_2x3_topbar",
        background="bg_white",
        content_zone="zone_grid_2x3",
        accents=["acc_top_bar"],
        suitable_for=["icon_grid", "technology", "team"],
        mood="professional",
    ),
    SlideBlueprint(
        id="white_center_corner",
        background="bg_white",
        content_zone="zone_center_narrow",
        accents=["acc_corner_circle"],
        suitable_for=["stats_highlight", "content"],
        mood="minimal",
    ),

    # ── Lavender backgrounds (soft, approachable) ────────────
    SlideBlueprint(
        id="lavender_full_topbar",
        background="bg_lavender",
        content_zone="zone_full",
        accents=["acc_top_bar"],
        suitable_for=["content", "stats_highlight", "key_value"],
        mood="calm",
    ),
    SlideBlueprint(
        id="lavender_full_accent_line",
        background="bg_lavender",
        content_zone="zone_full",
        accents=["acc_accent_line"],
        suitable_for=["content", "executive_summary"],
        mood="calm",
    ),
    SlideBlueprint(
        id="lavender_center",
        background="bg_lavender",
        content_zone="zone_center_narrow",
        accents=["acc_none"],
        suitable_for=["stats_highlight", "content"],
        mood="minimal",
    ),
    SlideBlueprint(
        id="lavender_grid",
        background="bg_lavender",
        content_zone="zone_grid_2x3",
        accents=["acc_bottom_band"],
        suitable_for=["icon_grid", "technology"],
        mood="calm",
    ),
    SlideBlueprint(
        id="lavender_thirds_sidebar",
        background="bg_lavender",
        content_zone="zone_thirds",
        accents=["acc_side_stripe"],
        suitable_for=["comparison_table", "team", "icon_grid"],
        mood="calm",
    ),

    # ── Off-white / Cool gray backgrounds ────────────────────
    SlideBlueprint(
        id="offwhite_full_topbar",
        background="bg_off_white",
        content_zone="zone_full",
        accents=["acc_top_bar"],
        suitable_for=["content", "process_flow"],
        mood="professional",
    ),
    SlideBlueprint(
        id="offwhite_thirds_corners",
        background="bg_off_white",
        content_zone="zone_thirds",
        accents=["acc_corner_circle"],
        suitable_for=["comparison_table", "team", "icon_grid"],
        mood="calm",
    ),
    SlideBlueprint(
        id="coolgray_full_sidebar",
        background="bg_cool_gray",
        content_zone="zone_full",
        accents=["acc_side_stripe"],
        suitable_for=["content", "challenges"],
        mood="professional",
    ),

    # ── Gradient backgrounds (subtle energy) ─────────────────
    SlideBlueprint(
        id="whisper_full_topbar",
        background="bg_gradient_whisper",
        content_zone="zone_full",
        accents=["acc_top_bar_gradient"],
        suitable_for=["content", "stats_highlight"],
        mood="calm",
    ),
    SlideBlueprint(
        id="whisper_60_40",
        background="bg_gradient_whisper",
        content_zone="zone_60_40",
        accents=["acc_accent_line"],
        suitable_for=["two_column", "content"],
        mood="calm",
    ),

    # ── Split backgrounds ────────────────────────────────────
    SlideBlueprint(
        id="split_left_content",
        background="bg_split_left",
        content_zone="zone_60_40",
        accents=["acc_none"],
        suitable_for=["two_column", "content"],
        mood="bold",
    ),
    SlideBlueprint(
        id="split_top_content",
        background="bg_split_top",
        content_zone="zone_full",
        accents=["acc_none"],
        suitable_for=["content", "stats_highlight"],
        mood="bold",
    ),

    # ── Dark backgrounds (premium, impactful) ────────────────
    SlideBlueprint(
        id="dark_full_accent_line",
        background="bg_dark",
        content_zone="zone_full",
        accents=["acc_accent_line"],
        suitable_for=["content", "stats_highlight", "key_value"],
        mood="premium",
    ),
    SlideBlueprint(
        id="dark_full_corners",
        background="bg_dark",
        content_zone="zone_full",
        accents=["acc_corner_circle", "acc_bottom_band"],
        suitable_for=["section_divider", "content"],
        mood="premium",
    ),
    SlideBlueprint(
        id="dark_full_topbar_gradient",
        background="bg_dark",
        content_zone="zone_full",
        accents=["acc_top_bar_gradient"],
        suitable_for=["content", "challenges", "stats_highlight"],
        mood="bold",
    ),
    SlideBlueprint(
        id="dark_center_gradient",
        background="bg_gradient_dark",
        content_zone="zone_center_narrow",
        accents=["acc_none"],
        suitable_for=["cover", "closing", "section_divider"],
        mood="premium",
    ),
    SlideBlueprint(
        id="dark_gradient_topbar",
        background="bg_gradient_purple",
        content_zone="zone_full",
        accents=["acc_top_bar"],
        suitable_for=["content", "stats_highlight"],
        mood="bold",
    ),

    # ── Photo wash ───────────────────────────────────────────
    SlideBlueprint(
        id="photo_wash_full",
        background="bg_photo_wash",
        content_zone="zone_full",
        accents=["acc_bottom_band"],
        suitable_for=["content", "section_divider"],
        mood="bold",
    ),
]


# ── Blueprint Registry ──────────────────────────────────────────

BLUEPRINT_REGISTRY: dict[str, SlideBlueprint] = {
    bp.id: bp for bp in _BLUEPRINTS
}


def get_blueprint(blueprint_id: str) -> SlideBlueprint:
    return BLUEPRINT_REGISTRY.get(blueprint_id, BLUEPRINT_REGISTRY["white_full_accent_line"])


def get_blueprints_for_content_type(content_type: str) -> list[SlideBlueprint]:
    return [bp for bp in _BLUEPRINTS if content_type in bp.suitable_for]


def get_light_blueprints() -> list[SlideBlueprint]:
    return [bp for bp in _BLUEPRINTS if bp.is_light]


def get_dark_blueprints() -> list[SlideBlueprint]:
    return [bp for bp in _BLUEPRINTS if bp.is_dark]


def get_blueprints_by_mood(mood: str) -> list[SlideBlueprint]:
    return [bp for bp in _BLUEPRINTS if bp.mood == mood]
