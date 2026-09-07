"""Post-render geometry validation for generated slides.

The visual-QA audit in docs/operations/deck-visual-layout-qa-plan.md found
label overflow and off-slide content by hand, once, on one generated deck.
This runs the same class of check automatically on every generation, using
real font metrics where available (PIL + the actual font file) instead of
the character-count estimate that caused several of the bugs that audit
found in the first place — a wrong estimate sizes the box wrong regardless
of how carefully the rest of the layout math is done.

This is deliberately narrow: two checks with a low false-positive rate
(text overflowing its own box, content bleeding off the slide edge), not
general shape-overlap detection. The audit's own methodology notes that a
naive overlap scan is very noisy — this design's zones/groups/items are
nested boxes with text legitimately drawn on top of colored backgrounds
throughout, so "shape A's bounding box intersects shape B's" is true
constantly by design and not a signal of anything wrong.
"""

from __future__ import annotations

import math
from pathlib import Path

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
_EDGE_TOLERANCE_IN = 0.05  # ignore sub-hairline rounding, not real overflow
_TEXT_BOX_MARGIN_IN = 0.05  # approx internal L/R margin python-pptx textboxes use
_LINE_HEIGHT_FACTOR = 1.22  # standard single-spaced line-height multiple of font size

_WINDOWS_FONTS_DIR = Path(r"C:\Windows\Fonts")
# Render/most Linux containers don't ship Arial/Calibri/Segoe UI at all
# (they're proprietary Microsoft fonts) — fontconfig's metric-compatible
# substitutes cover the two font families this renderer actually uses
# (see Dockerfile: fonts-liberation, fonts-crosextra-carlito).
_LIBERATION_DIR = Path("/usr/share/fonts/truetype/liberation2")
_CARLITO_DIR = Path("/usr/share/fonts/truetype/crosextra")
# Maps a (lowercased font name, bold) the renderer actually requests to an
# ordered list of (directory, filename) candidates, tried in order until
# one exists — the Windows original first (local dev), then its Linux
# metric-compatible substitute (Render/containers). "Poppins"/other
# non-Windows fonts fall back to Segoe UI's metrics as the closest
# reasonable proxy rather than skipping measurement entirely — an
# approximate real measurement is still far more accurate than a flat
# per-character guess.
_FONT_FILES = {
    ("segoe ui", False): ((_WINDOWS_FONTS_DIR, "segoeui.ttf"), (_LIBERATION_DIR, "LiberationSans-Regular.ttf")),
    ("segoe ui", True): ((_WINDOWS_FONTS_DIR, "segoeuib.ttf"), (_LIBERATION_DIR, "LiberationSans-Bold.ttf")),
    ("arial", False): ((_WINDOWS_FONTS_DIR, "arial.ttf"), (_LIBERATION_DIR, "LiberationSans-Regular.ttf")),
    ("arial", True): ((_WINDOWS_FONTS_DIR, "arialbd.ttf"), (_LIBERATION_DIR, "LiberationSans-Bold.ttf")),
    ("calibri", False): ((_WINDOWS_FONTS_DIR, "calibri.ttf"), (_CARLITO_DIR, "Carlito-Regular.ttf")),
    ("calibri", True): ((_WINDOWS_FONTS_DIR, "calibrib.ttf"), (_CARLITO_DIR, "Carlito-Bold.ttf")),
}
_FALLBACK_FONT = ("segoe ui", False)

_font_cache: dict = {}
_pil_available: bool | None = None


def _get_font(font_name: str, bold: bool):
    global _pil_available
    if _pil_available is False:
        return None
    key = ((font_name or "").lower().strip(), bool(bold))
    if key in _font_cache:
        return _font_cache[key]

    try:
        from PIL import ImageFont
    except ImportError:
        _pil_available = False
        return None
    _pil_available = True

    candidates = _FONT_FILES.get(key) or _FONT_FILES.get(_FALLBACK_FONT) or ()
    result = None
    for font_dir, filename in candidates:
        candidate = font_dir / filename
        if candidate.exists():
            result = candidate
            break
    _font_cache[key] = result
    return result


def _measure_width_in(text: str, font_name: str, bold: bool, size_pt: float) -> float:
    """Real rendered width in inches when the font file is available,
    otherwise the same per-character estimate used elsewhere in the
    renderer (kept identical on purpose — this function's job is to be
    MORE accurate when it can be, not to disagree with the rest of the
    codebase when it can't)."""
    font_path = _get_font(font_name, bold)
    if font_path is not None:
        try:
            from PIL import ImageFont
            render_size = max(8, round(size_pt * 4))  # oversample fractional pt sizes for precision
            font = ImageFont.truetype(str(font_path), render_size)
            bbox = font.getbbox(text)
            width_px = bbox[2] - bbox[0]
            width_pt = width_px * (size_pt / render_size)
            return width_pt / 72.0
        except Exception:
            pass
    avg_char_w_in = size_pt * 0.0072
    return len(text) * avg_char_w_in


def _needed_height_in(text: str, font_name: str, bold: bool, size_pt: float,
                      box_w_in: float) -> float:
    """Height this text needs once wrapped to box_w_in, at size_pt."""
    if not text.strip():
        return 0.0
    usable_w = max(0.1, box_w_in - 2 * _TEXT_BOX_MARGIN_IN)
    total_w = _measure_width_in(text, font_name, bold, size_pt)
    lines = max(1, math.ceil(total_w / usable_w))
    line_h_in = (size_pt * _LINE_HEIGHT_FACTOR) / 72.0
    return lines * line_h_in


def check_slide(slide, slide_label: str = "") -> list[dict]:
    """Check one already-rendered slide. Returns a list of finding dicts:
    {"slide": str, "shape": str, "issue": str, "detail": str}."""
    findings = []

    for shape in slide.shapes:
        try:
            left = shape.left / 914400.0
            top = shape.top / 914400.0
            width = shape.width / 914400.0
            height = shape.height / 914400.0
        except (TypeError, AttributeError):
            continue  # shape with no geometry (e.g. a connector's own group wrapper)

        if width <= 0 or height <= 0:
            continue

        # Off-slide check
        if (left < -_EDGE_TOLERANCE_IN or top < -_EDGE_TOLERANCE_IN or
                left + width > SLIDE_W_IN + _EDGE_TOLERANCE_IN or
                top + height > SLIDE_H_IN + _EDGE_TOLERANCE_IN):
            findings.append({
                "slide": slide_label, "shape": shape.name,
                "issue": "off_slide",
                "detail": f"bounds ({left:.2f},{top:.2f})..({left+width:.2f},{top+height:.2f})in "
                          f"exceed the {SLIDE_W_IN}x{SLIDE_H_IN}in slide",
            })

        # Text overflow check — only for non-autofit text frames; a shape
        # with TEXT_TO_FIT_SHAPE autosize shrinks its own font rather than
        # overflowing, so flagging it would be a false positive.
        if not getattr(shape, "has_text_frame", False):
            continue
        tf = shape.text_frame
        try:
            from pptx.enum.text import MSO_AUTO_SIZE
            if tf.auto_size == MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE:
                continue
        except Exception:
            pass
        if not tf.word_wrap:
            continue  # no-wrap text frames grow with content by convention here, not a bug

        total_needed_h = 0.0
        combined_text = []
        font_name = None
        bold = False
        size_pt = 12.0
        for para in tf.paragraphs:
            text = para.text
            if not text.strip():
                continue
            run_font = para.font
            font_name = run_font.name or font_name or "Segoe UI"
            bold = bool(run_font.bold)
            size_pt = run_font.size.pt if run_font.size else size_pt
            total_needed_h += _needed_height_in(text, font_name, bold, size_pt, width)
            combined_text.append(text)

        if total_needed_h <= 0:
            continue

        usable_h = max(0.05, height - 2 * _TEXT_BOX_MARGIN_IN)
        if total_needed_h > usable_h + _EDGE_TOLERANCE_IN:
            findings.append({
                "slide": slide_label, "shape": shape.name,
                "issue": "text_overflow",
                "detail": f"{' | '.join(combined_text)[:60]!r} needs ~{total_needed_h:.2f}in, "
                          f"box holds ~{usable_h:.2f}in",
            })

    return findings


def check_presentation(prs) -> list[dict]:
    """Check every slide in a Presentation. Returns all findings, each
    tagged with its slide number (1-indexed, matching what a user sees)."""
    all_findings = []
    for i, slide in enumerate(prs.slides):
        all_findings.extend(check_slide(slide, slide_label=f"slide {i + 1}"))
    return all_findings
