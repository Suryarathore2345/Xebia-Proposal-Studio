"""Claude-driven design engine for visually diverse, brand-aligned slides.

Three-layer system:
  Layer 1: DesignTheme — proposal-level visual strategy (Claude, once per deck)
  Layer 2: SlideBlueprint — 30+ curated bg + zone + accent combinations (Python)
  Layer 3: Per-slide design spec — Claude selects + parameterizes blueprints
"""

from generation.design_engine.palette import (
    PURPLE, NEUTRALS, GRADIENTS, PURPLE_SPECTRUM, ALL_APPROVED_BACKGROUNDS,
)
from generation.design_engine.blueprints import (
    SlideBlueprint, BLUEPRINT_REGISTRY, get_blueprint,
)
from generation.design_engine.theme_generator import DesignTheme, generate_theme
from generation.design_engine.variety_engine import enforce_variety

__all__ = [
    "PURPLE", "NEUTRALS", "GRADIENTS", "PURPLE_SPECTRUM",
    "ALL_APPROVED_BACKGROUNDS",
    "SlideBlueprint", "BLUEPRINT_REGISTRY", "get_blueprint",
    "DesignTheme", "generate_theme",
    "enforce_variety",
]
