"""Per-slide blueprint selection — Claude picks blueprints for each slide.

Given the slide manifest and design theme, selects and parameterizes
a blueprint for every slide. Falls back to rule-based selection
if Claude is unavailable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, field

from generation.design_engine.blueprints import (
    SlideBlueprint, BLUEPRINT_REGISTRY, get_blueprint,
)
from generation.design_engine.theme_generator import DesignTheme
from generation.design_engine.variety_engine import enforce_variety
from generation.slide_builders import has_customer_portfolio_logos


@dataclass
class SlideDesignSpec:
    """Design specification for a single slide."""
    slide_id: str
    slide_type: str
    blueprint_id: str
    accent_override: str | None = None
    card_style_override: str | None = None
    title_alignment: str = "left"


# ── Slide manifest builder ──────────────────────────────────────

def build_slide_manifest(plan: dict, reuse_master_slides: bool = False) -> list[dict]:
    """Enumerate every slide that will be generated, in order.

    When reuse_master_slides is True, cover/TOC/corporate_overview are
    entirely represented by the master template's own reused slides
    (patched/regenerated in place, not spec-driven) — they're excluded here
    so design_slides()'s output stays positionally aligned with the actual
    _next_spec() calls ProposalPPTGenerator.generate() makes."""
    slides = []
    storyline = plan.get("storyline", [])
    sections = plan.get("sections", {})

    for section_key in storyline:
        section = sections.get(section_key, {})
        title = section.get("title", section_key.replace("_", " ").title())

        if section_key == "cover":
            if not reuse_master_slides:
                slides.append({"id": "cover", "type": "cover", "title": title})
        elif section_key == "table_of_contents":
            if not reuse_master_slides:
                slides.append({"id": "toc", "type": "toc", "title": "Table of Contents"})
        elif section_key == "closing":
            slides.append({"id": "closing", "type": "closing", "title": title})
        elif section_key == "corporate_overview" and reuse_master_slides:
            continue
        else:
            slides.append({
                "id": f"{section_key}_div",
                "type": "section_divider",
                "title": title,
            })

            if section_key == "corporate_overview":
                layout = section.get("layout", "icon_grid")
                slides.append({"id": f"{section_key}_0", "type": layout, "title": title})
                slides.append({"id": "xebia_capabilities", "type": "icon_grid", "title": "Why Xebia"})
                slides.append({"id": "global_presence", "type": "content", "title": "Global Presence"})
                if has_customer_portfolio_logos():
                    slides.append({"id": "customer_portfolio", "type": "content", "title": "Xebia Customer Portfolio"})
            elif section_key == "executive_summary":
                slides.append({"id": "exec_summary", "type": "content", "title": title})
            else:
                sub_slides = section.get("slides", [])
                if sub_slides:
                    for i, s in enumerate(sub_slides):
                        slides.append({
                            "id": f"{section_key}_{i}",
                            "type": s.get("layout", "content"),
                            "title": s.get("title", title),
                        })
                else:
                    layout = section.get("layout", "content")
                    slides.append({
                        "id": f"{section_key}_0",
                        "type": layout,
                        "title": title,
                    })

    return slides


# ── Claude-based selection ───────────────────────────────────────

DESIGNER_PROMPT = """\
You are a presentation layout designer. For each slide below, select the best
blueprint from the available list.

DESIGN THEME: {theme_name}
Primary accent: {primary_accent} | Secondary: {secondary_accent}

SLIDE MANIFEST:
{slide_manifest}

AVAILABLE BLUEPRINTS:
{blueprint_list}

RULES:
- Cover and closing MUST use dark_center_gradient
- ALL other slides (dividers, TOC, content) must use LIGHT blueprints — no dark backgrounds
- CRITICAL: Pick ONE accent style for the ENTIRE deck (topbar OR sidebar OR accent_line)
  and use it consistently on every slide. Do NOT mix accent positions — a deck with
  top bars on some slides and side stripes on others looks inconsistent and unprofessional.
- Create visual variety through BACKGROUND COLORS only: rotate white → lavender → off-white → whisper gradient
- NEVER repeat the same blueprint consecutively
- No 3+ consecutive slides from the same background family
- Match zone layout to content type (grid for icon_grid, 60_40 for two_column, etc.)

Return ONLY valid JSON array (no markdown fences):
[
  {{"slide_id": "...", "blueprint_id": "...", "accent_override": null, "title_alignment": "left"}},
  ...
]

Array MUST have exactly {slide_count} entries, one per slide in the manifest."""


def _extract_json_array(text: str) -> str:
    """Pull the JSON array out of an LLM response that may include a code
    fence and/or a preamble sentence before it (e.g. "Looking at this deck,
    I'll standardize on...") — naive `startswith("\`\`\`")` stripping misses
    the preamble case, so fall back to slicing between the first "[" and
    the last "]" when no fence is found at the very start."""
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        return "\n".join(lines)
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def design_slides(plan: dict, theme: DesignTheme, provider: str = "claude",
                  reuse_master_slides: bool = False) -> list[SlideDesignSpec]:
    """Select blueprints for all slides, with a same-provider retry, a
    cross-provider retry, and a rule-based fallback if both LLM attempts fail."""
    manifest = build_slide_manifest(plan, reuse_master_slides=reuse_master_slides)

    other_provider = "gemini" if provider == "claude" else "claude"
    for attempt_provider in (provider, other_provider):
        try:
            specs = _llm_design(manifest, theme, attempt_provider)
            if len(specs) == len(manifest):
                specs = enforce_variety(specs, manifest)
                return specs
            print(f"[SlideDesigner] {attempt_provider}: count mismatch "
                  f"({len(specs)} vs {len(manifest)})")
        except Exception as e:
            print(f"[SlideDesigner] {attempt_provider} failed ({e})")

    print("[SlideDesigner] Both providers failed, using rule-based fallback")
    return _rule_based_design(manifest, theme)


def _llm_design(manifest: list[dict], theme: DesignTheme, provider: str = "claude") -> list[SlideDesignSpec]:
    """Call the LLM to select blueprints."""
    if provider == "gemini":
        from llm.gemini_client import generate_text
    else:
        from llm.anthropic_client import generate_text

    manifest_text = "\n".join(
        f"  {i+1}. [{s['type']}] \"{s['title']}\" (id: {s['id']})"
        for i, s in enumerate(manifest)
    )

    bp_text = "\n".join(
        f"  - {bp.id}: bg={bp.background}, zone={bp.content_zone}, "
        f"mood={bp.mood}, suitable_for={bp.suitable_for}"
        for bp in BLUEPRINT_REGISTRY.values()
    )

    prompt = DESIGNER_PROMPT.format(
        theme_name=theme.theme_name,
        primary_accent=theme.primary_accent,
        secondary_accent=theme.secondary_accent,
        slide_manifest=manifest_text,
        blueprint_list=bp_text,
        slide_count=len(manifest),
    )

    # ~8000 tokens covers a typical ~25-slide deck's JSON array comfortably;
    # scale up for larger decks so the response doesn't truncate mid-array
    # (empty/truncated JSON is the #1 cause of falling back to rule-based
    # design on big proposals).
    max_tokens = max(8000, len(manifest) * 220)
    text = generate_text(prompt, max_tokens=max_tokens).strip()
    text = _extract_json_array(text)

    data = json.loads(text)
    specs = []
    for item in data:
        bp_id = item.get("blueprint_id", "white_full_accent_line")
        if bp_id not in BLUEPRINT_REGISTRY:
            bp_id = "white_full_accent_line"
        specs.append(SlideDesignSpec(
            slide_id=item.get("slide_id", ""),
            slide_type="",
            blueprint_id=bp_id,
            accent_override=item.get("accent_override"),
            card_style_override=item.get("card_style_override"),
            title_alignment=item.get("title_alignment", "left"),
        ))

    for i, s in enumerate(specs):
        if i < len(manifest):
            s.slide_type = manifest[i]["type"]
            s.slide_id = manifest[i]["id"]

    return specs


# ── Rule-based fallback ─────────────────────────────────────────

# One accent style per deck, backgrounds rotate for variety.
# Each accent family uses the SAME accent position across all background colors.
_ACCENT_FAMILIES = {
    "topbar": [
        "white_full_topbar", "lavender_full_topbar", "offwhite_full_topbar",
        "whisper_full_topbar",
    ],
    "sidebar": [
        "white_full_sidebar", "white_full_sidebar_gradient", "coolgray_full_sidebar",
        "lavender_thirds_sidebar", "white_full_sidebar",
    ],
    "accent_line": [
        "white_full_accent_line", "lavender_full_accent_line", "white_60_40_accent_line",
        "white_full_accent_line", "lavender_full_accent_line",
    ],
}

_DEFAULT_ACCENT_FAMILY = "topbar"


def _rule_based_design(manifest: list[dict], theme: DesignTheme) -> list[SlideDesignSpec]:
    """Randomized fallback when Claude is unavailable."""
    import random

    family_keys = list(_ACCENT_FAMILIES.keys())
    accent_family = random.choice(family_keys)
    rotation = list(_ACCENT_FAMILIES[accent_family])
    random.shuffle(rotation)

    specs = []
    content_idx = 0

    for m in manifest:
        slide_type = m["type"]

        if slide_type in ("cover", "closing"):
            bp_id = "dark_center_gradient"
        elif slide_type == "toc":
            bp_id = rotation[0]
        else:
            bp_id = rotation[content_idx % len(rotation)]
            content_idx += 1

        accent = theme.accent_cycle[content_idx % len(theme.accent_cycle)] if theme.accent_cycle else theme.primary_accent

        specs.append(SlideDesignSpec(
            slide_id=m["id"],
            slide_type=slide_type,
            blueprint_id=bp_id,
            accent_override=accent,
        ))

    return enforce_variety(specs, manifest)
