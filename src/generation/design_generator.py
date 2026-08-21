"""Shared design data structures used by the PPTX generation pipeline.

The actual AI-driven design decisions (theme + per-slide blueprint
selection) live in `generation/design_engine/theme_generator.py` and
`generation/design_engine/slide_designer.py`. This module only holds the
palette/style dataclasses those modules and `pptx_generator.py` pass
around.
"""

from dataclasses import dataclass, field


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
    """Legacy per-proposal design container, kept as a plain data holder.

    create_presentation() accepts one for its type signature but doesn't
    read its fields — actual theme/blueprint decisions now live in
    generation/design_engine/ (theme_generator.py, slide_designer.py).
    """
    palette: DesignPalette
    heading_font: str
    body_font: str
    card_style: str         # accent_top | rounded_shadow | flat_bordered | outlined | minimal
    slide_visuals: list[SlideVisual] = field(default_factory=list)
    rationale: str = ""


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
