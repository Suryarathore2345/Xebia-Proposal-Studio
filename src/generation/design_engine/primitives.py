"""Low-level visual primitives for python-pptx.

Extends python-pptx with gradient fills, transparency, dashed borders,
and decorative shapes via direct OpenXML manipulation.
"""

from lxml import etree
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn


SLIDE_W = 13.333
SLIDE_H = 7.500


def rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ── Gradient Fill ───────────────────────────────────────────────

def gradient_fill(shape, color1: str, color2: str, angle: int = 270):
    """Apply linear gradient fill to a shape.

    angle: degrees, 0=right, 90=up, 180=left, 270=down (default top-to-bottom).
    """
    spPr = shape._element.spPr

    for tag in ("solidFill", "gradFill", "noFill", "pattFill"):
        for child in list(spPr):
            if child.tag.endswith("}" + tag):
                spPr.remove(child)

    gradFill = etree.SubElement(spPr, qn("a:gradFill"))
    gsLst = etree.SubElement(gradFill, qn("a:gsLst"))

    gs1 = etree.SubElement(gsLst, qn("a:gs"))
    gs1.set("pos", "0")
    srgb1 = etree.SubElement(gs1, qn("a:srgbClr"))
    srgb1.set("val", color1.lstrip("#"))

    gs2 = etree.SubElement(gsLst, qn("a:gs"))
    gs2.set("pos", "100000")
    srgb2 = etree.SubElement(gs2, qn("a:srgbClr"))
    srgb2.set("val", color2.lstrip("#"))

    lin = etree.SubElement(gradFill, qn("a:lin"))
    lin.set("ang", str(angle * 60000))
    lin.set("scaled", "1")


# ── Shape Transparency ─────────────────────────────────────────

def set_fill_opacity(shape, opacity: float):
    """Set shape fill transparency. 1.0 = fully opaque, 0.0 = fully transparent."""
    alpha_val = str(int(opacity * 100000))
    spPr = shape._element.spPr

    solid = spPr.find(qn("a:solidFill"))
    if solid is not None:
        srgb = solid.find(qn("a:srgbClr"))
        if srgb is not None:
            for existing in srgb.findall(qn("a:alpha")):
                srgb.remove(existing)
            alpha = etree.SubElement(srgb, qn("a:alpha"))
            alpha.set("val", alpha_val)


# ── Dashed Borders ──────────────────────────────────────────────

def set_dash_style(shape, dash: str = "dash", color: str = "#6C1D5F",
                   width: float = 1.5):
    """Set dashed border on a shape.

    dash options: "solid", "dash", "dashDot", "lgDash", "lgDashDot",
                  "sysDash", "sysDot", "lgDashDotDot"
    """
    ln = shape.line
    ln.color.rgb = rgb(color)
    ln.width = Pt(width)

    ln_elem = shape._element.spPr.find(qn("a:ln"))
    if ln_elem is None:
        ln_elem = etree.SubElement(shape._element.spPr, qn("a:ln"))

    for existing in ln_elem.findall(qn("a:prstDash")):
        ln_elem.remove(existing)
    prstDash = etree.SubElement(ln_elem, qn("a:prstDash"))
    prstDash.set("val", dash)


# ── Send Shape to Back ──────────────────────────────────────────

def send_to_back(shape, slide):
    """Move shape behind all other shapes on the slide."""
    sp = shape._element
    spTree = slide.shapes._spTree
    sp.getparent().remove(sp)
    spTree.insert(2, sp)


# ── Core Shape Builders ────────────────────────────────────────

def add_rectangle(slide, left: float, top: float, width: float, height: float,
                  fill_color: str = None, line_color: str = None,
                  line_width: float = None):
    """Add a rectangle shape with optional fill and border. Dimensions in inches."""
    left = max(0, min(left, SLIDE_W - 0.01))
    top = max(0, min(top, SLIDE_H - 0.01))
    width = min(width, SLIDE_W - left)
    height = min(height, SLIDE_H - top)

    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top),
        Inches(width), Inches(height),
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill_color)
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = rgb(line_color)
        if line_width:
            shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def add_rounded_rectangle(slide, left: float, top: float, width: float,
                          height: float, fill_color: str = None,
                          line_color: str = None, line_width: float = None):
    """Add a rounded rectangle. Dimensions in inches."""
    left = max(0, min(left, SLIDE_W - 0.01))
    top = max(0, min(top, SLIDE_H - 0.01))
    width = min(width, SLIDE_W - left)
    height = min(height, SLIDE_H - top)

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top),
        Inches(width), Inches(height),
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill_color)
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = rgb(line_color)
        if line_width:
            shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def add_circle(slide, center_x: float, center_y: float, radius: float,
               fill_color: str = None, line_color: str = None):
    """Add a circle shape. center_x/y and radius in inches."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(center_x - radius), Inches(center_y - radius),
        Inches(radius * 2), Inches(radius * 2),
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill_color)
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = rgb(line_color)
    else:
        shape.line.fill.background()
    return shape


def add_triangle(slide, left: float, top: float, width: float, height: float,
                 fill_color: str = None, rotation: float = 0):
    """Add an isosceles triangle with optional rotation (degrees)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ISOSCELES_TRIANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill_color)
    else:
        shape.fill.background()
    shape.line.fill.background()
    if rotation:
        shape.rotation = rotation
    return shape


def add_right_triangle(slide, left: float, top: float, width: float,
                       height: float, fill_color: str = None,
                       rotation: float = 0):
    """Add a right triangle for corner accents."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_TRIANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill_color)
    else:
        shape.fill.background()
    shape.line.fill.background()
    if rotation:
        shape.rotation = rotation
    return shape


# ── Decorative Patterns ────────────────────────────────────────

def add_dot_pattern(slide, region_left: float, region_top: float,
                    region_width: float, region_height: float,
                    dot_size: float = 0.04, spacing: float = 0.25,
                    color: str = "#6C1D5F", opacity: float = 0.10):
    """Add a grid of small dots as decorative texture."""
    shapes = []
    x = region_left
    while x < region_left + region_width:
        y = region_top
        while y < region_top + region_height:
            dot = add_circle(slide, x + dot_size, y + dot_size, dot_size,
                             fill_color=color)
            set_fill_opacity(dot, opacity)
            shapes.append(dot)
            y += spacing
        x += spacing
    return shapes


def add_floating_circles(slide, anchor_x: float, anchor_y: float,
                         color: str = "#6C1D5F", opacity: float = 0.08,
                         count: int = 3):
    """Add overlapping circles as decorative accent near an anchor point."""
    configs = [
        (0, 0, 0.8),
        (0.5, -0.3, 0.5),
        (-0.2, 0.6, 0.35),
    ]
    shapes = []
    for i in range(min(count, len(configs))):
        dx, dy, r = configs[i]
        circle = add_circle(slide, anchor_x + dx, anchor_y + dy, r,
                            fill_color=color)
        set_fill_opacity(circle, opacity)
        shapes.append(circle)
    return shapes


# ── Gradient Shape Helpers ──────────────────────────────────────

def add_gradient_rectangle(slide, left: float, top: float, width: float,
                           height: float, color1: str, color2: str,
                           angle: int = 270):
    """Add a rectangle with gradient fill."""
    shape = add_rectangle(slide, left, top, width, height)
    shape.fill.background()
    gradient_fill(shape, color1, color2, angle)
    return shape


def add_full_slide_background(slide, fill_color: str = None,
                              gradient_colors: tuple = None,
                              gradient_angle: int = 270):
    """Add a full-slide background shape and send it to back."""
    if gradient_colors:
        shape = add_gradient_rectangle(
            slide, 0, 0, SLIDE_W, SLIDE_H,
            gradient_colors[0], gradient_colors[1], gradient_angle,
        )
    elif fill_color:
        shape = add_rectangle(slide, 0, 0, SLIDE_W, SLIDE_H,
                              fill_color=fill_color)
    else:
        return None
    send_to_back(shape, slide)
    return shape
