"""AI-driven design system generator — unique visual identity per proposal.

Uses Gemini to analyze proposal content, industry, and brand constraints
to generate a fresh color palette, typography, and per-slide visual
decisions for every proposal. No two decks look the same.

Architecture:
  Proposal Plan → Gemini analyzes context → DesignSystem generated
  → Python validates variety rules → SlideStyle resolved per slide
  → Builders render with dynamic colors/fonts/accents
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from google import genai
from google.genai import types


# ── Gemini client (shared with gemini_client.py) ──────────────

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    _client = genai.Client(api_key=api_key)
    return _client


# ── Data structures ───────────────────────────────────────────

@dataclass
class DesignPalette:
    primary: str
    secondary: str
    accent1: str
    accent2: str
    accent3: str
    bg_light: str
    bg_dark: str
    bg_warm: str
    bg_card: str
    text_dark: str
    text_medium: str
    text_light: str


@dataclass
class SlideVisual:
    slide_id: str
    composition: str        # bold_header | dark_full | clean | top_bar | left_bar | bottom_band | none
    accent_color: str       # hex from palette


@dataclass
class ProposalDesignSystem:
    palette: DesignPalette
    heading_font: str
    body_font: str
    card_style: str         # accent_top | rounded_shadow | flat_bordered | outlined | minimal
    slide_visuals: list[SlideVisual] = field(default_factory=list)
    rationale: str = ""

    def get_slide_visual(self, idx: int) -> SlideVisual:
        if idx < len(self.slide_visuals):
            return self.slide_visuals[idx]
        return self.slide_visuals[idx % max(1, len(self.slide_visuals))]

    def accent_cycle(self) -> list[str]:
        return [
            self.palette.primary, self.palette.accent1,
            self.palette.secondary, self.palette.accent2,
            self.palette.accent3,
        ]


@dataclass
class SlideStyle:
    """Resolved visual style for rendering one slide."""
    heading_font: str
    body_font: str
    composition: str
    accent_color: str
    card_style: str
    title_color: str
    body_color: str
    card_bg: str
    border_color: str
    palette: DesignPalette
    blueprint_id: str = ""
    design_theme: object = None

    @staticmethod
    def from_design_system(ds: ProposalDesignSystem, slide_idx: int) -> "SlideStyle":
        sv = ds.get_slide_visual(slide_idx)
        return SlideStyle(
            heading_font=ds.heading_font,
            body_font=ds.body_font,
            composition=sv.composition,
            accent_color=sv.accent_color,
            card_style=ds.card_style,
            title_color=ds.palette.text_dark,
            body_color=ds.palette.text_medium,
            card_bg=ds.palette.bg_card,
            border_color="#EAEAEA",
            palette=ds.palette,
        )

    @staticmethod
    def dark_style(ds: ProposalDesignSystem) -> "SlideStyle":
        """Style for dark-background slides (covers, dividers, closing)."""
        return SlideStyle(
            heading_font=ds.heading_font,
            body_font=ds.body_font,
            composition="none",
            accent_color=ds.palette.primary,
            card_style=ds.card_style,
            title_color=ds.palette.text_light,
            body_color="#E0E0E0",
            card_bg="#2A2A2A",
            border_color="#404040",
            palette=ds.palette,
        )


# ── Helpers ───────────────────────────────────────────────────

def _lighten(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


# ── Slide manifest builder ───────────────────────────────────

def _build_slide_manifest(plan: dict) -> list[dict]:
    """Enumerate every slide that will be generated, in order."""
    slides = []
    storyline = plan.get("storyline", [])
    sections = plan.get("sections", {})

    for section_key in storyline:
        section = sections.get(section_key, {})
        title = section.get("title", section_key.replace("_", " ").title())

        if section_key == "cover":
            slides.append({"id": "cover", "type": "cover", "title": title})
        elif section_key == "table_of_contents":
            slides.append({"id": "toc", "type": "toc", "title": "Table of Contents"})
        elif section_key == "closing":
            slides.append({"id": "closing", "type": "closing", "title": title})
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


# ── Gemini design system prompt ───────────────────────────────

DESIGN_SYSTEM_PROMPT = """\
You are a senior presentation designer creating a VISUALLY DIVERSE deck.
Each slide must feel like a distinct design — not a repetitive template.

PROPOSAL CONTEXT:
- Title: {title}
- Customer: {customer}
- Industry: {industry}
- Total slides: {slide_count}

SLIDE MANIFEST (in order):
{slide_manifest}

COMPOSITION MODES — these create fundamentally different slide layouts:
- "bold_header": Wide colored banner fills the top 1.85in of slide. Title appears
  as white text ON the colored banner. Content sits below on white. Very dramatic.
- "dark_full": Entire slide gets a dark background. All text becomes white/light.
  Cards and shapes get dark fills. Creates editorial-magazine feel.
- "clean": Standard white slide with thin accent line under title.
- "top_bar": Thin colored bar at very top (0.4in). Title and content below normally.
- "left_bar": Vertical colored bar on left edge (0.18in). Subtle structural accent.
- "bottom_band": Colored band at bottom of slide (0.35in). Grounds the layout.
- "none": No decorative element (use for cover, dividers, closing — template handles).

RULES:
- Xebia brand purple #6C1D5F MUST be in the palette
- Use at least 4 DIFFERENT composition types across the deck
- bold_header should be used for 3-5 content slides (it's the most impactful)
- dark_full should be used for 2-3 content slides (powerful but don't overuse)
- Mix clean, top_bar, left_bar, bottom_band for remaining content slides
- NEVER use the same composition 3+ times in a row
- Cover, section_divider, toc, closing slides MUST use "none"
- Rotate accent_color through palette colors — avoid same color 3+ times in a row
- Create a visual RHYTHM: alternate between dramatic and calm compositions

AVAILABLE FONTS (pick a heading/body pair):
Poppins, Arial, Calibri, Century Gothic, Segoe UI, Trebuchet MS

CARD STYLES: accent_top, rounded_shadow, flat_bordered, outlined, minimal

Return ONLY valid JSON (no markdown fences):
{{
  "palette": {{
    "primary": "#hex (must include #6C1D5F somewhere in palette)",
    "secondary": "#hex",
    "accent1": "#hex",
    "accent2": "#hex",
    "accent3": "#hex",
    "bg_light": "#hex (white or near-white)",
    "bg_dark": "#hex (near-black or deep brand color)",
    "bg_warm": "#hex (warm neutral for variety)",
    "bg_card": "#hex (subtle card background)",
    "text_dark": "#hex (near-black for headings)",
    "text_medium": "#hex (medium gray for body)",
    "text_light": "#FFFFFF"
  }},
  "typography": {{
    "heading_font": "font name",
    "body_font": "font name"
  }},
  "card_style": "one of: accent_top, rounded_shadow, flat_bordered, outlined, minimal",
  "slides": [
    {{
      "composition": "bold_header | dark_full | clean | top_bar | left_bar | bottom_band | none",
      "accent_color": "#hex from palette"
    }}
  ],
  "rationale": "2 sentences explaining design choices"
}}

The "slides" array MUST have exactly {slide_count} entries, one per slide in the manifest."""


def generate_design_system(plan: dict) -> ProposalDesignSystem:
    """Generate a unique per-proposal design system using Gemini."""
    manifest = _build_slide_manifest(plan)

    manifest_text = "\n".join(
        f"  {i+1}. [{s['type']}] \"{s['title']}\""
        for i, s in enumerate(manifest)
    )

    prompt = DESIGN_SYSTEM_PROMPT.format(
        title=plan.get("title", "Proposal"),
        customer=plan.get("customer", "Client"),
        industry=plan.get("industry", "technology"),
        slide_count=len(manifest),
        slide_manifest=manifest_text,
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=4000,
            ),
        )
        ds = _parse_design_response(response.text, manifest)
        ds = _validate_and_fix(ds)
        return ds
    except Exception as e:
        print(f"[DesignGenerator] Gemini call failed ({e}), using fallback")
        return _default_design_system(plan)


def _parse_design_response(text: str, manifest: list[dict]) -> ProposalDesignSystem:
    """Parse Gemini JSON output into a ProposalDesignSystem."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    pal_data = data.get("palette", {})
    palette = DesignPalette(
        primary=pal_data.get("primary", "#6C1D5F"),
        secondary=pal_data.get("secondary", "#002060"),
        accent1=pal_data.get("accent1", "#00A19A"),
        accent2=pal_data.get("accent2", "#DD6B20"),
        accent3=pal_data.get("accent3", "#00B050"),
        bg_light=pal_data.get("bg_light", "#FFFFFF"),
        bg_dark=pal_data.get("bg_dark", "#1A1A1A"),
        bg_warm=pal_data.get("bg_warm", "#F8F6F3"),
        bg_card=pal_data.get("bg_card", "#F7F8FC"),
        text_dark=pal_data.get("text_dark", "#222222"),
        text_medium=pal_data.get("text_medium", "#595959"),
        text_light=pal_data.get("text_light", "#FFFFFF"),
    )

    typo = data.get("typography", {})
    heading_font = typo.get("heading_font", "Poppins")
    body_font = typo.get("body_font", "Arial")

    card_style = data.get("card_style", "accent_top")
    valid_cards = {"accent_top", "rounded_shadow", "flat_bordered", "outlined", "minimal"}
    if card_style not in valid_cards:
        card_style = "accent_top"

    slide_data = data.get("slides", [])
    valid_compositions = {
        "bold_header", "dark_full", "clean", "top_bar",
        "left_bar", "bottom_band", "none",
    }
    accents = [palette.primary, palette.accent1, palette.secondary,
               palette.accent2, palette.accent3]
    fallback_cycle = ["bold_header", "none", "clean", "dark_full", "top_bar",
                      "none", "left_bar", "none", "bottom_band", "none"]

    visuals = []
    for i, m in enumerate(manifest):
        if i < len(slide_data):
            sd = slide_data[i]
            comp = sd.get("composition", sd.get("accent_treatment", "clean"))
            if comp not in valid_compositions:
                comp = "clean"
            color = sd.get("accent_color", accents[i % len(accents)])
        else:
            comp = fallback_cycle[i % len(fallback_cycle)]
            color = accents[i % len(accents)]

        visuals.append(SlideVisual(
            slide_id=m["id"],
            composition=comp,
            accent_color=color,
        ))

    return ProposalDesignSystem(
        palette=palette,
        heading_font=heading_font,
        body_font=body_font,
        card_style=card_style,
        slide_visuals=visuals,
        rationale=data.get("rationale", ""),
    )


def _validate_and_fix(ds: ProposalDesignSystem) -> ProposalDesignSystem:
    """Enforce variety rules — fix repetition without a second Gemini call."""
    visuals = ds.slide_visuals
    if len(visuals) < 3:
        return ds

    accents = ds.accent_cycle()
    compositions = ["bold_header", "dark_full", "clean", "top_bar", "left_bar", "bottom_band"]

    # Fix 3+ consecutive same composition
    for i in range(2, len(visuals)):
        if (visuals[i].composition == visuals[i-1].composition
                == visuals[i-2].composition
                and visuals[i].composition != "none"):
            alt = [c for c in compositions if c != visuals[i].composition]
            visuals[i].composition = alt[i % len(alt)]

    # Fix 3+ consecutive same accent_color
    for i in range(2, len(visuals)):
        if (visuals[i].accent_color == visuals[i-1].accent_color
                == visuals[i-2].accent_color):
            alt = [c for c in accents if c != visuals[i].accent_color]
            visuals[i].accent_color = alt[i % len(alt)] if alt else accents[0]

    # Ensure at least 4 different composition types across deck
    used = {v.composition for v in visuals}
    if len(used) < 4:
        needed = [c for c in compositions if c not in used]
        content_indices = [i for i, v in enumerate(visuals)
                          if v.composition != "none"]
        for j, c in enumerate(needed):
            if j < len(content_indices):
                idx = content_indices[-(j + 1)]
                visuals[idx].composition = c

    # Ensure bold_header and dark_full are used at least once
    has_bold = any(v.composition == "bold_header" for v in visuals)
    has_dark = any(v.composition == "dark_full" for v in visuals)
    content_vis = [i for i, v in enumerate(visuals) if v.composition not in ("none",)]
    if not has_bold and len(content_vis) >= 3:
        visuals[content_vis[1]].composition = "bold_header"
    if not has_dark and len(content_vis) >= 5:
        visuals[content_vis[3]].composition = "dark_full"

    # Ensure Xebia purple appears in palette
    purple = "#6C1D5F"
    pal = ds.palette
    all_colors = [pal.primary, pal.secondary, pal.accent1, pal.accent2, pal.accent3]
    if purple.upper() not in [c.upper() for c in all_colors]:
        ds.palette.primary = purple

    return ds


# ── Fallback design systems ──────────────────────────────────

INDUSTRY_PALETTES = {
    "technology": DesignPalette(
        primary="#6C1D5F", secondary="#2563EB",
        accent1="#06B6D4", accent2="#8B5CF6", accent3="#EC4899",
        bg_light="#FFFFFF", bg_dark="#0F172A", bg_warm="#F8FAFC",
        bg_card="#F1F5F9", text_dark="#1E293B", text_medium="#64748B",
        text_light="#FFFFFF",
    ),
    "finance": DesignPalette(
        primary="#6C1D5F", secondary="#1E3A5F",
        accent1="#C8A951", accent2="#2D6A4F", accent3="#4A7C59",
        bg_light="#FFFFFF", bg_dark="#1A2332", bg_warm="#FAF8F5",
        bg_card="#F5F3EF", text_dark="#1A2332", text_medium="#5A6577",
        text_light="#FFFFFF",
    ),
    "healthcare": DesignPalette(
        primary="#0D9488", secondary="#6C1D5F",
        accent1="#059669", accent2="#0284C7", accent3="#7C3AED",
        bg_light="#FFFFFF", bg_dark="#134E4A", bg_warm="#F0FDFA",
        bg_card="#F0FDF4", text_dark="#1A2332", text_medium="#64748B",
        text_light="#FFFFFF",
    ),
    "retail": DesignPalette(
        primary="#6C1D5F", secondary="#EA580C",
        accent1="#D97706", accent2="#0D9488", accent3="#2563EB",
        bg_light="#FFFFFF", bg_dark="#1C1917", bg_warm="#FEF7ED",
        bg_card="#FFF7ED", text_dark="#1C1917", text_medium="#78716C",
        text_light="#FFFFFF",
    ),
    "manufacturing": DesignPalette(
        primary="#6C1D5F", secondary="#475569",
        accent1="#0369A1", accent2="#D97706", accent3="#059669",
        bg_light="#FFFFFF", bg_dark="#1E293B", bg_warm="#F8FAFC",
        bg_card="#F1F5F9", text_dark="#0F172A", text_medium="#64748B",
        text_light="#FFFFFF",
    ),
    "energy": DesignPalette(
        primary="#065F46", secondary="#6C1D5F",
        accent1="#D97706", accent2="#0369A1", accent3="#7C3AED",
        bg_light="#FFFFFF", bg_dark="#022C22", bg_warm="#F0FDF4",
        bg_card="#ECFDF5", text_dark="#022C22", text_medium="#4B5563",
        text_light="#FFFFFF",
    ),
    "telecom": DesignPalette(
        primary="#6C1D5F", secondary="#3B82F6",
        accent1="#22C55E", accent2="#F59E0B", accent3="#EC4899",
        bg_light="#FFFFFF", bg_dark="#0F172A", bg_warm="#EFF6FF",
        bg_card="#F0F9FF", text_dark="#0F172A", text_medium="#6B7280",
        text_light="#FFFFFF",
    ),
}


def _default_design_system(plan: dict) -> ProposalDesignSystem:
    """Industry-aware fallback when Gemini is unavailable."""
    industry = plan.get("industry", "technology").lower()
    palette = INDUSTRY_PALETTES.get(industry, INDUSTRY_PALETTES["technology"])

    manifest = _build_slide_manifest(plan)
    content_compositions = [
        "bold_header", "clean", "dark_full", "top_bar",
        "bold_header", "left_bar", "clean", "bottom_band",
        "bold_header", "dark_full", "clean", "top_bar",
    ]
    accents = [palette.primary, palette.accent1, palette.secondary,
               palette.accent2, palette.accent3]

    content_idx = 0
    visuals = []
    for i, m in enumerate(manifest):
        if m["type"] in ("cover", "closing", "section_divider", "toc"):
            comp = "none"
        else:
            comp = content_compositions[content_idx % len(content_compositions)]
            content_idx += 1
        visuals.append(SlideVisual(
            slide_id=m["id"],
            composition=comp,
            accent_color=accents[i % len(accents)],
        ))

    return ProposalDesignSystem(
        palette=palette,
        heading_font="Poppins",
        body_font="Arial",
        card_style="accent_top",
        slide_visuals=visuals,
        rationale=f"Fallback design for {industry} industry",
    )
