"""Xebia Proposal Slide Builders — Dynamic Design System.

All builders accept a SlideStyle parameter that provides colors, fonts,
and accent treatments generated uniquely for each proposal by the AI
design system. No hardcoded colors or repetitive patterns.

Canvas: 13.333 x 7.500 inches (widescreen 16:9)
Template: xebia_retail.pptx
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from generation.design_generator import SlideStyle, ProposalDesignSystem
from generation.template_engine import create_themed_presentation, add_world_map
from generation.design_engine.blueprints import get_blueprint, render_blueprint


def _resolve_tech_icon(name: str):
    """Look up a real icon file for a technology/service name.

    Tries the broad AWS/Azure/Fabric icon registry first, then the
    curated general-tools registry (Kafka, Airflow, PostgreSQL, etc.).
    Returns None if neither has a match — callers keep their existing
    text-only rendering in that case.
    """
    if not name:
        return None
    try:
        from images.icon_library import IconLibrary
        icon = IconLibrary().get_icon(name)
        if icon:
            return icon
    except Exception:
        pass
    try:
        from images.tech_icon_registry import TechIconRegistry
        return TechIconRegistry().get_icon(name)
    except Exception:
        return None

# ── Layout geometry (from template placeholder analysis) ──────
# These are physical constraints, not design choices.

SLIDE_W = 13.333
SLIDE_H = 7.500
MARGIN_L = 0.61
CONTENT_L = 0.61
CONTENT_W = 12.13
CONTENT_R = 12.74
TITLE_TOP = 0.60
TITLE_H = 1.24
CONTENT_TOP = 2.00
CONTENT_BOTTOM = 6.90
CONTENT_H = 4.90
FOOTER_Y = 6.90

ACCENT_LINE_Y = 1.92
ACCENT_LINE_H = 0.03


def _distribute_rows(n: int, min_h: float, max_h: float, gap: float,
                      zone_top: float = CONTENT_TOP, zone_h: float = CONTENT_H) -> tuple[float, float]:
    """Row/card height (grown up to max_h, never shrunk below min_h) and a
    start_y that vertically centers the resulting block within the zone, so
    a short list doesn't leave a dead band at the bottom of the slide."""
    if n <= 0:
        return max_h, zone_top
    row_h = max(min_h, min(max_h, (zone_h - (n - 1) * gap) / n))
    block_h = n * row_h + (n - 1) * gap
    start_y = zone_top + max(0.0, (zone_h - block_h) / 2)
    return row_h, start_y

# Font sizes — constrained by slide geometry to prevent overflow.
SZ_HERO = 32
SZ_SECTION = 28
SZ_TITLE = 24
SZ_SUBTITLE = 14
SZ_BODY = 12
SZ_SMALL = 10
SZ_TINY = 9


# ── Core helpers ──────────────────────────────────────────────

def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def create_presentation(ds: ProposalDesignSystem, template_path: str | None = None) -> Presentation:
    if template_path is None:
        from generation.template_engine import generate_theme
        template_path = generate_theme()
    prs = create_themed_presentation(template_path)
    # Remove all existing slides from the template — keep only slide masters/layouts
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        if rId:
            prs.part.drop_rel(rId)
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[0])
    return prs


def _get_layout(prs: Presentation, name: str):
    for layout in prs.slide_layouts:
        if layout.name == name:
            return layout
    fallbacks = ["Content_Basic", "Title Content/White", "Content Title", "Blank"]
    for fb in fallbacks:
        for layout in prs.slide_layouts:
            if fb in layout.name:
                return layout
    return prs.slide_layouts[0]


def _set_text(tf, text: str, size: float, color: str,
              bold: bool = False, alignment=None, font_name: str = "Arial"):
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = Pt(size)
    p.font.color.rgb = _rgb(color)
    p.font.bold = bold
    p.font.name = font_name
    if alignment:
        p.alignment = alignment


def _add_paragraph(tf, text: str, size: float, color: str,
                   bold: bool = False, alignment=None,
                   space_before: float = 0, font_name: str = "Arial"):
    p = tf.add_paragraph()
    p.text = str(text)
    p.font.size = Pt(size)
    p.font.color.rgb = _rgb(color)
    p.font.bold = bold
    p.font.name = font_name
    if alignment:
        p.alignment = alignment
    if space_before:
        p.space_before = Pt(space_before)
    return p


def _add_shape(slide, shape_type, left, top, width, height,
               fill_color=None, line_color=None, line_width=None):
    left = max(0, min(left, SLIDE_W - 0.01))
    top = max(0, min(top, SLIDE_H - 0.01))
    width = min(width, SLIDE_W - left)
    height = min(height, SLIDE_H - top)
    shape = slide.shapes.add_shape(
        shape_type, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _rgb(fill_color) if isinstance(fill_color, str) else fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = _rgb(line_color) if isinstance(line_color, str) else line_color
        if line_width:
            shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def _add_textbox(slide, left, top, width, height, text, size, color,
                 bold=False, alignment=None, font_name="Poppins"):
    left = max(0, min(left, SLIDE_W - 0.1))
    top = max(0, min(top, SLIDE_H - 0.1))
    width = min(width, SLIDE_W - left)
    height = min(height, SLIDE_H - top)
    tx = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    _set_text(tf, text, size, color, bold=bold, alignment=alignment, font_name=font_name)
    return tx


def _get_ph(slide, idx: int):
    try:
        return slide.placeholders[idx]
    except (KeyError, IndexError):
        return None


def _fill_ph(slide, idx: int, text: str, size: float = None,
             color: str = None, bold: bool = None, alignment=None,
             font_name: str = "Arial"):
    ph = _get_ph(slide, idx)
    if ph is None:
        return None
    tf = ph.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(text)
    if size:
        p.font.size = Pt(size)
    if color:
        p.font.color.rgb = _rgb(color)
    if bold is not None:
        p.font.bold = bold
    p.font.name = font_name
    if alignment:
        p.alignment = alignment
    return ph


def _fill_ph_multi(slide, idx: int, lines: list[str],
                   size: float = SZ_BODY, color: str = "#595959",
                   bold: bool = False, bullet_char: str = "",
                   font_name: str = "Arial"):
    ph = _get_ph(slide, idx)
    if ph is None:
        return None
    tf = ph.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        prefix = f"{bullet_char} " if bullet_char else ""
        p.text = f"{prefix}{line}"
        p.font.size = Pt(size)
        p.font.color.rgb = _rgb(color)
        p.font.bold = bold
        p.font.name = font_name
        p.space_before = Pt(4) if i > 0 else Pt(0)
    return ph


# ── Picture placeholder handling ──────────────────────────────

def _get_picture_placeholders(slide):
    from pptx.oxml.ns import qn
    pic_indices = []
    for sp in slide.shapes._spTree.iterchildren(qn('p:sp')):
        nvSpPr = sp.find(qn('p:nvSpPr'))
        if nvSpPr is not None:
            nvPr = nvSpPr.find(qn('p:nvPr'))
            if nvPr is not None:
                ph = nvPr.find(qn('p:ph'))
                if ph is not None and ph.get('type') == 'pic':
                    idx = ph.get('idx')
                    if idx is not None:
                        pic_indices.append(int(idx))
    return pic_indices


def _remove_picture_placeholders(slide):
    from pptx.oxml.ns import qn
    spTree = slide.shapes._spTree
    to_remove = []
    for sp in spTree.iterchildren(qn('p:sp')):
        nvSpPr = sp.find(qn('p:nvSpPr'))
        if nvSpPr is not None:
            nvPr = nvSpPr.find(qn('p:nvPr'))
            if nvPr is not None:
                ph = nvPr.find(qn('p:ph'))
                if ph is not None and ph.get('type') == 'pic':
                    to_remove.append(sp)
    for sp in to_remove:
        spTree.remove(sp)


def _insert_image_into_placeholder(slide, image_path: str) -> bool:
    pic_indices = _get_picture_placeholders(slide)
    if not pic_indices or not image_path:
        return False
    try:
        ph = slide.placeholders[pic_indices[0]]
        ph.insert_picture(image_path)
        from pptx.oxml.ns import qn
        spTree = slide.shapes._spTree
        for idx in pic_indices[1:]:
            for sp in list(spTree.iterchildren(qn('p:sp'))):
                nvSpPr = sp.find(qn('p:nvSpPr'))
                if nvSpPr is not None:
                    nvPr = nvSpPr.find(qn('p:nvPr'))
                    if nvPr is not None:
                        ph_el = nvPr.find(qn('p:ph'))
                        if ph_el is not None and ph_el.get('type') == 'pic':
                            ph_idx = ph_el.get('idx')
                            if ph_idx is not None and int(ph_idx) == idx:
                                spTree.remove(sp)
        return True
    except Exception:
        _remove_picture_placeholders(slide)
        return False


def _add_slide(prs: Presentation, layout_name: str, image_path: str = None):
    layout = _get_layout(prs, layout_name)
    slide = prs.slides.add_slide(layout)
    if image_path:
        if not _insert_image_into_placeholder(slide, image_path):
            _remove_picture_placeholders(slide)
    else:
        _remove_picture_placeholders(slide)
    return slide


# ── Visual treatment engine ───────────────────────────────────

def _apply_composition(slide, style: SlideStyle):
    """Apply visual treatment to a slide.

    When style.blueprint_id is set, renders the full blueprint (background +
    zones + accents) from the design engine. Otherwise falls back to the
    legacy composition modes for backward compatibility.

    Mutates style.title_color, style.body_color, style.card_bg, style.border_color
    based on whether the background is dark.
    Must be called BEFORE any _fill_ph or _add_textbox calls.
    """
    if style.blueprint_id and style.design_theme:
        blueprint = get_blueprint(style.blueprint_id)
        rendered = render_blueprint(slide, blueprint, style.design_theme)
        if rendered.bg_result.is_dark:
            style.title_color = "#FFFFFF"
            style.body_color = "#D4D4D8"
            style.card_bg = "#2A2A3A"
            style.border_color = "#3F3F50"
        return

    mode = style.composition
    c = style.accent_color

    if mode == "bold_header":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, 1.85, fill_color=c)
        style.title_color = style.palette.text_light

    elif mode == "dark_full":
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
            Inches(SLIDE_W), Inches(SLIDE_H)
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = _rgb(style.palette.bg_dark)
        bg.line.fill.background()
        sp = bg._element
        sp.getparent().remove(sp)
        slide.shapes._spTree.insert(2, sp)
        style.title_color = style.palette.text_light
        style.body_color = "#D4D4D8"
        style.card_bg = "#2A2A3A"
        style.border_color = "#3F3F50"

    elif mode == "top_bar":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, 0.40, fill_color=c)

    elif mode == "left_bar":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, 0.18, SLIDE_H, fill_color=c)

    elif mode == "clean":
        _add_shape(slide, MSO_SHAPE.RECTANGLE,
                   CONTENT_L, ACCENT_LINE_Y, CONTENT_W, ACCENT_LINE_H, fill_color=c)

    elif mode == "bottom_band":
        _add_shape(slide, MSO_SHAPE.RECTANGLE,
                   0, SLIDE_H - 0.35, SLIDE_W, 0.35, fill_color=c)
    # "none" — no decoration


def _add_card(slide, x, y, w, h, style: SlideStyle, accent_color=None):
    """Add a card shape styled according to the design system."""
    cs = style.card_style
    ac = accent_color or style.accent_color
    fill = style.card_bg

    if cs == "rounded_shadow":
        shadow_offset = 0.03
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                   x + shadow_offset, y + shadow_offset, w, h,
                   fill_color="#E0E0E0")
        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                          fill_color=fill, line_color=style.border_color, line_width=0.5)
    elif cs == "flat_bordered":
        card = _add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h,
                          fill_color=fill, line_color=style.border_color, line_width=1)
    elif cs == "outlined":
        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                          fill_color=None, line_color=ac, line_width=1.5)
    elif cs == "minimal":
        card = _add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h,
                          fill_color=fill, line_color=style.border_color, line_width=0.25)
    else:  # accent_top (default)
        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                          fill_color=fill, line_color=style.border_color, line_width=0.75)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, 0.06, fill_color=ac)

    return card


def _clear_body_ph(slide):
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""
    return body_ph


# ── COVER ─────────────────────────────────────────────────────

def build_cover_slide(prs: Presentation, style: SlideStyle, title: str,
                      subtitle: str = "", customer: str = "", date: str = "",
                      image_path: str = None, layout_name: str = None) -> None:
    slide = _add_slide(prs, layout_name or "Content_Basic", image_path=image_path)
    _apply_composition(slide, style)
    _clear_body_ph(slide)
    _place_logo(slide, style)

    title_y = 2.50
    _add_textbox(slide, CONTENT_L, title_y, CONTENT_W, 1.80,
                 title, SZ_HERO, style.title_color,
                 bold=True, font_name=style.heading_font)

    # subtitle already names the customer (per SECTION_SCHEMA guidance), so
    # only append a "Prepared for" clause when the customer isn't already
    # mentioned in it — avoids repeating the customer name twice on the slide.
    prepared_for = ""
    if customer and customer.lower() not in subtitle.lower():
        prepared_for = f"Prepared for {customer}"
    sub_parts = [p for p in [subtitle, prepared_for, date] if p]
    if sub_parts:
        _add_textbox(slide, CONTENT_L, title_y + 1.90, CONTENT_W, 0.60,
                     " | ".join(sub_parts), SZ_SUBTITLE, style.body_color,
                     font_name=style.body_font)

    if customer:
        _add_textbox(slide, CONTENT_L, CONTENT_BOTTOM - 0.05, CONTENT_W, 0.55,
                     f"CONFIDENTIAL — prepared exclusively for {customer}; "
                     "not for external distribution.",
                     SZ_TINY, style.body_color, font_name=style.body_font)


# ── TABLE OF CONTENTS ─────────────────────────────────────────

def build_toc_slide(prs: Presentation, style: SlideStyle,
                    items: list[str], slide_number: int = 0,
                    layout_name: str = None) -> None:
    slide = _add_slide(prs, layout_name or "Content_Basic")
    _apply_composition(slide, style)
    title_ph = _fill_ph(slide, 0, "Table of Contents", size=SZ_TITLE, color=style.title_color,
                        bold=True, font_name=style.heading_font)
    if title_ph is None:
        # Blueprint/layout didn't expose a title placeholder at idx 0 — the
        # heading must still render, so fall back to an explicit textbox in
        # the deck's standard title zone rather than shipping a headless slide.
        _add_textbox(slide, CONTENT_L, TITLE_TOP, CONTENT_W, TITLE_H,
                     "Table of Contents", SZ_TITLE, style.title_color,
                     bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    mid = len(items) // 2 + len(items) % 2
    col1_items = items[:mid]
    col2_items = items[mid:]

    col_w = (CONTENT_W - 0.40) / 2
    item_h, start_y = _distribute_rows(max(len(col1_items), len(col2_items), 1),
                                        min_h=0.45, max_h=0.85, gap=0.0,
                                        zone_top=CONTENT_TOP + 0.15, zone_h=CONTENT_H - 0.15)

    for i, item in enumerate(col1_items):
        y = start_y + i * item_h
        num_text = f"{i+1:02d}"
        _add_textbox(slide, CONTENT_L, y, 0.55, item_h,
                     num_text, 14, style.accent_color, bold=True,
                     font_name=style.heading_font)
        _add_textbox(slide, CONTENT_L + 0.55, y, col_w - 0.55, item_h,
                     item, 13, style.body_color, font_name=style.body_font)

    for i, item in enumerate(col2_items):
        y = start_y + i * item_h
        num = mid + i + 1
        num_text = f"{num:02d}"
        col2_x = CONTENT_L + col_w + 0.40
        _add_textbox(slide, col2_x, y, 0.55, item_h,
                     num_text, 14, style.accent_color, bold=True,
                     font_name=style.heading_font)
        _add_textbox(slide, col2_x + 0.55, y, col_w - 0.55, item_h,
                     item, 13, style.body_color, font_name=style.body_font)


# ── SECTION DIVIDER ───────────────────────────────────────────

def build_section_divider(prs: Presentation, style: SlideStyle, title: str,
                          slide_number: int = 0, image_path: str = None,
                          use_light: bool = False, layout_name: str = None) -> None:
    slide = _add_slide(prs, layout_name or "Content_Basic", image_path=image_path)
    _apply_composition(slide, style)
    _clear_body_ph(slide)
    _place_logo(slide, style)

    # Decorative background art (blob/curve accents from the blueprint) can
    # land anywhere behind the title on a divider, since there's no card or
    # body content to occlude it. Give the title a solid backing panel in the
    # theme's own card color so it stays legible no matter what renders
    # underneath — same contrast guarantee the theme already provides cards.
    title_y = 2.80
    _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, CONTENT_L - 0.20, title_y - 0.18,
               CONTENT_W + 0.40, 1.05, fill_color=style.card_bg)
    _add_textbox(slide, CONTENT_L, title_y, CONTENT_W, 1.50,
                 title, SZ_SECTION, style.title_color,
                 bold=True, font_name=style.heading_font)


# ── EXECUTIVE SUMMARY ─────────────────────────────────────────

def build_executive_summary_slide(prs: Presentation, style: SlideStyle,
                                  title: str, summary_text: str = "",
                                  key_points: list[str] = None,
                                  slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)

    body_ph = _get_ph(slide, 1)
    if body_ph:
        tf = body_ph.text_frame
        tf.word_wrap = True
        if summary_text:
            p = tf.paragraphs[0]
            p.text = summary_text
            p.font.size = Pt(SZ_BODY)
            p.font.color.rgb = _rgb(style.body_color)
            p.font.name = style.body_font
            p.space_after = Pt(12)

        if key_points:
            p_header = tf.add_paragraph()
            p_header.text = "Key Highlights"
            p_header.font.size = Pt(SZ_SUBTITLE)
            p_header.font.color.rgb = _rgb(style.accent_color)
            p_header.font.bold = True
            p_header.font.name = style.heading_font
            p_header.space_before = Pt(12)

            for point in key_points[:6]:
                p = tf.add_paragraph()
                p.text = f"▸  {point}"
                p.font.size = Pt(11)
                p.font.color.rgb = _rgb(style.body_color)
                p.font.name = style.body_font
                p.space_before = Pt(4)


# ── CONTENT SLIDE ─────────────────────────────────────────────

def build_content_slide(prs: Presentation, style: SlideStyle, title: str,
                        body_text: str = "", bullets: list[str] = None,
                        slide_number: int = 0) -> None:
    if not body_text and not bullets:
        # This is both the "content" layout and the catch-all fallback for
        # any unrecognized layout — with no body/bullets the body
        # placeholder never gets touched and ships as a raw, unfilled
        # template ghost. Skip rather than show that.
        return

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)

    body_ph = _get_ph(slide, 1)
    if body_ph:
        tf = body_ph.text_frame
        tf.word_wrap = True
        first_para = True
        if body_text:
            p = tf.paragraphs[0]
            p.text = body_text
            p.font.size = Pt(SZ_BODY)
            p.font.color.rgb = _rgb(style.body_color)
            p.font.name = style.body_font
            first_para = False

        if bullets:
            for bullet in bullets:
                p = tf.paragraphs[0] if first_para else tf.add_paragraph()
                first_para = False
                p.text = f"▸  {bullet}"
                p.font.size = Pt(11)
                p.font.color.rgb = _rgb(style.body_color)
                p.font.name = style.body_font
                p.space_before = Pt(4)


# ── CONTENT WITH PHOTO ────────────────────────────────────────

def build_content_photo_slide(prs: Presentation, style: SlideStyle, title: str,
                              subtitle: str = "", body_text: str = "",
                              bullets: list[str] = None,
                              image_path: str = None,
                              prefer_left: bool = False,
                              use_dark: bool = False,
                              slide_number: int = 0) -> None:
    if use_dark:
        layout = "Content_Photo-Big_left_dark" if prefer_left else "Content_Photo-Big_right_dark"
        text_color = style.palette.text_light
        body_clr = "#E0E0E0"
    else:
        layout = "Content_Photo-Big_left" if prefer_left else "Content_Photo-Big_right"
        text_color = style.title_color
        body_clr = style.body_color

    slide = _add_slide(prs, layout, image_path=image_path)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=text_color,
             bold=True, font_name=style.heading_font)

    if subtitle:
        _fill_ph(slide, 11, subtitle, size=SZ_SUBTITLE, color=style.accent_color,
                 bold=True, font_name=style.heading_font)

    body_ph = _get_ph(slide, 1)
    if body_ph:
        tf = body_ph.text_frame
        tf.word_wrap = True
        first_para = True
        if body_text:
            p = tf.paragraphs[0]
            p.text = body_text
            p.font.size = Pt(SZ_BODY)
            p.font.color.rgb = _rgb(body_clr)
            p.font.name = style.body_font
            first_para = False
        if bullets:
            for bullet in bullets:
                p = tf.paragraphs[0] if first_para else tf.add_paragraph()
                first_para = False
                p.text = f"▸  {bullet}"
                p.font.size = Pt(11)
                p.font.color.rgb = _rgb(body_clr)
                p.font.name = style.body_font
                p.space_before = Pt(4)


# ── TWO COLUMN ────────────────────────────────────────────────

def build_two_column_slide(prs: Presentation, style: SlideStyle, title: str,
                           left_title: str = "", left_bullets: list[str] = None,
                           right_title: str = "", right_bullets: list[str] = None,
                           slide_number: int = 0) -> None:
    if not left_bullets and not right_bullets:
        # Both columns empty means the unfilled PowerPoint placeholders
        # (left/right title + body) would ship as raw template ghosts —
        # skip the slide rather than show that.
        return

    slide = _add_slide(prs, "Content_2 Columns")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)

    if left_title:
        _fill_ph(slide, 11, left_title, size=SZ_SUBTITLE, color=style.accent_color,
                 bold=True, font_name=style.heading_font)
    if left_bullets:
        _fill_ph_multi(slide, 1, left_bullets, size=11, color=style.body_color,
                       bullet_char="▸", font_name=style.body_font)
    if right_title:
        _fill_ph(slide, 14, right_title, size=SZ_SUBTITLE, color=style.accent_color,
                 bold=True, font_name=style.heading_font)
    if right_bullets:
        _fill_ph_multi(slide, 13, right_bullets, size=11, color=style.body_color,
                       bullet_char="▸", font_name=style.body_font)


# ── ICON GRID ─────────────────────────────────────────────────

def build_icon_grid_slide(prs: Presentation, style: SlideStyle, title: str,
                          items: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    accents = style.palette
    cycle = [accents.primary, accents.accent1, accents.secondary,
             accents.accent2, accents.accent3]

    num_items = min(len(items), 9)
    cols = 3 if num_items > 2 else num_items
    rows = (num_items + cols - 1) // cols
    gap_x, gap_y = 0.25, 0.20
    card_w = (CONTENT_W - (cols - 1) * gap_x) / cols
    # min_h is a floor, not a forced value: with 3 rows (7-9 items) at a
    # fixed 2.2" each the grid would overflow CONTENT_H (7.0" > 4.9") — a
    # low floor lets row_h shrink to fit while still centering/growing
    # toward 2.2" when there's only 1-2 rows.
    card_h, grid_top = _distribute_rows(rows, min_h=0.5, max_h=2.2, gap=gap_y)

    for i, item in enumerate(items[:num_items]):
        col, row = i % cols, i // cols
        x = CONTENT_L + col * (card_w + gap_x)
        y = grid_top + row * (card_h + gap_y)
        color = cycle[i % len(cycle)]

        _add_card(slide, x, y, card_w, card_h, style, accent_color=color)

        icon_size = 0.42
        _add_shape(slide, MSO_SHAPE.OVAL, x + 0.2, y + 0.2,
                   icon_size, icon_size, fill_color=color)
        initial = item.get("label", "X")[0].upper()
        _add_textbox(slide, x + 0.2, y + 0.24, icon_size, icon_size - 0.08,
                     initial, 14, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        _add_textbox(slide, x + 0.75, y + 0.22, card_w - 0.95, 0.35,
                     item.get("label", ""), SZ_SUBTITLE, style.title_color,
                     bold=True, font_name=style.heading_font)

        desc = item.get("description", "")
        if desc:
            _add_textbox(slide, x + 0.2, y + 0.75, card_w - 0.4, card_h - 0.95,
                         desc, SZ_SMALL, style.body_color, font_name=style.body_font)


# ── PROCESS FLOW ──────────────────────────────────────────────

def build_process_flow_slide(prs: Presentation, style: SlideStyle, title: str,
                             steps: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    normalized = []
    for s in steps:
        if isinstance(s, str):
            normalized.append({"label": s, "description": ""})
        else:
            normalized.append(s)

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3]

    num_steps = min(len(normalized), 6)
    gap = 0.20
    step_w = (CONTENT_W - (num_steps - 1) * gap) / num_steps
    circle_y = 2.30
    circle_size = 0.50
    card_top = 3.10
    card_h = min(3.60, CONTENT_BOTTOM - card_top - 0.1)

    _add_shape(slide, MSO_SHAPE.RECTANGLE,
               CONTENT_L, circle_y + circle_size / 2 - 0.015,
               CONTENT_W, 0.03, fill_color=style.border_color)

    for i, step in enumerate(normalized[:num_steps]):
        x = CONTENT_L + i * (step_w + gap)
        color = cycle[i % len(cycle)]

        cx = x + (step_w - circle_size) / 2
        _add_shape(slide, MSO_SHAPE.OVAL, cx, circle_y,
                   circle_size, circle_size, fill_color=color)
        _add_textbox(slide, cx, circle_y + 0.05, circle_size, circle_size - 0.1,
                     str(i + 1), 16, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        _add_card(slide, x, card_top, step_w, card_h, style, accent_color=color)

        # The numbered circle above already conveys the ordinal — strip a
        # leading "1. "/"1) " the LLM sometimes repeats in the label itself,
        # so the number doesn't show twice.
        label = re.sub(r"^\d+[.)]\s*", "", step.get("label", ""))
        _add_textbox(slide, x + 0.1, card_top + 0.15, step_w - 0.2, 0.40,
                     label, 11, style.title_color, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        desc = step.get("description", "")
        if desc:
            _add_textbox(slide, x + 0.1, card_top + 0.60, step_w - 0.2, card_h - 0.80,
                         desc, SZ_SMALL, style.body_color,
                         alignment=PP_ALIGN.CENTER, font_name=style.body_font)

        if i < num_steps - 1:
            ax = x + step_w + 0.02
            muted = style.palette.accent1
            _add_shape(slide, MSO_SHAPE.RIGHT_ARROW, ax, circle_y + 0.10,
                       gap - 0.04, 0.30, fill_color=muted)


# ── COMPARISON TABLE ──────────────────────────────────────────

def build_comparison_table_slide(prs: Presentation, style: SlideStyle, title: str,
                                 headers: list[str], rows: list[list[str]],
                                 caption: str = "", slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    caption_h = 0.35 if caption else 0.0
    num_cols = len(headers)
    num_rows = min(len(rows) + 1, 12)
    row_height, table_top = _distribute_rows(num_rows, min_h=0.35, max_h=0.75, gap=0.0,
                                             zone_top=CONTENT_TOP + 0.15,
                                             zone_h=CONTENT_H - 0.15 - caption_h)
    table_w = min(CONTENT_W, 11.8)

    table_shape = slide.shapes.add_table(
        num_rows, num_cols,
        Inches(CONTENT_L), Inches(table_top),
        Inches(table_w), Inches(row_height * num_rows)
    )
    table = table_shape.table
    col_w = table_w / num_cols
    for i in range(num_cols):
        table.columns[i].width = Inches(col_w)

    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = _rgb(style.accent_color)
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(11)
            p.font.color.rgb = _rgb(style.palette.text_light)
            p.font.bold = True
            p.font.name = style.heading_font
            p.alignment = PP_ALIGN.CENTER

    for r_idx, row in enumerate(rows[:num_rows - 1]):
        for c_idx, val in enumerate(row[:num_cols]):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = str(val)
            bg = style.card_bg if r_idx % 2 == 0 else "#FFFFFF"
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(bg)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(SZ_SMALL)
                p.font.color.rgb = _rgb(style.body_color)
                p.font.name = style.body_font

    if caption:
        _add_textbox(slide, CONTENT_L, table_top + row_height * num_rows + 0.06,
                     table_w, caption_h - 0.06,
                     caption, SZ_TINY, style.body_color,
                     font_name=style.body_font)


# ── STATS HIGHLIGHT ───────────────────────────────────────────

def build_stats_highlight_slide(prs: Presentation, style: SlideStyle, title: str,
                                stats: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3]

    num_stats = min(len(stats), 4)
    gap = 0.30
    card_w = (CONTENT_W - (num_stats - 1) * gap) / num_stats
    stat_card_h = min(3.8, CONTENT_H - 0.2)
    card_h, card_y = _distribute_rows(1, min_h=stat_card_h, max_h=stat_card_h, gap=0.0)

    for i, stat in enumerate(stats[:4]):
        x = CONTENT_L + i * (card_w + gap)
        color = cycle[i % len(cycle)]

        _add_card(slide, x, card_y, card_w, card_h, style, accent_color=color)

        icon_size = 0.50
        _add_shape(slide, MSO_SHAPE.OVAL,
                   x + (card_w - icon_size) / 2, card_y + 0.30,
                   icon_size, icon_size, fill_color=color)

        # The LLM occasionally emits a value that's a short phrase rather
        # than a bare number/percentage (e.g. "0 Downtime" instead of
        # value="0" + label="Downtime") — at a fixed 36pt that wraps and
        # overflows into the label below it. Scale down for longer values
        # so it always fits within its box instead of bleeding over.
        value_text = str(stat.get("value", ""))
        value_size = 36 if len(value_text) <= 6 else max(16, 36 - 2 * (len(value_text) - 6))
        _add_textbox(slide, x + 0.1, card_y + 1.0, card_w - 0.2, 0.80,
                     value_text, value_size, color,
                     bold=True, alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        _add_textbox(slide, x + 0.1, card_y + 1.85, card_w - 0.2, 0.40,
                     stat.get("label", ""), 13, style.title_color,
                     bold=True, alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        sublabel = stat.get("description", "")
        if sublabel:
            _add_textbox(slide, x + 0.1, card_y + 2.30, card_w - 0.2, 1.2,
                         sublabel, SZ_SMALL, style.body_color,
                         alignment=PP_ALIGN.CENTER, font_name=style.body_font)


# ── KEY-VALUE PAIRS ───────────────────────────────────────────

def build_key_value_slide(prs: Presentation, style: SlideStyle, title: str,
                          pairs: list[dict], slide_number: int = 0) -> None:
    if not pairs:
        # A title with no pairs (e.g. an under-generated case study) would
        # render as a near-blank slide with nothing but a heading — skip it
        # rather than ship a slide with no actual content.
        return

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    n = len(pairs[:10])
    row_h, start_y = _distribute_rows(n, min_h=0.50, max_h=0.85, gap=0.0,
                                       zone_top=CONTENT_TOP + 0.1, zone_h=CONTENT_H - 0.1)
    key_w = 3.5

    for i, pair in enumerate(pairs[:10]):
        y = start_y + i * row_h
        if y + row_h > CONTENT_BOTTOM:
            break
        bg = style.card_bg if i % 2 == 0 else "#FFFFFF"
        _add_shape(slide, MSO_SHAPE.RECTANGLE,
                   CONTENT_L, y, CONTENT_W, row_h, fill_color=bg)
        _add_shape(slide, MSO_SHAPE.RECTANGLE,
                   CONTENT_L, y, 0.06, row_h, fill_color=style.accent_color)
        _add_textbox(slide, CONTENT_L + 0.2, y + 0.07, key_w, row_h - 0.14,
                     str(pair.get("key", "")), SZ_BODY, style.accent_color,
                     bold=True, font_name=style.heading_font)
        _add_textbox(slide, CONTENT_L + key_w + 0.4, y + 0.07,
                     CONTENT_W - key_w - 0.6, row_h - 0.14,
                     str(pair.get("value", "")), SZ_BODY, style.body_color,
                     font_name=style.body_font)


# ── TIMELINE ──────────────────────────────────────────────────

def _parse_weeks_from_duration(duration: str, fallback_weeks: int = 2) -> int:
    """Best-effort parse of a week count from a human label like "Week 1-4"
    or "3 Weeks" when a phase doesn't supply duration_weeks explicitly —
    keeps the Gantt renderer usable even against older-shaped plan data."""
    import re
    if not duration:
        return fallback_weeks
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", duration)
    if m:
        return max(1, int(m.group(2)) - int(m.group(1)) + 1)
    m = re.search(r"(\d+)", duration)
    if m:
        return max(1, int(m.group(1)))
    return fallback_weeks


def build_timeline_slide(prs: Presentation, style: SlideStyle, title: str,
                         phases: list[dict], slide_number: int = 0) -> None:
    """Week-ruled Gantt: one row per phase/workstream, bars positioned by
    start_week/duration_weeks so genuinely parallel workstreams can overlap,
    instead of a purely sequential phase-card layout."""
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3]

    # Normalize start_week/duration_weeks, filling gaps sequentially for any
    # phase that omits them so older-shaped plan data still renders sanely.
    normalized = []
    cursor = 1
    for phase in phases[:8]:
        dur = phase.get("duration_weeks")
        if not isinstance(dur, int) or dur <= 0:
            dur = _parse_weeks_from_duration(phase.get("duration", ""))
        start = phase.get("start_week")
        if not isinstance(start, int) or start <= 0:
            start = cursor
        normalized.append({**phase, "start_week": start, "duration_weeks": dur})
        cursor = start + dur

    if not normalized:
        return

    total_weeks = max(p["start_week"] + p["duration_weeks"] - 1 for p in normalized)

    label_w = 2.6
    chart_x = CONTENT_L + label_w
    chart_w = CONTENT_R - chart_x
    week_col_w = chart_w / total_weeks

    _add_textbox(slide, CONTENT_L, CONTENT_TOP - 0.35, CONTENT_W, 0.30,
                 f"TOTAL PROJECT TIMELINE: {total_weeks} WEEKS", SZ_SMALL,
                 style.accent_color, bold=True, alignment=PP_ALIGN.CENTER,
                 font_name=style.heading_font)

    header_y = CONTENT_TOP + 0.05
    header_h = 0.30
    n = len(normalized)
    row_h, rows_start_y = _distribute_rows(
        n, min_h=0.35, max_h=0.55, gap=0.08,
        zone_top=header_y + header_h + 0.10,
        zone_h=CONTENT_BOTTOM - (header_y + header_h + 0.10))
    chart_bottom = rows_start_y + n * row_h + (n - 1) * 0.08

    # Week-number ticks and vertical gridlines behind the bars.
    week_step = 1 if total_weeks <= 14 else 2
    for w in range(0, total_weeks + 1, week_step):
        gx = chart_x + w * week_col_w
        if w > 0:
            label_box_w = max(week_col_w, 0.45)
            tick = _add_textbox(slide, gx - label_box_w / 2, header_y, label_box_w, header_h,
                                f"W{w}", SZ_TINY, style.body_color, bold=True,
                                alignment=PP_ALIGN.CENTER, font_name=style.body_font)
            tick.text_frame.word_wrap = False
        _add_shape(slide, MSO_SHAPE.RECTANGLE, gx, header_y + header_h,
                   0.01, chart_bottom - (header_y + header_h), fill_color=style.border_color)

    _add_shape(slide, MSO_SHAPE.RECTANGLE, chart_x, header_y + header_h,
               chart_w, 0.02, fill_color=style.border_color)

    for i, phase in enumerate(normalized):
        y = rows_start_y + i * (row_h + 0.08)
        color = cycle[i % len(cycle)]

        _add_textbox(slide, CONTENT_L, y + 0.03, label_w - 0.15, row_h,
                     phase.get("name", ""), SZ_SMALL, style.title_color,
                     bold=True, font_name=style.heading_font)

        bar_x = chart_x + (phase["start_week"] - 1) * week_col_w
        bar_w = max(phase["duration_weeks"] * week_col_w - 0.04, 0.15)
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, bar_x, y, bar_w, row_h,
                   fill_color=color)

        duration_label = phase.get("duration") or f"{phase['duration_weeks']}w"
        if bar_w >= 0.7:
            _add_textbox(slide, bar_x, y + 0.03, bar_w, row_h, duration_label,
                         SZ_TINY, style.palette.text_light, bold=True,
                         alignment=PP_ALIGN.CENTER, font_name=style.body_font)
        else:
            _add_textbox(slide, bar_x + bar_w + 0.06, y + 0.03, 1.0, row_h,
                         duration_label, SZ_TINY, style.body_color,
                         font_name=style.body_font)


# ── TEAM ──────────────────────────────────────────────────────

def build_team_slide(prs: Presentation, style: SlideStyle, title: str,
                     team_members: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3]

    num_members = min(len(team_members), 8)
    cols = min(num_members, 4)
    gap_x, gap_y = 0.20, 0.15
    card_w = (CONTENT_W - (cols - 1) * gap_x) / cols
    rows = (num_members + cols - 1) // cols
    card_h, grid_top = _distribute_rows(rows, min_h=0.5, max_h=2.0, gap=gap_y)

    for i, member in enumerate(team_members[:num_members]):
        col, row = i % cols, i // cols
        x = CONTENT_L + col * (card_w + gap_x)
        y = grid_top + row * (card_h + gap_y)
        color = cycle[i % len(cycle)]

        _add_card(slide, x, y, card_w, card_h, style, accent_color=color)

        avatar_size = 0.48
        _add_shape(slide, MSO_SHAPE.OVAL,
                   x + (card_w - avatar_size) / 2, y + 0.18,
                   avatar_size, avatar_size, fill_color=color)

        name = member.get("name", "TBD")
        initials = "".join(w[0].upper() for w in name.split()[:2] if w)
        _add_textbox(slide, x + (card_w - avatar_size) / 2, y + 0.24,
                     avatar_size, avatar_size - 0.12,
                     initials, 13, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        _add_textbox(slide, x + 0.1, y + 0.78, card_w - 0.2, 0.30,
                     name, 11, style.title_color, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)
        _add_textbox(slide, x + 0.1, y + 1.08, card_w - 0.2, 0.25,
                     member.get("role", ""), SZ_SMALL, style.accent_color,
                     alignment=PP_ALIGN.CENTER, font_name=style.body_font)

        expertise = member.get("expertise", "")
        if expertise:
            _add_textbox(slide, x + 0.1, y + 1.33, card_w - 0.2, card_h - 1.50,
                         expertise, SZ_TINY, style.body_color,
                         alignment=PP_ALIGN.CENTER, font_name=style.body_font)


# ── COMMERCIALS TABLE ─────────────────────────────────────────

def build_commercials_slide(prs: Presentation, style: SlideStyle, title: str,
                            rows: list[dict] = None, total: str = "",
                            assumptions: list[str] = None,
                            slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    if rows:
        headers = ["Role / Item", "Hours", "Rate ($/hr)", "Cost ($)"]
        num_rows = len(rows) + 2
        # Grows row height when the table is short, but stays top-anchored
        # (rather than centered) so it lines up with the Assumptions column,
        # which starts at the same CONTENT_TOP + 0.1 y-position.
        row_h, _ = _distribute_rows(num_rows, min_h=0.42, max_h=0.65, gap=0.0,
                                    zone_top=CONTENT_TOP + 0.1, zone_h=CONTENT_H - 0.1)
        table_w = 8.0
        table_shape = slide.shapes.add_table(
            num_rows, 4,
            Inches(CONTENT_L), Inches(CONTENT_TOP + 0.1),
            Inches(table_w), Inches(row_h * num_rows)
        )
        table = table_shape.table
        table.columns[0].width = Inches(3.5)
        table.columns[1].width = Inches(1.5)
        table.columns[2].width = Inches(1.5)
        table.columns[3].width = Inches(1.5)

        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(style.accent_color)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = _rgb(style.palette.text_light)
                p.font.bold = True
                p.font.name = style.heading_font

        for r_idx, row in enumerate(rows):
            for c_idx, key in enumerate(["item", "hours", "rate", "cost"]):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = str(row.get(key, ""))
                bg = style.card_bg if r_idx % 2 == 0 else "#FFFFFF"
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(bg)
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(SZ_SMALL)
                    p.font.color.rgb = _rgb(style.body_color)
                    p.font.name = style.body_font

        total_row = num_rows - 1
        light_accent = _lighten_color(style.accent_color, 0.85)
        for c_idx in range(4):
            cell = table.cell(total_row, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(light_accent)
            if c_idx == 0:
                cell.text = "TOTAL"
            elif c_idx == 3:
                cell.text = str(total)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.bold = True
                p.font.color.rgb = _rgb(style.accent_color)
                p.font.name = style.heading_font

    if assumptions:
        assume_x = CONTENT_L + 8.5
        _add_textbox(slide, assume_x, CONTENT_TOP + 0.1, 3.5, 0.35,
                     "Assumptions", 13, style.accent_color, bold=True,
                     font_name=style.heading_font)
        for i, assumption in enumerate(assumptions[:6]):
            y = CONTENT_TOP + 0.55 + i * 0.48
            _add_shape(slide, MSO_SHAPE.OVAL,
                       assume_x, y + 0.05, 0.10, 0.10, fill_color=style.accent_color)
            _add_textbox(slide, assume_x + 0.20, y, 3.2, 0.42,
                         assumption, SZ_TINY, style.body_color, font_name=style.body_font)


_LOGO_DIR = Path(__file__).resolve().parent.parent.parent / "xebia_design_system" / "assets" / "logos"
_LOGO_ASPECT = 85 / 29  # native SVG viewBox width/height


def _place_logo(slide, style: SlideStyle, top: float = 0.55, width: float = 0.85):
    """Place the Xebia wordmark top-left, picking the white variant on dark
    backgrounds and the near-black variant on light ones for contrast."""
    is_dark_bg = style.title_color.upper() == "#FFFFFF"
    logo_path = _LOGO_DIR / ("xebia_logo_light.png" if is_dark_bg else "xebia_logo_dark.png")
    if not logo_path.exists():
        return
    try:
        slide.shapes.add_picture(str(logo_path), Inches(CONTENT_L), Inches(top),
                                  width=Inches(width), height=Inches(width / _LOGO_ASPECT))
    except Exception:
        pass


def _lighten_color(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


# ── CLOSING ───────────────────────────────────────────────────

def build_closing_slide(prs: Presentation, style: SlideStyle,
                        title: str = "Thank You",
                        contact_name: str = "", contact_email: str = "",
                        contact_phone: str = "", slide_number: int = 0,
                        image_path: str = None, layout_name: str = None) -> None:
    slide = _add_slide(prs, layout_name or "Content_Basic", image_path=image_path)
    _apply_composition(slide, style)
    _clear_body_ph(slide)
    _place_logo(slide, style)

    _add_textbox(slide, CONTENT_L, 2.20, CONTENT_W, 1.80,
                 title, SZ_HERO, style.title_color,
                 bold=True, alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

    contact_parts = [p for p in [contact_name, contact_email, contact_phone] if p]
    if contact_parts:
        _add_textbox(slide, CONTENT_L, 4.20, CONTENT_W, 1.20,
                     "\n".join(contact_parts), SZ_SUBTITLE, style.body_color,
                     alignment=PP_ALIGN.CENTER, font_name=style.body_font)


# ── ARCHITECTURE DIAGRAM ─────────────────────────────────────

def build_architecture_slide(prs: Presentation, style: SlideStyle, title: str,
                             layers: list[dict] = None,
                             slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    if not layers:
        layers = [
            {"name": "Source Systems", "components": ["Data Sources"], "color": "blue"},
            {"name": "Ingestion", "components": ["Data Ingestion"], "color": "teal"},
            {"name": "Processing", "components": ["Transformation"], "color": "purple"},
            {"name": "Storage", "components": ["Data Store"], "color": "green"},
            {"name": "Consumption", "components": ["Analytics"], "color": "orange"},
        ]

    color_map = {
        "blue": style.palette.secondary,
        "teal": style.palette.accent1,
        "purple": style.palette.primary,
        "green": style.palette.accent3,
        "orange": style.palette.accent2,
        "light_blue": style.palette.accent1,
        "red": "#C00000",
        "gold": "#F2C811",
    }

    num_layers = min(len(layers), 7)
    arrow_gap = 0.12
    available_h = CONTENT_BOTTOM - CONTENT_TOP - 0.2
    layer_h = (available_h - (num_layers - 1) * arrow_gap) / num_layers
    layer_h = min(layer_h, 0.85)
    label_w = 2.2
    diagram_w = CONTENT_W

    for i, layer in enumerate(layers[:num_layers]):
        y = CONTENT_TOP + 0.1 + i * (layer_h + arrow_gap)
        color_name = layer.get("color", list(color_map.keys())[i % len(color_map)])
        color = color_map.get(color_name, style.palette.primary)

        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                   CONTENT_L, y, diagram_w, layer_h,
                   fill_color=style.card_bg,
                   line_color=style.border_color, line_width=0.5)

        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                   CONTENT_L, y, label_w, layer_h, fill_color=color)
        _add_textbox(slide, CONTENT_L + 0.12, y + (layer_h - 0.30) / 2,
                     label_w - 0.24, 0.30,
                     layer.get("name", ""), 11, style.palette.text_light,
                     bold=True, font_name=style.heading_font)

        components = layer.get("components", [])
        if components:
            num_comp = min(len(components), 5)
            comp_area_x = CONTENT_L + label_w + 0.12
            comp_area_w = diagram_w - label_w - 0.24
            comp_gap = 0.10
            comp_w = (comp_area_w - (num_comp - 1) * comp_gap) / num_comp
            comp_h = layer_h - 0.16

            for j, comp in enumerate(components[:num_comp]):
                cx = comp_area_x + j * (comp_w + comp_gap)
                cy = y + 0.08
                _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                           cx, cy, comp_w, comp_h,
                           fill_color="#FFFFFF",
                           line_color=color, line_width=1)

                icon_path = _resolve_tech_icon(comp)
                if icon_path and comp_h >= 0.5:
                    icon_size = min(0.32, comp_h - 0.32)
                    icon_x = cx + (comp_w - icon_size) / 2
                    icon_y = cy + 0.06
                    try:
                        slide.shapes.add_picture(str(icon_path), Inches(icon_x), Inches(icon_y),
                                                  height=Inches(icon_size))
                    except Exception:
                        icon_path = None

                if icon_path and comp_h >= 0.5:
                    label_top = cy + 0.06 + icon_size + 0.03
                    label_h = max(0.15, cy + comp_h - label_top)
                    _add_textbox(slide, cx + 0.05, label_top,
                                 comp_w - 0.1, label_h,
                                 comp, SZ_TINY - 1, style.body_color,
                                 alignment=PP_ALIGN.CENTER, font_name=style.body_font)
                else:
                    _add_textbox(slide, cx + 0.05, cy + (comp_h - 0.25) / 2,
                                 comp_w - 0.1, 0.25,
                                 comp, SZ_TINY, style.body_color,
                                 alignment=PP_ALIGN.CENTER, font_name=style.body_font)

        if i < num_layers - 1:
            arrow_y = y + layer_h + 0.01
            arrow_x = CONTENT_L + diagram_w / 2 - 0.12
            _add_shape(slide, MSO_SHAPE.DOWN_ARROW,
                       arrow_x, arrow_y, 0.24, arrow_gap - 0.02,
                       fill_color=style.palette.accent1)


# ── TECHNOLOGY CARDS ──────────────────────────────────────────

def build_technology_slide(prs: Presentation, style: SlideStyle, title: str,
                           technologies: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3]

    num_items = min(len(technologies), 6)
    cols = min(num_items, 3)
    rows = (num_items + cols - 1) // cols
    gap_x, gap_y = 0.20, 0.15
    card_w = (CONTENT_W - (cols - 1) * gap_x) / cols
    card_h, grid_top = _distribute_rows(rows, min_h=0.5, max_h=2.0, gap=gap_y)

    for i, tech in enumerate(technologies[:num_items]):
        col, row = i % cols, i // cols
        x = CONTENT_L + col * (card_w + gap_x)
        y = grid_top + row * (card_h + gap_y)
        color = cycle[i % len(cycle)]

        _add_card(slide, x, y, card_w, card_h, style, accent_color=color)

        _add_shape(slide, MSO_SHAPE.RECTANGLE,
                   x, y, 0.07, card_h, fill_color=color)

        category = tech.get("category", "Technology")
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                   x + 0.22, y + 0.12, 1.6, 0.26, fill_color=color)
        _add_textbox(slide, x + 0.27, y + 0.13, 1.5, 0.23,
                     category.upper(), 8, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        tech_name = tech.get("name", "")
        icon_path = _resolve_tech_icon(tech_name)
        name_x = x + 0.22
        name_w = card_w - 0.40
        if icon_path:
            icon_size = 0.34
            try:
                slide.shapes.add_picture(str(icon_path), Inches(x + card_w - icon_size - 0.18),
                                          Inches(y + 0.10), height=Inches(icon_size))
                name_w = card_w - 0.40 - icon_size - 0.10
            except Exception:
                pass

        _add_textbox(slide, name_x, y + 0.50, name_w, 0.35,
                     tech_name, SZ_SUBTITLE, style.title_color,
                     bold=True, font_name=style.heading_font)

        desc = tech.get("description", "")
        if desc:
            _add_textbox(slide, x + 0.22, y + 0.90, card_w - 0.40, card_h - 1.10,
                         desc, SZ_SMALL, style.body_color, font_name=style.body_font)


# ── CHALLENGES & SOLUTIONS ───────────────────────────────────

def build_challenges_slide(prs: Presentation, style: SlideStyle, title: str,
                           challenges: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    col_headers = [
        ("Challenge", "#C00000"),
        ("Impact", style.palette.accent2),
        ("Solution", style.palette.accent3),
    ]
    col_w = (CONTENT_W - 0.20) / 3
    header_y = CONTENT_TOP + 0.1

    for j, (header, hcolor) in enumerate(col_headers):
        hx = CONTENT_L + j * (col_w + 0.10)
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
                   hx, header_y, col_w, 0.40, fill_color=hcolor)
        _add_textbox(slide, hx + 0.1, header_y + 0.03, col_w - 0.2, 0.32,
                     header, 11, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

    rows_zone_top = header_y + 0.55
    n = len(challenges[:5])
    row_h, rows_start_y = _distribute_rows(n, min_h=0.75, max_h=1.15, gap=0.08,
                                           zone_top=rows_zone_top,
                                           zone_h=CONTENT_BOTTOM - rows_zone_top)
    for i, ch in enumerate(challenges[:5]):
        y = rows_start_y + i * (row_h + 0.08)
        if y + row_h > CONTENT_BOTTOM:
            break
        keys_colors = [
            ("challenge", "#C00000"),
            ("impact", style.palette.accent2),
            ("solution", style.palette.accent3),
        ]
        for j, (key, ccolor) in enumerate(keys_colors):
            cx = CONTENT_L + j * (col_w + 0.10)
            _add_card(slide, cx, y, col_w, row_h, style)
            _add_shape(slide, MSO_SHAPE.RECTANGLE,
                       cx, y, 0.05, row_h, fill_color=ccolor)
            _add_textbox(slide, cx + 0.15, y + 0.06, col_w - 0.25, row_h - 0.12,
                         ch.get(key, ""), SZ_SMALL, style.body_color,
                         font_name=style.body_font)


# ── GLOBAL PRESENCE ───────────────────────────────────────────

_MAP_ASSET = _LOGO_DIR.parent / "maps" / "world_presence_map.png"
_MAP_PX_W, _MAP_PX_H = 1532, 634
# Equirectangular fit calibrated against Xebia's own reference deck's map
# graphic (least-squares fit of known hub lon/lat to that image's pixels).
_MAP_LON_A, _MAP_LON_B = 5.15818, 706.866   # px_x = A * lon + B
_MAP_LAT_A, _MAP_LAT_B = -5.76466, 358.188  # px_y = A * lat + B

# (country, lon, lat, label offset direction as (dx, dy) in inches)
_GLOBAL_HUBS = [
    ("USA", -122.33, 47.61, (-0.75, -0.05)),
    ("Canada", -79.38, 43.65, (0.15, -0.30)),
    ("Colombia", -74.07, 4.71, (0.20, 0.10)),
    ("Spain", -6.20, 36.46, (-0.55, 0.10)),
    ("UK", -0.13, 51.51, (-0.60, -0.05)),
    ("Netherlands", 5.18, 52.22, (-0.20, -0.35)),
    ("Belgium", 4.40, 51.22, (-0.75, 0.10)),
    ("Germany", 8.68, 50.11, (0.15, -0.20)),
    ("Switzerland", 8.54, 47.37, (0.45, 0.30)),
    ("Poland", 21.01, 52.23, (0.20, -0.30)),
    ("Saudi Arabia", 46.68, 24.71, (-0.55, 0.15)),
    ("UAE", 55.27, 25.20, (0.40, 0.35)),
    ("India", 77.03, 28.46, (0.20, -0.35)),
    ("Singapore", 103.82, 1.35, (0.20, 0.15)),
    ("Vietnam", 106.63, 10.82, (0.20, -0.20)),
    ("Australia", 144.96, -37.81, (0.20, 0.15)),
]


def build_global_presence_slide(prs: Presentation, style: SlideStyle,
                                slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, "Global Presence", size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    map_top = CONTENT_TOP
    map_h = 3.45
    map_w = map_h * (_MAP_PX_W / _MAP_PX_H)
    map_x = CONTENT_L + (CONTENT_W - map_w) / 2

    if _MAP_ASSET.exists():
        slide.shapes.add_picture(str(_MAP_ASSET), Inches(map_x), Inches(map_top),
                                  width=Inches(map_w), height=Inches(map_h))

        for name, lon, lat, (dx, dy) in _GLOBAL_HUBS:
            px = _MAP_LON_A * lon + _MAP_LON_B
            py = _MAP_LAT_A * lat + _MAP_LAT_B
            dot_x = map_x + (px / _MAP_PX_W) * map_w
            dot_y = map_top + (py / _MAP_PX_H) * map_h
            label_w = 1.1
            label_x = dot_x + dx - (label_w / 2 if dx == 0 else 0)
            _add_textbox(slide, label_x, dot_y + dy, label_w, 0.22,
                         name, 7, style.palette.primary, bold=True,
                         alignment=PP_ALIGN.CENTER, font_name=style.heading_font)
    else:
        add_world_map(slide, style.palette.primary)

    cycle = [style.palette.primary, style.palette.accent1,
             style.palette.secondary, style.palette.accent2]
    stats = [("6,500+", "Professionals"), ("16", "Countries"),
             ("25+", "Years"), ("$400M", "FY24 Revenue")]
    card_w = 2.1
    gap = 0.50
    total_w = len(stats) * card_w + (len(stats) - 1) * gap
    start_x = CONTENT_L + (CONTENT_W - total_w) / 2
    y = 5.60

    for i, (value, label) in enumerate(stats):
        x = start_x + i * (card_w + gap)
        color = cycle[i % len(cycle)]
        _add_card(slide, x, y, card_w, 1.15, style, accent_color=color)
        _add_textbox(slide, x + 0.1, y + 0.12, card_w - 0.2, 0.50,
                     value, 26, color, bold=True, alignment=PP_ALIGN.CENTER,
                     font_name=style.heading_font)
        _add_textbox(slide, x + 0.1, y + 0.65, card_w - 0.2, 0.35,
                     label, SZ_BODY, style.body_color, alignment=PP_ALIGN.CENTER,
                     font_name=style.body_font)


# ── CUSTOMER PORTFOLIO ───────────────────────────────────────

_PORTFOLIO_DIR = _LOGO_DIR / "customer_portfolio"
_PORTFOLIO_CATEGORIES = [
    ("retail_cpg", "Retail & CPG"),
    ("travel_hospitality", "Travel &\nHospitality"),
    ("banking_fintech_insurance", "Banking, Fintech\n& Insurance"),
    ("govt_public_utilities", "Govt., Public\n& Utilities"),
    ("media_telco_entertainment", "Media, Telco\n& Entertainment"),
    ("technology_isvs", "Technology\n& ISVs"),
    ("pharma_life_sciences", "Pharma &\nLife Sciences"),
]


def _load_portfolio_names() -> dict:
    names_path = _PORTFOLIO_DIR / "names.json"
    if not names_path.exists():
        return {}
    try:
        import json
        return json.loads(names_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize_company(name: str) -> str:
    n = name.lower().strip()
    if n.startswith("the "):
        n = n[4:]
    for suffix in (" inc.", " inc", " corp.", " corp", " corporation", " company",
                   " co.", " co", " ltd.", " ltd", " llc", " group", " n.v.", " nv"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n.strip()


def _load_portfolio_logos(exclude_customer: str | None = None) -> list[tuple[str, list]]:
    """[(display_label, [logo_path, ...]), ...] for categories with assets on disk.
    Excludes any logo whose known name matches exclude_customer, so a deck
    pitched to a company that happens to also be an extracted logo (e.g. a
    proposal for Disney) doesn't show that company its own logo back."""
    names_by_category = _load_portfolio_names()
    excl = _normalize_company(exclude_customer) if exclude_customer else None

    result = []
    for slug, label in _PORTFOLIO_CATEGORIES:
        folder = _PORTFOLIO_DIR / slug
        if not folder.exists():
            continue
        files = sorted(folder.glob("*.png"))
        if excl:
            names = names_by_category.get(slug, [])
            kept = []
            for i, f in enumerate(files):
                norm = _normalize_company(names[i]) if i < len(names) else ""
                is_match = norm and (
                    norm == excl or
                    (len(norm) >= 4 and len(excl) >= 4 and (norm in excl or excl in norm))
                )
                if is_match:
                    continue
                kept.append(f)
            files = kept
        if files:
            result.append((label, files))
    return result


def has_customer_portfolio_logos() -> bool:
    """Whether any approved client-logo assets exist to render this slide."""
    return bool(_load_portfolio_logos())


def build_customer_portfolio_slide(prs: Presentation, style: SlideStyle,
                                   slide_number: int = 0,
                                   customer_name: str | None = None) -> None:
    """Logo wall of real Xebia clients grouped by industry, sourced from
    xebia_design_system/assets/logos/customer_portfolio/. Skipped
    automatically when that directory is empty (no approved logo set)."""
    columns = _load_portfolio_logos(exclude_customer=customer_name)
    if not columns:
        return

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, "Xebia Customer Portfolio", size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    from PIL import Image

    num_cols = len(columns)
    gap_x = 0.15
    col_w = (CONTENT_W - (num_cols - 1) * gap_x) / num_cols
    header_h = 0.50
    stack_top = CONTENT_TOP + header_h
    available_h = CONTENT_H - header_h - 0.15
    gap_y = 0.05

    for i, (label, paths) in enumerate(columns):
        x = CONTENT_L + i * (col_w + gap_x)

        _add_textbox(slide, x, CONTENT_TOP, col_w, header_h,
                     label, 10, style.palette.primary, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        n = len(paths)
        logo_h = max(0.15, min(0.32, (available_h - (n - 1) * gap_y) / n))
        stack_h = n * logo_h + (n - 1) * gap_y
        y = stack_top + max(0.0, (available_h - stack_h) / 2)

        for path in paths:
            try:
                with Image.open(path) as im:
                    aspect = im.width / im.height
            except Exception:
                aspect = 2.5

            w, h = logo_h * aspect, logo_h
            if w > col_w - 0.10:
                w = col_w - 0.10
                h = w / aspect

            try:
                slide.shapes.add_picture(str(path), Inches(x + (col_w - w) / 2),
                                          Inches(y + (logo_h - h) / 2),
                                          width=Inches(w), height=Inches(h))
            except Exception:
                pass

            y += logo_h + gap_y


# ── XEBIA CAPABILITIES ───────────────────────────────────────

def build_xebia_capabilities_slide(prs: Presentation, style: SlideStyle,
                                   slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, "Why Xebia", size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    capabilities = [
        ("Data & AI", "End-to-end data engineering, ML/AI, and analytics solutions"),
        ("Cloud", "Multi-cloud architecture, migration, and managed services"),
        ("Software Engineering", "Full-stack development, microservices, DevOps"),
        ("Agile & Quality", "Agile coaching, testing strategy, quality engineering"),
        ("Low Code", "Rapid application development with enterprise platforms"),
        ("Academy", "Certified training programs for upskilling teams"),
    ]

    cycle = [style.palette.primary, style.palette.accent1, style.palette.secondary,
             style.palette.accent2, style.palette.accent3, style.palette.accent1]

    cols = 3
    gap_x, gap_y = 0.25, 0.20
    card_w = (CONTENT_W - (cols - 1) * gap_x) / cols
    card_h = 2.0

    for i, (cap_name, cap_desc) in enumerate(capabilities):
        col, row = i % cols, i // cols
        x = CONTENT_L + col * (card_w + gap_x)
        y = CONTENT_TOP + 0.1 + row * (card_h + gap_y)
        color = cycle[i % len(cycle)]

        _add_card(slide, x, y, card_w, card_h, style, accent_color=color)

        icon_size = 0.42
        _add_shape(slide, MSO_SHAPE.OVAL, x + 0.18, y + 0.20,
                   icon_size, icon_size, fill_color=color)
        _add_textbox(slide, x + 0.18, y + 0.25, icon_size, icon_size - 0.08,
                     cap_name[0], 14, style.palette.text_light, bold=True,
                     alignment=PP_ALIGN.CENTER, font_name=style.heading_font)

        _add_textbox(slide, x + 0.72, y + 0.22, card_w - 0.90, 0.35,
                     cap_name, 13, style.title_color, bold=True,
                     font_name=style.heading_font)
        _add_textbox(slide, x + 0.18, y + 0.78, card_w - 0.36, 1.0,
                     cap_desc, SZ_SMALL, style.body_color, font_name=style.body_font)


# ── IMAGE PLACEHOLDER ─────────────────────────────────────────

def build_image_placeholder_slide(prs: Presentation, style: SlideStyle, title: str,
                                  placeholder_text: str = "Architecture Diagram",
                                  caption: str = "", slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE,
               CONTENT_L + 0.2, CONTENT_TOP + 0.2,
               CONTENT_W - 0.4, 3.8,
               fill_color=style.card_bg,
               line_color=style.border_color, line_width=1.5)
    _add_textbox(slide, 3.0, 3.5, 7.0, 0.50,
                 f"[ {placeholder_text} ]", 18, style.border_color,
                 alignment=PP_ALIGN.CENTER, font_name=style.heading_font)
    _add_textbox(slide, 3.0, 4.0, 7.0, 0.35,
                 "Insert diagram or image here", 11, style.border_color,
                 alignment=PP_ALIGN.CENTER, font_name=style.body_font)
    if caption:
        _add_textbox(slide, CONTENT_L, CONTENT_BOTTOM - 0.5, CONTENT_W, 0.35,
                     caption, SZ_SMALL, style.body_color,
                     alignment=PP_ALIGN.CENTER, font_name=style.body_font)


# ── ARCHITECTURE DIAGRAM (new engine) ─────────────────────────

def build_architecture_diagram_slide(prs: Presentation, style: SlideStyle,
                                     title: str, diagram: dict = None,
                                     slide_number: int = 0) -> None:
    """Render a multi-zone architecture diagram using the new diagram engine."""
    from generation.diagrams.architecture_renderer import ArchitectureDiagramRenderer

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    if not diagram:
        diagram = {}

    renderer = ArchitectureDiagramRenderer(slide, style, diagram)
    renderer.render()


# ── SERVICE GRID (new engine) ─────────────────────────────────

def build_service_grid_slide(prs: Presentation, style: SlideStyle,
                             title: str, diagram: dict = None,
                             slide_number: int = 0) -> None:
    """Render a categorized service/technology grid using the new diagram engine."""
    from generation.diagrams.service_grid_renderer import ServiceGridRenderer

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    if not diagram:
        diagram = {}

    renderer = ServiceGridRenderer(slide, style, diagram)
    renderer.render()


# ── MIGRATION FLOW (new engine) ────────────────────────────────

def build_migration_flow_slide(prs: Presentation, style: SlideStyle,
                               title: str, diagram: dict = None,
                               slide_number: int = 0) -> None:
    """Render a multi-zone left-to-right architecture flow diagram."""
    from generation.diagrams.migration_flow_renderer import MigrationFlowRenderer

    slide = _add_slide(prs, "Content_Basic")
    _apply_composition(slide, style)
    _fill_ph(slide, 0, title, size=SZ_TITLE, color=style.title_color,
             bold=True, font_name=style.heading_font)
    _clear_body_ph(slide)

    if not diagram:
        diagram = {}

    renderer = MigrationFlowRenderer(slide, style, diagram)
    renderer.render()


# ── LAYOUT DISPATCHER ─────────────────────────────────────────

LAYOUT_BUILDERS = {
    "content": build_content_slide,
    "two_column": build_two_column_slide,
    "icon_grid": build_icon_grid_slide,
    "process_flow": build_process_flow_slide,
    "comparison_table": build_comparison_table_slide,
    "stats_highlight": build_stats_highlight_slide,
    "key_value": build_key_value_slide,
    "image_placeholder": build_image_placeholder_slide,
    "architecture": build_architecture_slide,
    "technology": build_technology_slide,
    "challenges": build_challenges_slide,
    "timeline": build_timeline_slide,
    "team": build_team_slide,
    "architecture_diagram": build_architecture_diagram_slide,
    "service_grid": build_service_grid_slide,
    "migration_flow": build_migration_flow_slide,
}


def build_slide_by_layout(prs: Presentation, layout: str, style: SlideStyle,
                          data: dict, slide_number: int = 0) -> None:
    builder = LAYOUT_BUILDERS.get(layout)

    if builder is None:
        build_content_slide(prs, style, title=data.get("title", ""),
                            body_text=data.get("body", ""),
                            bullets=data.get("bullets", []),
                            slide_number=slide_number)
        return

    if layout == "content":
        builder(prs, style, title=data.get("title", ""), body_text=data.get("body", ""),
                bullets=data.get("bullets", []), slide_number=slide_number)
    elif layout == "two_column":
        left = data.get("left", {})
        right = data.get("right", {})
        builder(prs, style, title=data.get("title", ""), left_title=left.get("title", ""),
                left_bullets=left.get("bullets", []), right_title=right.get("title", ""),
                right_bullets=right.get("bullets", []), slide_number=slide_number)
    elif layout == "icon_grid":
        builder(prs, style, title=data.get("title", ""), items=data.get("items", []),
                slide_number=slide_number)
    elif layout == "process_flow":
        builder(prs, style, title=data.get("title", ""), steps=data.get("steps", []),
                slide_number=slide_number)
    elif layout == "comparison_table":
        builder(prs, style, title=data.get("title", ""), headers=data.get("headers", []),
                rows=data.get("rows", []), caption=data.get("caption", ""),
                slide_number=slide_number)
    elif layout == "stats_highlight":
        builder(prs, style, title=data.get("title", ""), stats=data.get("stats", []),
                slide_number=slide_number)
    elif layout == "key_value":
        builder(prs, style, title=data.get("title", ""), pairs=data.get("pairs", []),
                slide_number=slide_number)
    elif layout == "image_placeholder":
        builder(prs, style, title=data.get("title", ""),
                placeholder_text=data.get("placeholder_text", "Diagram"),
                caption=data.get("caption", ""), slide_number=slide_number)
    elif layout == "architecture":
        builder(prs, style, title=data.get("title", ""), layers=data.get("layers", []),
                slide_number=slide_number)
    elif layout == "technology":
        builder(prs, style, title=data.get("title", ""),
                technologies=data.get("technologies", []), slide_number=slide_number)
    elif layout == "challenges":
        builder(prs, style, title=data.get("title", ""),
                challenges=data.get("challenges", []), slide_number=slide_number)
    elif layout == "timeline":
        builder(prs, style, title=data.get("title", ""), phases=data.get("phases", []),
                slide_number=slide_number)
    elif layout == "team":
        builder(prs, style, title=data.get("title", ""),
                team_members=data.get("members", []), slide_number=slide_number)
    elif layout == "architecture_diagram":
        builder(prs, style, title=data.get("title", ""),
                diagram=data.get("diagram", {}), slide_number=slide_number)
    elif layout == "service_grid":
        builder(prs, style, title=data.get("title", ""),
                diagram=data.get("diagram", {}), slide_number=slide_number)
    elif layout == "migration_flow":
        builder(prs, style, title=data.get("title", ""),
                diagram=data.get("diagram", {}), slide_number=slide_number)
