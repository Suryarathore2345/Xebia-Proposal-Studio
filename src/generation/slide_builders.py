"""Xebia Proposal Slide Builders — Template-Based Design.

Uses the official Xebia PPTX template extracted from reference presentations.
The template contains 30 pre-designed layouts with proper branding, backgrounds,
decorative elements, and placeholder positioning.

Canvas: 13.33in x 7.50in (widescreen 16:9)
Primary: #6C1D5F (deep purple)
Font: Arial
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

from design_system.brand import colors, typography, spacing, theme

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "xebia_retail.pptx"

# ============================================================
# HELPERS
# ============================================================

def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _c(key: str) -> RGBColor:
    c = colors()
    lookup = {
        "purple": c["primary"]["purple"],
        "purple_dark": c["primary"]["purple_dark"],
        "purple_light": c["primary"]["purple_light"],
        "purple_muted": c["primary"]["purple_muted"],
        "purple_soft": c["primary"]["purple_soft"],
        "purple_bg": c["primary"]["purple_bg"],
        "white": c["neutral"]["white"],
        "off_white": c["neutral"]["off_white"],
        "light_gray": c["neutral"]["light_gray"],
        "mid_gray": c["neutral"]["mid_gray"],
        "dark_gray": c["neutral"]["dark_gray"],
        "charcoal": c["neutral"]["charcoal"],
        "black": c["neutral"]["black"],
        "teal": c["accent"]["teal"],
        "blue": c["accent"]["blue"],
        "light_blue": c["accent"]["light_blue"],
        "green": c["accent"]["green"],
        "orange": c["accent"]["orange"],
        "gold": c["accent"]["gold"],
        "red": c["accent"]["red"],
    }
    return _rgb(lookup.get(key, c["primary"]["purple"]))


ACCENT_COLORS = ["purple", "teal", "blue", "green", "orange", "light_blue"]


def create_presentation() -> Presentation:
    """Create a Presentation from the Xebia template."""
    if TEMPLATE_PATH.exists():
        return Presentation(str(TEMPLATE_PATH))
    return Presentation()


def _get_layout(prs: Presentation, name: str):
    """Find a slide layout by name, fallback to first blank-ish layout."""
    for layout in prs.slide_layouts:
        if layout.name == name:
            return layout
    for layout in prs.slide_layouts:
        if "Content_Basic" in layout.name:
            return layout
    return prs.slide_layouts[0]


def _set_text(tf, text: str, size: float, color: RGBColor,
              bold: bool = False, alignment=None, font_name: str = "Arial"):
    tf.word_wrap = True
    for para in tf.paragraphs:
        para.text = ""
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    if alignment:
        p.alignment = alignment


def _add_paragraph(tf, text: str, size: float, color: RGBColor,
                   bold: bool = False, alignment=None, space_before: float = 0,
                   font_name: str = "Arial"):
    p = tf.add_paragraph()
    p.text = str(text)
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    if alignment:
        p.alignment = alignment
    if space_before:
        p.space_before = Pt(space_before)
    return p


def _add_shape(slide, shape_type, left, top, width, height,
               fill_color=None, line_color=None, line_width=None):
    shape = slide.shapes.add_shape(
        shape_type, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        if line_width:
            shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def _add_textbox(slide, left, top, width, height, text, size, color,
                 bold=False, alignment=None):
    tx = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = tx.text_frame
    tf.word_wrap = True
    _set_text(tf, text, size, color, bold=bold, alignment=alignment)
    return tx


def _get_ph(slide, idx: int):
    """Get placeholder by index, return None if not found."""
    try:
        return slide.placeholders[idx]
    except (KeyError, IndexError):
        return None


def _get_picture_placeholders(slide):
    """Find PICTURE placeholder indices on a slide."""
    from pptx.oxml.ns import qn
    pic_indices = []
    spTree = slide.shapes._spTree
    for sp in spTree.iterchildren(qn('p:sp')):
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
    """Remove PICTURE placeholders so empty 'add a photo' boxes don't appear."""
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
    """Insert an image into the first PICTURE placeholder on the slide."""
    pic_indices = _get_picture_placeholders(slide)
    if not pic_indices or not image_path:
        return False
    try:
        ph = slide.placeholders[pic_indices[0]]
        ph.insert_picture(image_path)
        for idx in pic_indices[1:]:
            _remove_single_picture_placeholder(slide, idx)
        return True
    except Exception:
        _remove_picture_placeholders(slide)
        return False


def _remove_single_picture_placeholder(slide, idx: int):
    """Remove a specific PICTURE placeholder by index."""
    from pptx.oxml.ns import qn
    spTree = slide.shapes._spTree
    for sp in list(spTree.iterchildren(qn('p:sp'))):
        nvSpPr = sp.find(qn('p:nvSpPr'))
        if nvSpPr is not None:
            nvPr = nvSpPr.find(qn('p:nvPr'))
            if nvPr is not None:
                ph = nvPr.find(qn('p:ph'))
                if ph is not None and ph.get('type') == 'pic':
                    ph_idx = ph.get('idx')
                    if ph_idx is not None and int(ph_idx) == idx:
                        spTree.remove(sp)
                        return


def _add_slide(prs: Presentation, layout_name: str, image_path: str = None):
    """Add a slide from a named layout. If image_path is provided, insert it
    into the first PICTURE placeholder; otherwise remove all picture placeholders."""
    layout = _get_layout(prs, layout_name)
    slide = prs.slides.add_slide(layout)
    if image_path:
        if not _insert_image_into_placeholder(slide, image_path):
            _remove_picture_placeholders(slide)
    else:
        _remove_picture_placeholders(slide)
    return slide


def _fill_placeholder(slide, idx: int, text: str, size: float = None,
                      color: RGBColor = None, bold: bool = None,
                      alignment=None, font_name: str = "Arial"):
    """Fill a placeholder by index, with optional formatting overrides."""
    try:
        ph = slide.placeholders[idx]
    except (KeyError, IndexError):
        return None
    tf = ph.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(text)
    if size:
        p.font.size = Pt(size)
    if color:
        p.font.color.rgb = color
    if bold is not None:
        p.font.bold = bold
    if font_name:
        p.font.name = font_name
    if alignment:
        p.alignment = alignment
    return ph


def _fill_placeholder_multi(slide, idx: int, lines: list[str],
                            size: float = 12, color: RGBColor = None,
                            bold: bool = False, bullet_char: str = "",
                            font_name: str = "Arial"):
    """Fill a placeholder with multiple lines/paragraphs."""
    try:
        ph = slide.placeholders[idx]
    except (KeyError, IndexError):
        return None
    tf = ph.text_frame
    tf.word_wrap = True
    color = color or _c("charcoal")
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        prefix = f"{bullet_char} " if bullet_char else ""
        p.text = f"{prefix}{line}"
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.bold = bold
        p.font.name = font_name
        p.space_before = Pt(4) if i > 0 else Pt(0)
    return ph


# ============================================================
# COVER SLIDE — Main-cover_light
# ============================================================

def build_cover_slide(prs: Presentation, title: str, subtitle: str = "",
                      customer: str = "", date: str = "",
                      image_path: str = None) -> None:
    slide = _add_slide(prs, "Main-cover_dark", image_path=image_path)

    _fill_placeholder(slide, 0, title, size=28, color=_c("white"), bold=True)

    sub_parts = []
    if subtitle:
        sub_parts.append(subtitle)
    if customer:
        sub_parts.append(f"Prepared for {customer}")
    if date:
        sub_parts.append(date)
    if sub_parts:
        _fill_placeholder(slide, 1, " | ".join(sub_parts), size=14, color=_c("white"))


# ============================================================
# TABLE OF CONTENTS — Table of contents layout
# ============================================================

def build_toc_slide(prs: Presentation, items: list[str], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Table of contents")

    mid = len(items) // 2 + len(items) % 2
    col1 = items[:mid]
    col2 = items[mid:]

    col1_text = [f"{i+1:02d}  {item}" for i, item in enumerate(col1)]
    col2_text = [f"{mid+i+1:02d}  {item}" for i, item in enumerate(col2)]

    _fill_placeholder_multi(slide, 1, col1_text, size=13, color=_c("charcoal"))
    if col2_text:
        _fill_placeholder_multi(slide, 11, col2_text, size=13, color=_c("charcoal"))


# ============================================================
# SECTION DIVIDER — Chapter_dark
# ============================================================

def build_section_divider(prs: Presentation, title: str, slide_number: int = 0,
                          image_path: str = None) -> None:
    slide = _add_slide(prs, "Chapter_dark", image_path=image_path)

    _fill_placeholder(slide, 0, title, size=28, color=_c("white"), bold=True)


# ============================================================
# EXECUTIVE SUMMARY — Content_Basic with custom formatting
# ============================================================

def build_executive_summary_slide(prs: Presentation, title: str,
                                  summary_text: str = "", key_points: list[str] = None,
                                  slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)

    body_ph = _get_ph(slide, 1)
    if body_ph:
        tf = body_ph.text_frame
        tf.word_wrap = True
        if summary_text:
            p = tf.paragraphs[0]
            p.text = summary_text
            p.font.size = Pt(12)
            p.font.color.rgb = _c("charcoal")
            p.font.name = "Arial"
            p.space_after = Pt(12)

        if key_points:
            p_header = tf.add_paragraph()
            p_header.text = "Key Highlights"
            p_header.font.size = Pt(14)
            p_header.font.color.rgb = _c("purple")
            p_header.font.bold = True
            p_header.font.name = "Arial"
            p_header.space_before = Pt(12)

            for point in key_points[:6]:
                p = tf.add_paragraph()
                p.text = f"•  {point}"
                p.font.size = Pt(11)
                p.font.color.rgb = _c("charcoal")
                p.font.name = "Arial"
                p.space_before = Pt(4)


# ============================================================
# CONTENT SLIDE — Content_Basic
# ============================================================

def build_content_slide(prs: Presentation, title: str,
                        body_text: str = "", bullets: list[str] = None,
                        slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)

    body_ph = _get_ph(slide, 1)
    if body_ph:
        tf = body_ph.text_frame
        tf.word_wrap = True

        first_para = True
        if body_text:
            p = tf.paragraphs[0]
            p.text = body_text
            p.font.size = Pt(12)
            p.font.color.rgb = _c("charcoal")
            p.font.name = "Arial"
            first_para = False

        if bullets:
            for bullet in bullets:
                if first_para:
                    p = tf.paragraphs[0]
                    first_para = False
                else:
                    p = tf.add_paragraph()
                p.text = f"•  {bullet}"
                p.font.size = Pt(11)
                p.font.color.rgb = _c("charcoal")
                p.font.name = "Arial"
                p.space_before = Pt(4)


# ============================================================
# TWO COLUMN — Content_2 Columns
# ============================================================

def build_two_column_slide(prs: Presentation, title: str,
                           left_title: str = "", left_bullets: list[str] = None,
                           right_title: str = "", right_bullets: list[str] = None,
                           slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_2 Columns")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)

    if left_title:
        _fill_placeholder(slide, 11, left_title, size=14, color=_c("purple"), bold=True)
    if left_bullets:
        _fill_placeholder_multi(slide, 1, left_bullets, size=11, bullet_char="•")

    if right_title:
        _fill_placeholder(slide, 14, right_title, size=14, color=_c("purple"), bold=True)
    if right_bullets:
        _fill_placeholder_multi(slide, 13, right_bullets, size=11, bullet_char="•")


# ============================================================
# ICON GRID — Content_3 Columns or Content_4 Columns
# ============================================================

def build_icon_grid_slide(prs: Presentation, title: str,
                          items: list[dict], slide_number: int = 0) -> None:
    num = len(items)
    if num <= 3:
        slide = _add_slide(prs, "Content_3 Columns")
        _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
        col_data = [(11, 1, 12), (17, 16, 18), (14, 13, 15)]
        for i, item in enumerate(items[:3]):
            header_idx, body_idx, pic_idx = col_data[i]
            _fill_placeholder(slide, header_idx, item.get("label", ""), size=14, color=_c("purple"), bold=True)
            _fill_placeholder(slide, body_idx, item.get("description", ""), size=11, color=_c("charcoal"))
    else:
        slide = _add_slide(prs, "Content_Basic")
        _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)

        body_ph = _get_ph(slide, 1)
        if body_ph:
            tf = body_ph.text_frame
            tf.word_wrap = True
            for i, item in enumerate(items[:8]):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                label = item.get("label", "")
                desc = item.get("description", "")
                run = p.add_run()
                run.text = f"{label}: "
                run.font.size = Pt(12)
                run.font.color.rgb = _c("purple")
                run.font.bold = True
                run.font.name = "Arial"
                run2 = p.add_run()
                run2.text = desc
                run2.font.size = Pt(11)
                run2.font.color.rgb = _c("charcoal")
                run2.font.name = "Arial"
                p.space_before = Pt(6) if i > 0 else Pt(0)


# ============================================================
# PROCESS FLOW — Content_Basic + custom shapes
# ============================================================

def build_process_flow_slide(prs: Presentation, title: str,
                             steps: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)

    # Clear body placeholder
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    normalized = []
    for s in steps:
        if isinstance(s, str):
            normalized.append({"label": s, "description": ""})
        else:
            normalized.append(s)

    num_steps = min(len(normalized), 6)
    total_w = 11.5
    gap = 0.3
    step_w = (total_w - (num_steps - 1) * gap) / num_steps
    start_x = 0.8
    bar_y = 2.8

    _add_shape(slide, MSO_SHAPE.RECTANGLE, start_x, bar_y, total_w, 0.03, fill_color=_c("light_gray"))

    for i, step in enumerate(normalized[:num_steps]):
        x = start_x + i * (step_w + gap)
        color = _c(ACCENT_COLORS[i % len(ACCENT_COLORS)])

        circle_size = 0.55
        cx = x + (step_w - circle_size) / 2
        _add_shape(slide, MSO_SHAPE.OVAL, cx, 2.55, circle_size, circle_size, fill_color=color)
        _add_textbox(slide, cx, 2.6, circle_size, circle_size - 0.1, str(i + 1), 16, _c("white"), bold=True, alignment=PP_ALIGN.CENTER)

        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 3.4, step_w, 3.0, fill_color=_c("white"))
        card.line.color.rgb = _c("light_gray")
        card.line.width = Pt(0.75)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, x, 3.4, step_w, 0.06, fill_color=color)

        _add_textbox(slide, x + 0.1, 3.6, step_w - 0.2, 0.5, step.get("label", ""), 12, _c("black"), bold=True, alignment=PP_ALIGN.CENTER)

        desc = step.get("description", "")
        if desc:
            _add_textbox(slide, x + 0.1, 4.2, step_w - 0.2, 2.0, desc, 10, _c("dark_gray"), alignment=PP_ALIGN.CENTER)

        if i < num_steps - 1:
            ax = x + step_w + 0.02
            _add_shape(slide, MSO_SHAPE.RIGHT_ARROW, ax, 2.65, gap - 0.04, 0.3, fill_color=_c("purple_muted"))


# ============================================================
# COMPARISON TABLE
# ============================================================

def build_comparison_table_slide(prs: Presentation, title: str,
                                 headers: list[str], rows: list[list[str]],
                                 slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    num_cols = len(headers)
    num_rows = min(len(rows) + 1, 12)
    col_width = 11.8 / num_cols
    row_height = min(0.5, 4.5 / num_rows)

    table_shape = slide.shapes.add_table(num_rows, num_cols, Inches(0.6), Inches(2.2), Inches(11.8), Inches(row_height * num_rows))
    table = table_shape.table

    for i in range(num_cols):
        table.columns[i].width = Inches(col_width)

    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = _c("purple")
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(11)
            p.font.color.rgb = _c("white")
            p.font.bold = True
            p.font.name = "Arial"
            p.alignment = PP_ALIGN.CENTER

    for r_idx, row in enumerate(rows[:num_rows - 1]):
        for c_idx, val in enumerate(row[:num_cols]):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = str(val)
            bg = _c("off_white") if r_idx % 2 == 0 else _c("white")
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10)
                p.font.color.rgb = _c("charcoal")
                p.font.name = "Arial"


# ============================================================
# STATS / KPI HIGHLIGHT
# ============================================================

def build_stats_highlight_slide(prs: Presentation, title: str,
                                stats: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    num_stats = min(len(stats), 4)
    card_w = (11.8 - (num_stats - 1) * 0.4) / num_stats
    card_h = 4.2
    card_y = 2.2

    for i, stat in enumerate(stats[:4]):
        x = 0.6 + i * (card_w + 0.4)
        color = _c(ACCENT_COLORS[i % len(ACCENT_COLORS)])

        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, card_y, card_w, card_h, fill_color=_c("white"))
        card.line.color.rgb = _c("light_gray")
        card.line.width = Pt(0.75)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, x, card_y, card_w, 0.08, fill_color=color)
        _add_shape(slide, MSO_SHAPE.OVAL, x + (card_w - 0.6) / 2, card_y + 0.4, 0.6, 0.6, fill_color=color)

        _add_textbox(slide, x + 0.15, card_y + 1.2, card_w - 0.3, 1.0, str(stat.get("value", "")), 42, color, bold=True, alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, x + 0.15, card_y + 2.2, card_w - 0.3, 0.5, stat.get("label", ""), 13, _c("black"), bold=True, alignment=PP_ALIGN.CENTER)

        sublabel = stat.get("description", "")
        if sublabel:
            _add_textbox(slide, x + 0.15, card_y + 2.7, card_w - 0.3, 1.2, sublabel, 10, _c("dark_gray"), alignment=PP_ALIGN.CENTER)


# ============================================================
# KEY-VALUE PAIRS
# ============================================================

def build_key_value_slide(prs: Presentation, title: str,
                          pairs: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    start_y = 2.2
    row_h = 0.5
    key_w = 3.5

    for i, pair in enumerate(pairs[:10]):
        y = start_y + i * row_h
        if y > 6.5:
            break
        bg_color = _c("off_white") if i % 2 == 0 else _c("white")
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0.6, y, 11.8, row_h, fill_color=bg_color)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0.6, y, 0.06, row_h, fill_color=_c("purple"))
        _add_textbox(slide, 0.85, y + 0.07, key_w, row_h - 0.14, str(pair.get("key", "")), 12, _c("purple"), bold=True)
        _add_textbox(slide, 0.85 + key_w + 0.3, y + 0.07, 8.0, row_h - 0.14, str(pair.get("value", "")), 12, _c("charcoal"))


# ============================================================
# TIMELINE
# ============================================================

def build_timeline_slide(prs: Presentation, title: str,
                         phases: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    num_phases = min(len(phases), 6)
    bar_w = 11.5 / num_phases
    bar_h = 0.7
    bar_y = 2.4

    _add_shape(slide, MSO_SHAPE.RECTANGLE, 0.6, bar_y + bar_h / 2 - 0.02, 11.5, 0.04, fill_color=_c("light_gray"))

    for i, phase in enumerate(phases[:num_phases]):
        x = 0.6 + i * bar_w
        color = _c(ACCENT_COLORS[i % len(ACCENT_COLORS)])

        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.05, bar_y, bar_w - 0.1, bar_h, fill_color=color)
        _add_textbox(slide, x + 0.1, bar_y + 0.1, bar_w - 0.2, 0.5, phase.get("name", ""), 11, _c("white"), bold=True, alignment=PP_ALIGN.CENTER)

        duration = phase.get("duration", "")
        if duration:
            _add_textbox(slide, x + 0.05, bar_y + bar_h + 0.15, bar_w - 0.1, 0.3, duration, 10, _c("purple"), bold=True, alignment=PP_ALIGN.CENTER)

        desc = phase.get("description", "")
        if desc:
            card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.05, bar_y + bar_h + 0.5, bar_w - 0.1, 2.8, fill_color=_c("off_white"))
            card.line.color.rgb = _c("light_gray")
            card.line.width = Pt(0.5)
            _add_shape(slide, MSO_SHAPE.RECTANGLE, x + 0.05, bar_y + bar_h + 0.5, bar_w - 0.1, 0.05, fill_color=color)
            _add_textbox(slide, x + 0.15, bar_y + bar_h + 0.65, bar_w - 0.3, 2.5, desc, 10, _c("charcoal"))


# ============================================================
# TEAM STRUCTURE
# ============================================================

def build_team_slide(prs: Presentation, title: str,
                     team_members: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    num_members = min(len(team_members), 8)
    cols = min(num_members, 4)
    card_w = (11.8 - (cols - 1) * 0.25) / cols
    card_h = 2.2

    for i, member in enumerate(team_members[:8]):
        col = i % cols
        row = i // cols
        x = 0.6 + col * (card_w + 0.25)
        y = 2.2 + row * (card_h + 0.2)
        color = _c(ACCENT_COLORS[i % len(ACCENT_COLORS)])

        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h, fill_color=_c("white"))
        card.line.color.rgb = _c("light_gray")
        card.line.width = Pt(0.75)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, card_w, 0.06, fill_color=color)

        avatar_size = 0.55
        _add_shape(slide, MSO_SHAPE.OVAL, x + (card_w - avatar_size) / 2, y + 0.2, avatar_size, avatar_size, fill_color=color)

        name = member.get("name", "TBD")
        initials = "".join(w[0].upper() for w in name.split()[:2] if w)
        _add_textbox(slide, x + (card_w - avatar_size) / 2, y + 0.28, avatar_size, avatar_size - 0.15, initials, 14, _c("white"), bold=True, alignment=PP_ALIGN.CENTER)

        _add_textbox(slide, x + 0.1, y + 0.9, card_w - 0.2, 0.35, name, 11, _c("black"), bold=True, alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, x + 0.1, y + 1.25, card_w - 0.2, 0.3, member.get("role", ""), 10, _c("purple"), alignment=PP_ALIGN.CENTER)

        expertise = member.get("expertise", "")
        if expertise:
            _add_textbox(slide, x + 0.1, y + 1.55, card_w - 0.2, 0.55, expertise, 9, _c("dark_gray"), alignment=PP_ALIGN.CENTER)


# ============================================================
# COMMERCIALS TABLE
# ============================================================

def build_commercials_slide(prs: Presentation, title: str,
                            rows: list[dict] = None, total: str = "",
                            assumptions: list[str] = None,
                            slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    if rows:
        headers = ["Role / Item", "Hours", "Rate ($/hr)", "Cost ($)"]
        num_rows = len(rows) + 2
        table_shape = slide.shapes.add_table(num_rows, 4, Inches(0.6), Inches(2.2), Inches(8.0), Inches(0.45 * num_rows))
        table = table_shape.table
        table.columns[0].width = Inches(3.5)
        table.columns[1].width = Inches(1.5)
        table.columns[2].width = Inches(1.5)
        table.columns[3].width = Inches(1.5)

        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = _c("purple")
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = _c("white")
                p.font.bold = True
                p.font.name = "Arial"

        for r_idx, row in enumerate(rows):
            for c_idx, key in enumerate(["item", "hours", "rate", "cost"]):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = str(row.get(key, ""))
                bg = _c("off_white") if r_idx % 2 == 0 else _c("white")
                cell.fill.solid()
                cell.fill.fore_color.rgb = bg
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(10)
                    p.font.color.rgb = _c("charcoal")
                    p.font.name = "Arial"

        total_row = num_rows - 1
        for c_idx in range(4):
            cell = table.cell(total_row, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = _c("purple_bg")
            if c_idx == 0:
                cell.text = "TOTAL"
            elif c_idx == 3:
                cell.text = str(total)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.bold = True
                p.font.color.rgb = _c("purple")
                p.font.name = "Arial"

    if assumptions:
        _add_textbox(slide, 9.0, 2.2, 3.5, 0.4, "Assumptions", 13, _c("purple"), bold=True)
        for i, assumption in enumerate(assumptions[:6]):
            y = 2.7 + i * 0.5
            _add_shape(slide, MSO_SHAPE.OVAL, 9.0, y + 0.05, 0.12, 0.12, fill_color=_c("purple"))
            _add_textbox(slide, 9.25, y, 3.3, 0.45, assumption, 9, _c("dark_gray"))


# ============================================================
# CLOSING SLIDE — End-cover_dark
# ============================================================

def build_closing_slide(prs: Presentation, title: str = "Thank You",
                        contact_name: str = "", contact_email: str = "",
                        contact_phone: str = "", slide_number: int = 0,
                        image_path: str = None) -> None:
    slide = _add_slide(prs, "End-cover_dark", image_path=image_path)

    _fill_placeholder(slide, 0, title, size=36, color=_c("white"), bold=True)

    contact_parts = []
    if contact_name:
        contact_parts.append(contact_name)
    if contact_email:
        contact_parts.append(contact_email)
    if contact_phone:
        contact_parts.append(contact_phone)
    if contact_parts:
        _fill_placeholder(slide, 1, "\n".join(contact_parts), size=14, color=_c("white"))


# ============================================================
# ARCHITECTURE DIAGRAM
# ============================================================

def build_architecture_slide(prs: Presentation, title: str,
                             layers: list[dict] = None,
                             slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    if not layers:
        layers = [
            {"name": "Source Systems", "components": ["Data Sources"], "color": "blue"},
            {"name": "Ingestion", "components": ["Data Ingestion"], "color": "teal"},
            {"name": "Processing", "components": ["Transformation"], "color": "purple"},
            {"name": "Storage", "components": ["Data Store"], "color": "green"},
            {"name": "Consumption", "components": ["Reporting & Analytics"], "color": "orange"},
        ]

    num_layers = min(len(layers), 7)
    diagram_x = 0.8
    diagram_w = 11.5
    layer_h = (4.5 - (num_layers - 1) * 0.15) / num_layers
    layer_h = min(layer_h, 1.0)
    start_y = 2.2
    arrow_gap = 0.15

    for i, layer in enumerate(layers[:num_layers]):
        y = start_y + i * (layer_h + arrow_gap)
        color_name = layer.get("color", ACCENT_COLORS[i % len(ACCENT_COLORS)])
        color = _c(color_name)

        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, diagram_x, y, diagram_w, layer_h, fill_color=_c("off_white"))

        label_w = 2.5
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, diagram_x, y, label_w, layer_h, fill_color=color)
        _add_textbox(slide, diagram_x + 0.15, y + (layer_h - 0.35) / 2, label_w - 0.3, 0.35, layer.get("name", ""), 11, _c("white"), bold=True)

        components = layer.get("components", [])
        if components:
            num_comp = min(len(components), 5)
            comp_area_x = diagram_x + label_w + 0.15
            comp_area_w = diagram_w - label_w - 0.3
            comp_w = (comp_area_w - (num_comp - 1) * 0.15) / num_comp
            comp_h = layer_h - 0.2

            for j, comp in enumerate(components[:num_comp]):
                cx = comp_area_x + j * (comp_w + 0.15)
                cy = y + 0.1
                comp_shape = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, comp_w, comp_h, fill_color=_c("white"))
                comp_shape.line.color.rgb = color
                comp_shape.line.width = Pt(1)
                _add_textbox(slide, cx + 0.05, cy + (comp_h - 0.3) / 2, comp_w - 0.1, 0.3, comp, 9, _c("charcoal"), alignment=PP_ALIGN.CENTER)

        if i < num_layers - 1:
            arrow_y = y + layer_h + 0.02
            arrow_x = diagram_x + diagram_w / 2 - 0.15
            _add_shape(slide, MSO_SHAPE.DOWN_ARROW, arrow_x, arrow_y, 0.3, arrow_gap - 0.04, fill_color=_c("purple_muted"))


# ============================================================
# IMAGE PLACEHOLDER
# ============================================================

def build_image_placeholder_slide(prs: Presentation, title: str,
                                  placeholder_text: str = "Architecture Diagram",
                                  caption: str = "", slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    box = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.8, 2.2, 11.2, 4.0, fill_color=_c("off_white"))
    box.line.color.rgb = _c("light_gray")
    box.line.width = Pt(1.5)

    _add_textbox(slide, 3.0, 3.5, 7.0, 0.6, f"[ {placeholder_text} ]", 18, _c("mid_gray"), alignment=PP_ALIGN.CENTER)
    _add_textbox(slide, 3.0, 4.1, 7.0, 0.4, "Insert diagram or image here", 11, _c("light_gray"), alignment=PP_ALIGN.CENTER)

    if caption:
        _add_textbox(slide, 0.8, 6.3, 11.2, 0.4, caption, 10, _c("dark_gray"), alignment=PP_ALIGN.CENTER)


# ============================================================
# TECHNOLOGY CARDS
# ============================================================

def build_technology_slide(prs: Presentation, title: str,
                           technologies: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    num_items = min(len(technologies), 6)
    cols = min(num_items, 3)
    card_w = (11.8 - (cols - 1) * 0.25) / cols
    card_h = 2.2

    for i, tech in enumerate(technologies[:6]):
        col = i % cols
        row = i // cols
        x = 0.6 + col * (card_w + 0.25)
        y = 2.2 + row * (card_h + 0.2)
        color = _c(ACCENT_COLORS[i % len(ACCENT_COLORS)])

        card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h, fill_color=_c("white"))
        card.line.color.rgb = _c("light_gray")
        card.line.width = Pt(0.75)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, 0.08, card_h, fill_color=color)

        category = tech.get("category", "Technology")
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.25, y + 0.15, 1.8, 0.3, fill_color=color)
        _add_textbox(slide, x + 0.3, y + 0.17, 1.7, 0.25, category.upper(), 8, _c("white"), bold=True, alignment=PP_ALIGN.CENTER)

        _add_textbox(slide, x + 0.25, y + 0.6, card_w - 0.5, 0.4, tech.get("name", ""), 14, _c("black"), bold=True)

        desc = tech.get("description", "")
        if desc:
            _add_textbox(slide, x + 0.25, y + 1.05, card_w - 0.5, 1.0, desc, 10, _c("dark_gray"))


# ============================================================
# CHALLENGES & SOLUTIONS
# ============================================================

def build_challenges_slide(prs: Presentation, title: str,
                           challenges: list[dict], slide_number: int = 0) -> None:
    slide = _add_slide(prs, "Content_Basic")

    _fill_placeholder(slide, 0, title, size=24, color=_c("black"), bold=True)
    body_ph = _get_ph(slide, 1)
    if body_ph:
        body_ph.text_frame.paragraphs[0].text = ""

    col_headers = [("Challenge", "red"), ("Impact", "orange"), ("Solution", "green")]
    col_w = 3.8
    for j, (header, hcolor) in enumerate(col_headers):
        hx = 0.6 + j * (col_w + 0.15)
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, hx, 2.2, col_w, 0.45, fill_color=_c(hcolor))
        _add_textbox(slide, hx + 0.1, 2.23, col_w - 0.2, 0.35, header, 12, _c("white"), bold=True, alignment=PP_ALIGN.CENTER)

    for i, ch in enumerate(challenges[:5]):
        y = 2.85 + i * 0.85
        if y > 6.3:
            break
        for j, (key, cname) in enumerate([("challenge", "red"), ("impact", "orange"), ("solution", "green")]):
            cx = 0.6 + j * (col_w + 0.15)
            color = _c(cname)
            card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, cx, y, col_w, 0.7, fill_color=_c("off_white"))
            card.line.color.rgb = _c("light_gray")
            card.line.width = Pt(0.5)
            _add_shape(slide, MSO_SHAPE.RECTANGLE, cx, y, 0.06, 0.7, fill_color=color)
            _add_textbox(slide, cx + 0.2, y + 0.08, col_w - 0.35, 0.55, ch.get(key, ""), 10, _c("charcoal"))


# ============================================================
# LAYOUT DISPATCHER
# ============================================================

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
}


def build_slide_by_layout(prs: Presentation, layout: str, data: dict,
                          slide_number: int = 0) -> None:
    builder = LAYOUT_BUILDERS.get(layout)

    if builder is None:
        build_content_slide(prs, title=data.get("title", ""),
                            body_text=data.get("body", ""),
                            bullets=data.get("bullets", []),
                            slide_number=slide_number)
        return

    if layout == "content":
        builder(prs, title=data.get("title", ""), body_text=data.get("body", ""),
                bullets=data.get("bullets", []), slide_number=slide_number)
    elif layout == "two_column":
        left = data.get("left", {})
        right = data.get("right", {})
        builder(prs, title=data.get("title", ""), left_title=left.get("title", ""),
                left_bullets=left.get("bullets", []), right_title=right.get("title", ""),
                right_bullets=right.get("bullets", []), slide_number=slide_number)
    elif layout == "icon_grid":
        builder(prs, title=data.get("title", ""), items=data.get("items", []), slide_number=slide_number)
    elif layout == "process_flow":
        builder(prs, title=data.get("title", ""), steps=data.get("steps", []), slide_number=slide_number)
    elif layout == "comparison_table":
        builder(prs, title=data.get("title", ""), headers=data.get("headers", []),
                rows=data.get("rows", []), slide_number=slide_number)
    elif layout == "stats_highlight":
        builder(prs, title=data.get("title", ""), stats=data.get("stats", []), slide_number=slide_number)
    elif layout == "key_value":
        builder(prs, title=data.get("title", ""), pairs=data.get("pairs", []), slide_number=slide_number)
    elif layout == "image_placeholder":
        builder(prs, title=data.get("title", ""), placeholder_text=data.get("placeholder_text", "Diagram"),
                caption=data.get("caption", ""), slide_number=slide_number)
    elif layout == "architecture":
        builder(prs, title=data.get("title", ""), layers=data.get("layers", []), slide_number=slide_number)
    elif layout == "technology":
        builder(prs, title=data.get("title", ""), technologies=data.get("technologies", []), slide_number=slide_number)
    elif layout == "challenges":
        builder(prs, title=data.get("title", ""), challenges=data.get("challenges", []), slide_number=slide_number)
    elif layout == "timeline":
        builder(prs, title=data.get("title", ""), phases=data.get("phases", []), slide_number=slide_number)
    elif layout == "team":
        builder(prs, title=data.get("title", ""), team_members=data.get("members", []), slide_number=slide_number)
