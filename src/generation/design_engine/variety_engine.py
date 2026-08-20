"""Variety engine — enforces visual distribution and anti-repetition constraints.

Post-processes blueprint selections (whether from Gemini or rule-based)
to ensure no monotonous patterns slip through.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from generation.design_engine.blueprints import (
    BLUEPRINT_REGISTRY, get_blueprint, get_light_blueprints,
)

if TYPE_CHECKING:
    from generation.design_engine.slide_designer import SlideDesignSpec


# ── Accent-family-aware swap pools ────────────────────────────

_SWAP_POOLS = {
    "topbar": [
        "white_full_topbar", "lavender_full_topbar", "offwhite_full_topbar",
        "whisper_full_topbar",
    ],
    "sidebar": [
        "white_full_sidebar", "white_full_sidebar_gradient", "coolgray_full_sidebar",
        "lavender_thirds_sidebar",
    ],
    "accent_line": [
        "white_full_accent_line", "lavender_full_accent_line", "white_60_40_accent_line",
    ],
}

_FALLBACK_POOL = [
    "white_full_topbar", "lavender_full_topbar", "offwhite_full_topbar",
    "whisper_full_topbar",
]

_SPECIAL_TYPES = {"cover", "closing"}


def _detect_accent_family(specs: list[SlideDesignSpec]) -> str:
    """Detect which accent family the deck is using."""
    from collections import Counter
    family_counts = Counter()
    for pool_name, pool_ids in _SWAP_POOLS.items():
        pool_set = set(pool_ids)
        for s in specs:
            if s.blueprint_id in pool_set:
                family_counts[pool_name] += 1
    if family_counts:
        return family_counts.most_common(1)[0][0]
    return "topbar"


def enforce_variety(specs: list[SlideDesignSpec],
                    manifest: list[dict]) -> list[SlideDesignSpec]:
    """Apply all variety constraints, mutating specs in place."""
    _fix_consecutive_duplicates(specs)
    _fix_consecutive_bg_family(specs)
    _fix_dark_overuse(specs, manifest)
    return specs


def _is_content_slide(spec: SlideDesignSpec) -> bool:
    return spec.slide_type not in _SPECIAL_TYPES


def _get_bg_family(spec: SlideDesignSpec) -> str:
    bp = BLUEPRINT_REGISTRY.get(spec.blueprint_id)
    return bp.bg_family if bp else "white"


def _get_swap_pool(specs: list[SlideDesignSpec]) -> list[str]:
    """Get the swap pool matching the deck's accent family."""
    family = _detect_accent_family(specs)
    return _SWAP_POOLS.get(family, _FALLBACK_POOL)


def _pick_different(current_id: str, exclude_ids: set[str] = None,
                    pool: list[str] = None) -> str:
    """Pick a blueprint different from current, staying in the same accent family."""
    if pool is None:
        pool = _FALLBACK_POOL
    exclude = {current_id} | (exclude_ids or set())
    for bp_id in pool:
        if bp_id not in exclude:
            return bp_id
    return pool[0]


# ── Constraint: No consecutive duplicate blueprints ─────────────

def _fix_consecutive_duplicates(specs: list[SlideDesignSpec]):
    pool = _get_swap_pool(specs)
    for i in range(1, len(specs)):
        if not _is_content_slide(specs[i]):
            continue
        if specs[i].blueprint_id == specs[i - 1].blueprint_id:
            specs[i].blueprint_id = _pick_different(
                specs[i].blueprint_id,
                {specs[i - 1].blueprint_id},
                pool=pool,
            )


# ── Constraint: No 3+ consecutive same background family ───────

def _fix_consecutive_bg_family(specs: list[SlideDesignSpec]):
    pool = _get_swap_pool(specs)
    for i in range(2, len(specs)):
        if not _is_content_slide(specs[i]):
            continue
        fam_i = _get_bg_family(specs[i])
        fam_prev = _get_bg_family(specs[i - 1])
        fam_prev2 = _get_bg_family(specs[i - 2])

        if fam_i == fam_prev == fam_prev2:
            different_family_bps = [
                bp_id for bp_id in pool
                if BLUEPRINT_REGISTRY.get(bp_id) and
                BLUEPRINT_REGISTRY[bp_id].bg_family != fam_i
            ]
            if different_family_bps:
                specs[i].blueprint_id = different_family_bps[i % len(different_family_bps)]


# ── Constraint: Dark backgrounds ≤ 15% of content slides ───────

def _fix_dark_overuse(specs: list[SlideDesignSpec], manifest: list[dict]):
    content_specs = [(i, s) for i, s in enumerate(specs) if _is_content_slide(s)]
    if not content_specs:
        return

    max_dark = max(1, int(len(content_specs) * 0.15))

    dark_indices = []
    for idx, spec in content_specs:
        bp = BLUEPRINT_REGISTRY.get(spec.blueprint_id)
        if bp and bp.is_dark:
            dark_indices.append(idx)

    while len(dark_indices) > max_dark:
        fix_idx = dark_indices.pop()
        pool = _get_swap_pool(specs)
        specs[fix_idx].blueprint_id = _pick_different(specs[fix_idx].blueprint_id, pool=pool)
