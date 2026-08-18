"""Individual slide type builders for Xebia-branded PPTX generation.

Each builder creates one slide type using python-pptx, reading all brand
values from the design system. Slide types are derived from patterns
observed across 7 reference Xebia decks (254 slides analyzed).
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from design_system.brand import colors, typography, spacing, theme, copyright_text


def _rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _brand_purple() -> RGBColor:
    return _rgb(colors()["primary"]["purple"])


def _brand_purple_dark() -> RGBColor:
    return _rgb(colors()["primary"]["purple_dark"])


def _white() -> RGBColor:
    return _rgb("#FFFFFF")


def _black() -> RGBColor:
    return _rgb(colors()["neutral"]["black"])


def _charcoal() -> RGBColor:
    return _rgb(colors()["neutral"]["charcoal"])


def _gray() -> RGBColor:
    return _rgb(colors()["neutral"]["mid_gray"])


def _light_gray() -> RGBColor:
    return _rgb(colors()["neutral"]["light_gray"])


def _set_text(text_frame, text, font_size_pt, color, bold=False, alignment=PP_ALIGN.LEFT):
    """Set text in a text frame with consistent formatting."""
    text_frame.clear()
    text_frame.word_wrap = True
    p = text_frame.paragraphs[0]
    p.alignment = alignment
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size_pt)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"
    return p


def _add_paragraph(text_frame, text, font_size_pt, color, bold=False,
                   alignment=PP_ALIGN.LEFT, space_before=0, space_after=0):
    """Add a paragraph to an existing text frame."""
    p = text_frame.add_paragraph()
    p.alignment = alignment
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size_pt)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"
    return p


def _add_footer(slide, prs, slide_number: int):
    """Add standard Xebia footer: copyright left, slide number right."""
    sp = spacing()["ppt"]
    w = prs.slide_width
    h = prs.slide_height
    footer_h = Inches(sp["footer_height_in"])
    footer_y = h - footer_h

    # Copyright text
    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), footer_y,
        Inches(5), footer_h
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    _set_text(tf, copyright_text(), 9, _gray(), alignment=PP_ALIGN.LEFT)

    # Slide number
    txBox2 = slide.shapes.add_textbox(
        w - Inches(1.5), footer_y,
        Inches(1), footer_h
    )
    tf2 = txBox2.text_frame
    _set_text(tf2, str(slide_number), 9, _gray(), alignment=PP_ALIGN.RIGHT)


# ============================================================
# SLIDE TYPE: COVER
# ============================================================

def build_cover_slide(prs: Presentation, title: str, subtitle: str = "",
                      customer: str = "", date: str = "") -> None:
    """Purple full-background cover slide with white text — matches Xebia pattern."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    w = prs.slide_width
    h = prs.slide_height

    # Purple background shape
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, w, h
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = _brand_purple()
    bg.line.fill.background()

    # Decorative lighter purple circle (inspired by logo blob shape)
    circle_size = Inches(4.5)
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        w - circle_size - Inches(0.3),
        Inches(0.3),
        circle_size, circle_size
    )
    circle.fill.solid()
    circle.fill.fore_color.rgb = _brand_purple_dark()
    circle.line.fill.background()
    circle.rotation = -10.0

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.5), Inches(7), Inches(1.5)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    _set_text(tf, title, 36, _white(), bold=True, alignment=PP_ALIGN.LEFT)

    # Subtitle
    if subtitle:
        txBox2 = slide.shapes.add_textbox(
            Inches(0.8), Inches(3.1), Inches(7), Inches(0.8)
        )
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        _set_text(tf2, subtitle, 18, _white(), alignment=PP_ALIGN.LEFT)

    # Customer + date at bottom
    bottom_text = ""
    if customer:
        bottom_text += f"Prepared for: {customer}"
    if date:
        if bottom_text:
            bottom_text += "  |  "
        bottom_text += date

    if bottom_text:
        txBox3 = slide.shapes.add_textbox(
            Inches(0.8), Inches(4.4), Inches(6), Inches(0.5)
        )
        tf3 = txBox3.text_frame
        _set_text(tf3, bottom_text, 12, _rgb(colors()["primary"]["purple_muted"]),
                  alignment=PP_ALIGN.LEFT)

    # Tagline bottom-right
    txBox4 = slide.shapes.add_textbox(
        Inches(5.5), Inches(5.0), Inches(4), Inches(0.4)
    )
    tf4 = txBox4.text_frame
    _set_text(tf4, theme()["tagline"], 11, _white(), alignment=PP_ALIGN.RIGHT)


# ============================================================
# SLIDE TYPE: SECTION DIVIDER
# ============================================================

def build_section_divider(prs: Presentation, section_title: str,
                          slide_number: int) -> None:
    """Purple background section divider — visual break between proposal sections."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    w = prs.slide_width
    h = prs.slide_height

    # Purple background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, w, h)
    bg.fill.solid()
    bg.fill.fore_color.rgb = _brand_purple()
    bg.line.fill.background()

    # Section title centered
    txBox = slide.shapes.add_textbox(
        Inches(1), Inches(1.8), Inches(8), Inches(2)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    _set_text(tf, section_title, 36, _white(), bold=True, alignment=PP_ALIGN.LEFT)

    # Decorative line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1), Inches(3.5), Inches(2), Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = _white()
    line.line.fill.background()

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: TABLE OF CONTENTS
# ============================================================

def build_toc_slide(prs: Presentation, sections: list[str],
                    slide_number: int) -> None:
    """Table of contents slide with numbered section list."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.8)
    )
    _set_text(txBox.text_frame, "Contents", 36, _black(), bold=True)

    # Purple accent line under title
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(sp["margin_in"]), Inches(1.2), Inches(1.5), Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = _brand_purple()
    line.line.fill.background()

    # Section items in two columns
    items_per_col = (len(sections) + 1) // 2
    col_width = Inches(4)
    col_x = [Inches(sp["margin_in"]), Inches(5.2)]

    for col in range(2):
        start = col * items_per_col
        end = min(start + items_per_col, len(sections))
        if start >= len(sections):
            break

        txBox = slide.shapes.add_textbox(
            col_x[col], Inches(1.6), col_width, Inches(3.5)
        )
        tf = txBox.text_frame
        tf.word_wrap = True

        for i in range(start, end):
            if i == start:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            p.space_after = Pt(8)
            p.alignment = PP_ALIGN.LEFT

            # Number
            num_run = p.add_run()
            num_run.text = f"{i + 1:02d}  "
            num_run.font.size = Pt(13)
            num_run.font.color.rgb = _brand_purple()
            num_run.font.bold = True
            num_run.font.name = "Calibri"

            # Section name
            name_run = p.add_run()
            name_run.text = sections[i]
            name_run.font.size = Pt(13)
            name_run.font.color.rgb = _charcoal()
            name_run.font.name = "Calibri"

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: EXECUTIVE SUMMARY
# ============================================================

def build_executive_summary_slide(prs: Presentation, title: str,
                                  summary_text: str, key_points: list[str],
                                  slide_number: int) -> None:
    """Executive summary with text block and key points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.8)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    # Summary paragraph
    txBox2 = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(1.3),
        Inches(5.5), Inches(3.5)
    )
    tf = txBox2.text_frame
    tf.word_wrap = True
    _set_text(tf, summary_text, 12, _charcoal())

    # Key points in a right-side purple card
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(6.2), Inches(1.3), Inches(3.3), Inches(3.5)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = _rgb(colors()["neutral"]["off_white"])
    card.line.fill.background()

    txBox3 = slide.shapes.add_textbox(
        Inches(6.5), Inches(1.5), Inches(2.9), Inches(3.2)
    )
    tf3 = txBox3.text_frame
    tf3.word_wrap = True

    # Header
    _set_text(tf3, "Key Highlights", 14, _brand_purple(), bold=True)

    for point in key_points:
        p = tf3.add_paragraph()
        p.space_before = Pt(8)
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = f"•  {point}"
        run.font.size = Pt(11)
        run.font.color.rgb = _charcoal()
        run.font.name = "Calibri"

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: CONTENT (generic)
# ============================================================

def build_content_slide(prs: Presentation, title: str,
                        body_text: str = "", bullets: list[str] = None,
                        slide_number: int = 0) -> None:
    """Generic content slide with title and body text or bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.8)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    # Purple accent line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(sp["margin_in"]), Inches(1.2), Inches(1.5), Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = _brand_purple()
    line.line.fill.background()

    # Body
    txBox2 = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(1.5),
        Inches(9), Inches(3.5)
    )
    tf = txBox2.text_frame
    tf.word_wrap = True

    if body_text:
        _set_text(tf, body_text, 14, _charcoal())

    if bullets:
        for i, bullet in enumerate(bullets):
            if i == 0 and not body_text:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.space_before = Pt(6)
            p.space_after = Pt(4)
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = f"•  {bullet}"
            run.font.size = Pt(13)
            run.font.color.rgb = _charcoal()
            run.font.name = "Calibri"

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: TWO-COLUMN CONTENT
# ============================================================

def build_two_column_slide(prs: Presentation, title: str,
                           left_title: str, left_bullets: list[str],
                           right_title: str, right_bullets: list[str],
                           slide_number: int = 0) -> None:
    """Two-column layout for comparisons, scope/approach, etc."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.7)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    for col_idx, (col_title, col_bullets) in enumerate([
        (left_title, left_bullets), (right_title, right_bullets)
    ]):
        x = Inches(sp["margin_in"]) if col_idx == 0 else Inches(5.2)
        col_w = Inches(4.3)

        # Column header card
        header_card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x, Inches(1.3), col_w, Inches(0.5)
        )
        header_card.fill.solid()
        header_card.fill.fore_color.rgb = _brand_purple() if col_idx == 0 else _rgb(colors()["accent"]["teal"])
        header_card.line.fill.background()

        txH = slide.shapes.add_textbox(x + Inches(0.15), Inches(1.35), col_w - Inches(0.3), Inches(0.4))
        _set_text(txH.text_frame, col_title, 14, _white(), bold=True)

        # Bullets
        txB = slide.shapes.add_textbox(x, Inches(2.0), col_w, Inches(3.0))
        tf = txB.text_frame
        tf.word_wrap = True
        for i, bullet in enumerate(col_bullets):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.space_before = Pt(6)
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = f"•  {bullet}"
            run.font.size = Pt(12)
            run.font.color.rgb = _charcoal()
            run.font.name = "Calibri"

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: TIMELINE
# ============================================================

def build_timeline_slide(prs: Presentation, title: str,
                         phases: list[dict], slide_number: int = 0) -> None:
    """Timeline slide with horizontal phase bars.

    phases: [{"name": "Phase 1", "duration": "2 weeks", "description": "..."}]
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.7)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    chart_colors = [_brand_purple(), _rgb(colors()["accent"]["teal"]),
                    _rgb(colors()["accent"]["blue"]), _rgb(colors()["accent"]["green"]),
                    _rgb(colors()["accent"]["orange"])]

    num_phases = len(phases)
    bar_height = min(0.6, 3.0 / max(num_phases, 1))
    start_y = 1.5

    for i, phase in enumerate(phases):
        y = start_y + i * (bar_height + 0.25)
        color = chart_colors[i % len(chart_colors)]

        # Phase bar
        bar_w = Inches(6)
        bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(sp["margin_in"]), Inches(y),
            bar_w, Inches(bar_height)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()

        # Phase name inside bar
        txP = slide.shapes.add_textbox(
            Inches(sp["margin_in"] + 0.15), Inches(y + 0.05),
            Inches(3), Inches(bar_height - 0.1)
        )
        tf = txP.text_frame
        tf.word_wrap = True
        _set_text(tf, phase["name"], 11, _white(), bold=True)

        # Duration label to right of bar
        txD = slide.shapes.add_textbox(
            Inches(sp["margin_in"]) + bar_w + Inches(0.2), Inches(y + 0.05),
            Inches(2.5), Inches(bar_height - 0.1)
        )
        tf2 = txD.text_frame
        _set_text(tf2, phase.get("duration", ""), 11, _charcoal(), bold=True)

        # Description below
        if phase.get("description"):
            txDesc = slide.shapes.add_textbox(
                Inches(sp["margin_in"] + 0.15), Inches(y + 0.25),
                Inches(5.5), Inches(0.3)
            )
            tf3 = txDesc.text_frame
            tf3.word_wrap = True
            _set_text(tf3, phase["description"], 9, _white())

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: TEAM STRUCTURE
# ============================================================

def build_team_slide(prs: Presentation, title: str,
                     team_members: list[dict], slide_number: int = 0) -> None:
    """Team structure slide with member cards.

    team_members: [{"name": "...", "role": "...", "expertise": "..."}]
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.7)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    cols = min(len(team_members), 4)
    card_w = (9.0 - (cols - 1) * 0.3) / cols
    start_y = 1.5

    for i, member in enumerate(team_members[:8]):
        col = i % cols
        row = i // cols
        x = sp["margin_in"] + col * (card_w + 0.3)
        y = start_y + row * 2.0

        # Card background
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(y), Inches(card_w), Inches(1.7)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = _rgb(colors()["neutral"]["off_white"])
        card.line.fill.background()

        # Purple top accent
        accent = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(x), Inches(y), Inches(card_w), Inches(0.06)
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = _brand_purple()
        accent.line.fill.background()

        # Name
        txN = slide.shapes.add_textbox(
            Inches(x + 0.15), Inches(y + 0.2),
            Inches(card_w - 0.3), Inches(0.4)
        )
        _set_text(txN.text_frame, member["name"], 13, _black(), bold=True)

        # Role
        txR = slide.shapes.add_textbox(
            Inches(x + 0.15), Inches(y + 0.55),
            Inches(card_w - 0.3), Inches(0.35)
        )
        _set_text(txR.text_frame, member["role"], 11, _brand_purple(), bold=True)

        # Expertise
        if member.get("expertise"):
            txE = slide.shapes.add_textbox(
                Inches(x + 0.15), Inches(y + 0.9),
                Inches(card_w - 0.3), Inches(0.6)
            )
            tf = txE.text_frame
            tf.word_wrap = True
            _set_text(tf, member["expertise"], 9, _gray())

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: COMMERCIALS TABLE
# ============================================================

def build_commercials_slide(prs: Presentation, title: str,
                            rows: list[dict], total: str = "",
                            assumptions: list[str] = None,
                            slide_number: int = 0) -> None:
    """Commercials/pricing slide with a styled table.

    rows: [{"item": "...", "hours": "...", "rate": "...", "cost": "..."}]
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sp = spacing()["ppt"]

    txBox = slide.shapes.add_textbox(
        Inches(sp["margin_in"]), Inches(sp["margin_in"]),
        Inches(9), Inches(0.7)
    )
    _set_text(txBox.text_frame, title, 30, _black(), bold=True)

    headers = ["Item", "Hours", "Rate", "Cost"]
    col_widths = [Inches(4), Inches(1.5), Inches(1.5), Inches(2)]
    num_rows = len(rows) + 1 + (1 if total else 0)

    table_shape = slide.shapes.add_table(
        num_rows, 4,
        Inches(sp["margin_in"]), Inches(1.5),
        Inches(9), Inches(0.4 * num_rows)
    )
    table = table_shape.table

    for i, w in enumerate(col_widths):
        table.columns[i].width = w

    # Header row
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = _brand_purple()
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(11)
            p.font.color.rgb = _white()
            p.font.bold = True
            p.font.name = "Calibri"

    # Data rows
    for r_idx, row in enumerate(rows):
        values = [row.get("item", ""), row.get("hours", ""),
                  row.get("rate", ""), row.get("cost", "")]
        for c_idx, val in enumerate(values):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = str(val)
            if r_idx % 2 == 1:
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(colors()["neutral"]["off_white"])
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10)
                p.font.color.rgb = _charcoal()
                p.font.name = "Calibri"

    # Total row
    if total:
        total_row = len(rows) + 1
        for c_idx in range(4):
            cell = table.cell(total_row, c_idx)
            if c_idx == 0:
                cell.text = "Total"
            elif c_idx == 3:
                cell.text = total
            cell.fill.solid()
            cell.fill.fore_color.rgb = _brand_purple_dark()
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = _white()
                p.font.bold = True
                p.font.name = "Calibri"

    # Assumptions below table
    if assumptions:
        table_bottom = 1.5 + 0.4 * num_rows + 0.3
        txA = slide.shapes.add_textbox(
            Inches(sp["margin_in"]), Inches(table_bottom),
            Inches(9), Inches(1.5)
        )
        tf = txA.text_frame
        tf.word_wrap = True
        _set_text(tf, "Assumptions:", 11, _charcoal(), bold=True)
        for assumption in assumptions:
            _add_paragraph(tf, f"•  {assumption}", 10, _gray(), space_before=3)

    _add_footer(slide, prs, slide_number)


# ============================================================
# SLIDE TYPE: CLOSING / Q&A
# ============================================================

def build_closing_slide(prs: Presentation, title: str = "Thank You",
                        contact_name: str = "", contact_email: str = "",
                        contact_phone: str = "", slide_number: int = 0) -> None:
    """Closing slide — purple background with contact details."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    w = prs.slide_width
    h = prs.slide_height

    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, w, h)
    bg.fill.solid()
    bg.fill.fore_color.rgb = _brand_purple()
    bg.line.fill.background()

    # Title
    txBox = slide.shapes.add_textbox(
        Inches(1), Inches(1.5), Inches(8), Inches(1.2)
    )
    _set_text(txBox.text_frame, title, 40, _white(), bold=True, alignment=PP_ALIGN.LEFT)

    # Contact info
    if contact_name or contact_email:
        txC = slide.shapes.add_textbox(
            Inches(1), Inches(3.0), Inches(5), Inches(2)
        )
        tf = txC.text_frame
        tf.word_wrap = True
        if contact_name:
            _set_text(tf, contact_name, 16, _white(), bold=True)
        if contact_email:
            _add_paragraph(tf, contact_email, 13, _rgb(colors()["primary"]["purple_muted"]),
                          space_before=8)
        if contact_phone:
            _add_paragraph(tf, contact_phone, 13, _rgb(colors()["primary"]["purple_muted"]),
                          space_before=4)

    # Tagline
    txT = slide.shapes.add_textbox(
        Inches(5), Inches(4.8), Inches(4.5), Inches(0.5)
    )
    _set_text(txT.text_frame, theme()["tagline"], 12, _white(),
              alignment=PP_ALIGN.RIGHT)
