"""Xebia brand color palette — purple spectrum + neutrals only.

Purple is an ACCENT, never a full-slide background.
Full-slide backgrounds use white, off-white, lavender, or dark neutrals.
Purple appears in thin bars, gradient shapes, corner elements, card accents.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorDef:
    hex: str
    name: str
    role: str


# ── Purple Spectrum (light → dark) ──────────────────────────────

class PURPLE:
    BG        = "#F5EFF5"   # near-white lavender (slide bg alternative)
    MIST      = "#EDE4ED"   # very light (card fills)
    SOFT      = "#D4A5D4"   # light accent, borders
    MUTED     = "#B75EB7"   # medium accent, decorative shapes
    MID       = "#9B3F9B"   # cards, badges, icon backgrounds
    LIGHT     = "#7A2A7B"   # strong accent, bars, stripes
    BRAND     = "#6C1D5F"   # brand primary — accent elements, text highlights
    DEEP      = "#5A1750"   # premium accent, gradients
    DARK      = "#4A0D4B"   # dark backgrounds, gradient endpoints
    DEEPEST   = "#3A0838"   # darkest variant for contrast

PURPLE_SPECTRUM = [
    PURPLE.BG, PURPLE.MIST, PURPLE.SOFT, PURPLE.MUTED, PURPLE.MID,
    PURPLE.LIGHT, PURPLE.BRAND, PURPLE.DEEP, PURPLE.DARK, PURPLE.DEEPEST,
]


# ── Neutrals ────────────────────────────────────────────────────

class NEUTRALS:
    WHITE          = "#FFFFFF"
    OFF_WHITE      = "#F7F8FC"
    COOL_GRAY      = "#F0F0F5"   # card fills, zones
    LIGHT_GRAY     = "#EAEAEA"   # borders, dividers
    MID_GRAY       = "#9E9E9E"   # muted text, captions
    DARK_GRAY      = "#595959"   # body text
    CHARCOAL       = "#333333"   # headings on light
    NEAR_BLACK     = "#222222"   # strong headings
    BLACK          = "#1A1A1A"   # dark slide backgrounds


# ── Approved Backgrounds ────────────────────────────────────────

ALL_APPROVED_BACKGROUNDS = [
    NEUTRALS.WHITE,
    NEUTRALS.OFF_WHITE,
    NEUTRALS.COOL_GRAY,
    PURPLE.BG,        # lavender
    NEUTRALS.BLACK,    # dark
    NEUTRALS.NEAR_BLACK,
]


# ── Gradient Definitions ────────────────────────────────────────

@dataclass(frozen=True)
class GradientDef:
    color1: str
    color2: str
    name: str
    mood: str   # "dark", "medium", "light", "whisper"


class GRADIENTS:
    BRAND_DARK     = GradientDef(PURPLE.BRAND, PURPLE.DARK, "brand_dark", "dark")
    PURPLE_TO_BLACK = GradientDef(PURPLE.BRAND, NEUTRALS.BLACK, "purple_to_black", "dark")
    MEDIUM         = GradientDef(PURPLE.LIGHT, PURPLE.BRAND, "medium", "medium")
    SOFT           = GradientDef(PURPLE.MUTED, PURPLE.LIGHT, "soft", "medium")
    PASTEL         = GradientDef(PURPLE.SOFT, PURPLE.BG, "pastel", "light")
    WHISPER        = GradientDef(PURPLE.BG, NEUTRALS.WHITE, "whisper", "whisper")

    ALL = [BRAND_DARK, PURPLE_TO_BLACK, MEDIUM, SOFT, PASTEL, WHISPER]
    DARK = [BRAND_DARK, PURPLE_TO_BLACK]
    LIGHT = [PASTEL, WHISPER]


# ── Accent Color Cycles ────────────────────────────────────────

ACCENT_CYCLE_DEEP = [
    PURPLE.BRAND, PURPLE.DEEP, PURPLE.DARK, PURPLE.LIGHT, PURPLE.MID,
]

ACCENT_CYCLE_SOFT = [
    PURPLE.LIGHT, PURPLE.MUTED, PURPLE.SOFT, PURPLE.BRAND, PURPLE.MID,
]

ACCENT_CYCLE_MIXED = [
    PURPLE.BRAND, PURPLE.MUTED, PURPLE.DEEP, PURPLE.LIGHT, PURPLE.SOFT,
]


# ── Card Colors ─────────────────────────────────────────────────

CARD_FILL_LIGHT   = PURPLE.BG
CARD_FILL_MIST    = PURPLE.MIST
CARD_FILL_NEUTRAL = NEUTRALS.OFF_WHITE
CARD_FILL_DARK    = "#2A2A3A"

CARD_BORDER_LIGHT = PURPLE.SOFT
CARD_BORDER_NEUTRAL = NEUTRALS.LIGHT_GRAY
CARD_BORDER_DARK  = "#3F3F50"


# ── Text Colors ─────────────────────────────────────────────────

TEXT_HEADING_LIGHT = NEUTRALS.NEAR_BLACK
TEXT_HEADING_DARK  = NEUTRALS.WHITE
TEXT_BODY_LIGHT    = NEUTRALS.DARK_GRAY
TEXT_BODY_DARK     = "#D4D4D8"
TEXT_MUTED_LIGHT   = NEUTRALS.MID_GRAY
TEXT_MUTED_DARK    = "#9E9EAE"
TEXT_ACCENT        = PURPLE.BRAND


# ── Helpers ─────────────────────────────────────────────────────

def lighten(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


def darken(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02X}{g:02X}{b:02X}"
