"""Design theme generator — proposal-level visual strategy via Gemini.

Generates a DesignTheme once per deck that controls which purple shades
to emphasize, background distribution, typography, and card styling.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from generation.design_engine.palette import (
    PURPLE, NEUTRALS, GRADIENTS, GradientDef,
    ACCENT_CYCLE_DEEP, ACCENT_CYCLE_SOFT, ACCENT_CYCLE_MIXED,
)


@dataclass
class DesignTheme:
    """Proposal-level visual strategy controlling all design decisions."""
    theme_name: str = "Default"
    primary_accent: str = PURPLE.BRAND
    secondary_accent: str = PURPLE.MUTED
    gradient_pair: GradientDef = field(default_factory=lambda: GRADIENTS.BRAND_DARK)
    card_accent: str = PURPLE.LIGHT
    card_fill: str = PURPLE.BG
    card_border: str = PURPLE.SOFT
    heading_font: str = "Century Gothic"
    body_font: str = "Arial"
    card_style: str = "accent_top"
    accent_cycle: list[str] = field(default_factory=lambda: list(ACCENT_CYCLE_MIXED))
    rationale: str = ""

    @property
    def text_heading_light(self) -> str:
        return NEUTRALS.NEAR_BLACK

    @property
    def text_heading_dark(self) -> str:
        return NEUTRALS.WHITE

    @property
    def text_body_light(self) -> str:
        return NEUTRALS.DARK_GRAY

    @property
    def text_body_dark(self) -> str:
        return "#D4D4D8"

    @property
    def text_accent(self) -> str:
        return self.primary_accent


# ── Gemini client ───────────────────────────────────────────────

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai
    _client = genai.Client(api_key=api_key)
    return _client


# ── Theme generation prompt ─────────────────────────────────────

THEME_PROMPT = """\
You are a senior presentation designer for Xebia. Design a visual theme
using ONLY the Xebia purple spectrum and neutral colors.

PROPOSAL CONTEXT:
- Title: {title}
- Customer: {customer}
- Industry: {industry}
- Total slides: {slide_count}

APPROVED PURPLE SHADES (light → dark):
  #F5EFF5 (lavender bg)
  #EDE4ED (mist, card fills)
  #D4A5D4 (soft accent, borders)
  #B75EB7 (medium accent, shapes)
  #9B3F9B (mid, badges)
  #7A2A7B (strong accent, bars)
  #6C1D5F (brand primary — MUST appear)
  #5A1750 (deep premium)
  #4A0D4B (dark, gradients)
  #3A0838 (deepest)

APPROVED NEUTRALS:
  #FFFFFF (white — dominant background)
  #F7F8FC (off-white)
  #F0F0F5 (cool gray)
  #EAEAEA (borders)
  #9E9E9E (muted text)
  #595959 (body text)
  #333333 (charcoal headings)
  #222222 (near-black headings)
  #1A1A1A (dark slide background)

RULES:
- Purple is an ACCENT, never a full-slide background
- Backgrounds use white, off-white, lavender, or dark (#1A1A1A)
- NO other colors (no teal, blue, green, orange, red, gold)
- Pick which purple shades to emphasize for THIS proposal's personality
- Finance/banking → deeper purples (#4A0D4B, #5A1750) for gravity
- Technology → brighter purples (#B75EB7, #7A2A7B) for energy
- Healthcare/consulting → softer purples (#D4A5D4, #B75EB7) for approachability

AVAILABLE FONTS (heading/body pairs):
  Century Gothic + Arial (modern, geometric)
  Calibri + Arial (clean corporate)
  Trebuchet MS + Arial (friendly)
  Segoe UI + Arial (Microsoft-aligned)
  Arial + Arial (safe default)

CARD STYLES: accent_top, rounded_shadow, flat_bordered, outlined, minimal

Return ONLY valid JSON (no markdown fences):
{{
  "theme_name": "2-3 word name for this theme's personality",
  "primary_accent": "#hex (the main purple for bars, lines, accents)",
  "secondary_accent": "#hex (a different purple shade for variety)",
  "gradient_pair": ["#hex lighter", "#hex darker"],
  "card_accent": "#hex (purple shade for card top accents)",
  "card_fill": "#hex (very light purple or off-white for card bg)",
  "card_border": "#hex (light purple or gray for card borders)",
  "heading_font": "font name",
  "body_font": "font name",
  "card_style": "one of the card styles above",
  "accent_cycle": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
  "rationale": "1-2 sentences explaining the visual strategy"
}}

accent_cycle is 5 purple shades to rotate through for visual variety.
All hex values MUST come from the approved lists above."""


def generate_theme(plan: dict) -> DesignTheme:
    """Generate a unique design theme for this proposal via Gemini."""
    title = plan.get("title", "Proposal")
    customer = plan.get("customer", "Client")
    industry = plan.get("industry", "technology")
    storyline = plan.get("storyline", [])
    sections = plan.get("sections", {})
    slide_count = sum(
        1 + len(sections.get(s, {}).get("slides", []))
        for s in storyline
    )

    prompt = THEME_PROMPT.format(
        title=title, customer=customer,
        industry=industry, slide_count=slide_count,
    )

    try:
        client = _get_client()
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2000,
            ),
        )
        return _parse_theme(response.text)
    except Exception as e:
        print(f"[ThemeGenerator] Gemini failed ({e}), using fallback")
        return _fallback_theme(industry)


def _parse_theme(text: str) -> DesignTheme:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    gp = data.get("gradient_pair", [PURPLE.BRAND, PURPLE.DARK])
    gradient = GradientDef(gp[0], gp[1], "custom", "dark")

    valid_cards = {"accent_top", "rounded_shadow", "flat_bordered", "outlined", "minimal"}
    card_style = data.get("card_style", "accent_top")
    if card_style not in valid_cards:
        card_style = "accent_top"

    valid_fonts = {"Century Gothic", "Calibri", "Trebuchet MS", "Segoe UI", "Arial", "Poppins"}
    heading = data.get("heading_font", "Century Gothic")
    body = data.get("body_font", "Arial")
    if heading not in valid_fonts:
        heading = "Century Gothic"
    if body not in valid_fonts:
        body = "Arial"

    cycle = data.get("accent_cycle", list(ACCENT_CYCLE_MIXED))
    if len(cycle) < 3:
        cycle = list(ACCENT_CYCLE_MIXED)

    return DesignTheme(
        theme_name=data.get("theme_name", "Custom"),
        primary_accent=data.get("primary_accent", PURPLE.BRAND),
        secondary_accent=data.get("secondary_accent", PURPLE.MUTED),
        gradient_pair=gradient,
        card_accent=data.get("card_accent", PURPLE.LIGHT),
        card_fill=data.get("card_fill", PURPLE.BG),
        card_border=data.get("card_border", PURPLE.SOFT),
        heading_font=heading,
        body_font=body,
        card_style=card_style,
        accent_cycle=cycle,
        rationale=data.get("rationale", ""),
    )


# ── Fallback themes ─────────────────────────────────────────────

def _fallback_theme(industry: str) -> DesignTheme:
    if industry in ("finance", "banking", "insurance"):
        return DesignTheme(
            theme_name="Deep Authority",
            primary_accent=PURPLE.BRAND,
            secondary_accent=PURPLE.DEEP,
            gradient_pair=GRADIENTS.BRAND_DARK,
            card_accent=PURPLE.DARK,
            card_fill=PURPLE.BG,
            card_border=PURPLE.SOFT,
            heading_font="Century Gothic",
            body_font="Arial",
            card_style="flat_bordered",
            accent_cycle=list(ACCENT_CYCLE_DEEP),
        )
    elif industry in ("healthcare", "pharma", "consulting"):
        return DesignTheme(
            theme_name="Soft Clarity",
            primary_accent=PURPLE.LIGHT,
            secondary_accent=PURPLE.MUTED,
            gradient_pair=GRADIENTS.SOFT,
            card_accent=PURPLE.MID,
            card_fill=PURPLE.MIST,
            card_border=PURPLE.SOFT,
            heading_font="Calibri",
            body_font="Arial",
            card_style="rounded_shadow",
            accent_cycle=list(ACCENT_CYCLE_SOFT),
        )
    else:
        return DesignTheme(
            theme_name="Balanced Precision",
            primary_accent=PURPLE.BRAND,
            secondary_accent=PURPLE.MUTED,
            gradient_pair=GRADIENTS.MEDIUM,
            card_accent=PURPLE.LIGHT,
            card_fill=PURPLE.BG,
            card_border=PURPLE.SOFT,
            heading_font="Century Gothic",
            body_font="Arial",
            card_style="accent_top",
            accent_cycle=list(ACCENT_CYCLE_MIXED),
        )
