"""Dynamic Template Engine — generates unique visual themes for each proposal.

Instead of using one fixed template, this engine:
1. Rotates across multiple Xebia base templates (retail, carrington, synapse)
2. Generates dynamic theme variations (color accents, light/dark mixing, decorative styles)
3. Maps slide types to the best available layout in the selected template
4. Adds premium decorative elements (world map, gradient overlays, geometric patterns)
"""

import random
from pathlib import Path
from dataclasses import dataclass, field
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor


TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

AVAILABLE_TEMPLATES = {
    "retail": {
        "file": "xebia_retail.pptx",
        "cover_dark": "Main-cover_dark",
        "cover_light": "Main-cover_light",
        "chapter_dark": "Chapter_dark",
        "chapter_light": "Chapter_light",
        "content_basic": "Content_Basic",
        "content_2col": "Content_2 Columns",
        "content_3col": "Content_3 Columns",
        "content_4col": "Content_4 Columns",
        "content_photo_right": "Content_Photo_right",
        "content_photo_left": "Content_Photo_left",
        "content_photo_big_right": "Content_Photo-Big_right",
        "content_photo_big_left": "Content_Photo-Big_left",
        "content_photo_big_right_dark": "Content_Photo-Big_right_dark",
        "content_photo_big_left_dark": "Content_Photo-Big_left_dark",
        "content_2col_photo": "Content_2 Columns_Photo",
        "toc": "Table of contents",
        "toc_photo": "Table of contents_photo",
        "end_dark": "End-cover_dark",
        "end_light": "End-cover_light",
        "photo_bg": "1_Photo_background",
        "content_title": "Content Title",
    },
    "synapse": {
        "file": "xebia_synapse.pptx",
        "cover_dark": "Main-cover_dark",
        "cover_light": "Main-cover_light",
        "chapter_dark": "Chapter_dark",
        "chapter_light": "Chapter_light",
        "content_basic": "Content_Basic",
        "content_2col": "Content_2 Columns",
        "content_3col": "Content_3 Columns",
        "content_4col": "Content_4 Columns",
        "content_photo_right": "Content_Photo_right",
        "content_photo_left": "Content_Photo_left",
        "content_photo_big_right": "Content_Photo-Big_right",
        "content_photo_big_left": "Content_Photo-Big_left",
        "content_photo_big_right_dark": "Content_Photo-Big_right_dark",
        "content_photo_big_left_dark": "Content_Photo-Big_left_dark",
        "content_2col_photo": "Content_2 Columns_Photo",
        "toc": "Table of contents",
        "toc_photo": "Table of contents_photo",
        "end_dark": "End-cover_dark",
        "end_light": "End-cover_light",
        "content_title": "Content Title",
    },
    "carrington": {
        "file": "xebia_carrington.pptx",
        "cover_dark": "Title Slide / Dark",
        "cover_light": "Title Slide / White",
        "chapter_dark": "Section Divider / Dark",
        "chapter_light": "Section Divider / Light",
        "content_basic": "Title Content/White",
        "content_2col": "Double / Column / Light",
        "content_3col": "Triple / Column / Light",
        "content_photo_right": "Image / Right / Light",
        "content_photo_right_dark": "Image / Right / Dark",
        "toc": "Table / Content Short",
        "end_dark": "Title Slide / Dark / 2",
        "end_light": "Title Slide / White / 2",
        "card_3col": "Card / 3 Column / Light",
        "card_4col": "Card / 4 Column / Light",
        "card_6col": "Card / 6 Column / Light",
        "quote_light": "Quote / Light",
        "quote_dark": "Quote / Dark",
        "moodboard": "Moodboard / Text / Light",
        "content_title": "Header_Only/White",
    },
}

ACCENT_PALETTES = [
    {"name": "classic", "accents": ["#6C1D5F", "#00A5B5", "#2D6EB5", "#3DAE2B", "#F39200", "#8BC4E0"]},
    {"name": "ocean", "accents": ["#1A5276", "#00A5B5", "#2980B9", "#48C9B0", "#1ABC9C", "#3498DB"]},
    {"name": "sunset", "accents": ["#6C1D5F", "#C0392B", "#E74C3C", "#F39200", "#F1C40F", "#D35400"]},
    {"name": "forest", "accents": ["#1E8449", "#27AE60", "#2ECC71", "#00A5B5", "#16A085", "#6C1D5F"]},
    {"name": "royal", "accents": ["#6C1D5F", "#8E44AD", "#9B59B6", "#2D6EB5", "#3498DB", "#1ABC9C"]},
    {"name": "tech", "accents": ["#2D6EB5", "#3498DB", "#00A5B5", "#6C1D5F", "#8BC4E0", "#2C3E50"]},
    {"name": "warm", "accents": ["#6C1D5F", "#E67E22", "#F39200", "#D35400", "#C0392B", "#F1C40F"]},
]

DECORATIVE_STYLES = [
    "geometric",
    "gradient_bars",
    "world_map",
    "dot_grid",
    "corner_accent",
    "wave_line",
]


@dataclass
class ThemeConfig:
    """Dynamic theme configuration for a proposal deck."""
    template_name: str
    template_file: str
    layout_map: dict
    accent_palette: list[str]
    palette_name: str
    dark_mode_ratio: float
    decorative_style: str
    use_photo_layouts: bool
    alternate_photo_side: bool
    slide_counter: int = 0

    def next_accent(self) -> str:
        color = self.accent_palette[self.slide_counter % len(self.accent_palette)]
        self.slide_counter += 1
        return color

    def should_use_dark(self) -> bool:
        return random.random() < self.dark_mode_ratio

    def get_layout_name(self, role: str) -> str:
        return self.layout_map.get(role, self.layout_map.get("content_basic", ""))

    def get_photo_layout(self, prefer_big: bool = False) -> str:
        if not self.use_photo_layouts:
            return self.get_layout_name("content_basic")

        self.slide_counter += 1
        use_left = (self.slide_counter % 2 == 0) if self.alternate_photo_side else random.choice([True, False])

        if prefer_big:
            if self.should_use_dark():
                key = "content_photo_big_left_dark" if use_left else "content_photo_big_right_dark"
            else:
                key = "content_photo_big_left" if use_left else "content_photo_big_right"
        else:
            key = "content_photo_left" if use_left else "content_photo_right"

        return self.layout_map.get(key, self.get_layout_name("content_basic"))

    def get_chapter_layout(self) -> str:
        if self.should_use_dark():
            return self.get_layout_name("chapter_dark")
        return self.get_layout_name("chapter_light")


def generate_theme(proposal_context: dict = None) -> ThemeConfig:
    """Generate a unique theme configuration for a proposal.

    Uses proposal context (industry, tech stack, tone) to influence
    template and palette selection, with randomization for variety.
    """
    context = proposal_context or {}
    industry = context.get("industry", "").lower()
    tone = context.get("tone", "professional")

    template_name = random.choice(list(AVAILABLE_TEMPLATES.keys()))

    if industry in ("finance", "banking", "insurance"):
        palette = next((p for p in ACCENT_PALETTES if p["name"] == "royal"), random.choice(ACCENT_PALETTES))
    elif industry in ("technology", "software", "saas"):
        palette = next((p for p in ACCENT_PALETTES if p["name"] == "tech"), random.choice(ACCENT_PALETTES))
    elif industry in ("retail", "ecommerce", "cpg"):
        palette = next((p for p in ACCENT_PALETTES if p["name"] == "warm"), random.choice(ACCENT_PALETTES))
    elif industry in ("healthcare", "pharma"):
        palette = next((p for p in ACCENT_PALETTES if p["name"] == "ocean"), random.choice(ACCENT_PALETTES))
    else:
        palette = random.choice(ACCENT_PALETTES)

    template_config = AVAILABLE_TEMPLATES[template_name]
    template_file = str(TEMPLATES_DIR / template_config["file"])

    layout_map = {k: v for k, v in template_config.items() if k != "file"}

    dark_ratio = random.uniform(0.3, 0.6)
    decorative = random.choice(DECORATIVE_STYLES)

    return ThemeConfig(
        template_name=template_name,
        template_file=template_file,
        layout_map=layout_map,
        accent_palette=palette["accents"],
        palette_name=palette["name"],
        dark_mode_ratio=dark_ratio,
        decorative_style=decorative,
        use_photo_layouts=True,
        alternate_photo_side=random.choice([True, False]),
    )


def create_themed_presentation(theme: ThemeConfig) -> Presentation:
    """Create a Presentation from the selected template."""
    tpl_path = Path(theme.template_file)
    if tpl_path.exists():
        return Presentation(str(tpl_path))
    fallback = TEMPLATES_DIR / "xebia_retail.pptx"
    if fallback.exists():
        return Presentation(str(fallback))
    return Presentation()


# ============================================================
# DECORATIVE ELEMENTS — added to slides for visual richness
# ============================================================

def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def add_decorative_element(slide, style: str, accent_color: str, position: str = "bottom"):
    """Add a decorative element to a slide based on the theme's style."""
    color = _rgb(accent_color)

    if style == "gradient_bars":
        _add_gradient_bars(slide, color, position)
    elif style == "geometric":
        _add_geometric_shapes(slide, color, position)
    elif style == "dot_grid":
        _add_dot_grid(slide, color, position)
    elif style == "corner_accent":
        _add_corner_accent(slide, color, position)
    elif style == "wave_line":
        _add_wave_line(slide, color, position)
    elif style == "world_map":
        _add_world_map_dots(slide, color)


def _add_gradient_bars(slide, color: RGBColor, position: str):
    """Add a series of gradient accent bars."""
    bar_count = random.randint(3, 5)
    bar_h = 0.04
    if position == "bottom":
        base_y = 7.1
        for i in range(bar_count):
            opacity = 1.0 - (i * 0.2)
            w = 13.33 * (1.0 - i * 0.15)
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0), Inches(base_y + i * 0.08),
                Inches(w), Inches(bar_h)
            )
            shape.fill.solid()
            r, g, b = color[0], color[1], color[2]
            shape.fill.fore_color.rgb = RGBColor(
                min(255, int(r + (255 - r) * (1 - opacity))),
                min(255, int(g + (255 - g) * (1 - opacity))),
                min(255, int(b + (255 - b) * (1 - opacity))),
            )
            shape.line.fill.background()
    else:
        base_y = 0.0
        for i in range(bar_count):
            w = 13.33 * (1.0 - i * 0.15)
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(13.33 - w), Inches(base_y + i * 0.08),
                Inches(w), Inches(bar_h)
            )
            shape.fill.solid()
            r, g, b = color[0], color[1], color[2]
            opacity = 1.0 - (i * 0.2)
            shape.fill.fore_color.rgb = RGBColor(
                min(255, int(r + (255 - r) * (1 - opacity))),
                min(255, int(g + (255 - g) * (1 - opacity))),
                min(255, int(b + (255 - b) * (1 - opacity))),
            )
            shape.line.fill.background()


def _add_geometric_shapes(slide, color: RGBColor, position: str):
    """Add subtle geometric accent shapes."""
    if position == "bottom":
        x, y = 10.5, 6.2
    else:
        x, y = 0.3, 0.3

    sizes = [0.4, 0.25, 0.15]
    for i, size in enumerate(sizes):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.DIAMOND if i % 2 == 0 else MSO_SHAPE.OVAL,
            Inches(x + i * 0.6), Inches(y + (i % 2) * 0.3),
            Inches(size), Inches(size)
        )
        shape.fill.solid()
        r, g, b = color[0], color[1], color[2]
        opacity = 0.3 + (i * 0.15)
        shape.fill.fore_color.rgb = RGBColor(
            min(255, int(r + (255 - r) * (1 - opacity))),
            min(255, int(g + (255 - g) * (1 - opacity))),
            min(255, int(b + (255 - b) * (1 - opacity))),
        )
        shape.line.fill.background()


def _add_dot_grid(slide, color: RGBColor, position: str):
    """Add a subtle dot pattern."""
    if position == "bottom":
        base_x, base_y = 10.0, 6.0
    else:
        base_x, base_y = 0.5, 0.5

    dot_size = 0.06
    spacing = 0.25
    rows, cols = 4, 6
    for r in range(rows):
        for c in range(cols):
            if random.random() > 0.6:
                continue
            dot = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(base_x + c * spacing), Inches(base_y + r * spacing),
                Inches(dot_size), Inches(dot_size)
            )
            dot.fill.solid()
            opacity = random.uniform(0.15, 0.4)
            rv, gv, bv = color[0], color[1], color[2]
            dot.fill.fore_color.rgb = RGBColor(
                min(255, int(rv + (255 - rv) * (1 - opacity))),
                min(255, int(gv + (255 - gv) * (1 - opacity))),
                min(255, int(bv + (255 - bv) * (1 - opacity))),
            )
            dot.line.fill.background()


def _add_corner_accent(slide, color: RGBColor, position: str):
    """Add accent lines in the corner."""
    if position == "bottom":
        x, y = 11.5, 6.8
        shapes = [
            (MSO_SHAPE.RECTANGLE, x, y, 1.8, 0.04),
            (MSO_SHAPE.RECTANGLE, x + 0.5, y + 0.15, 1.3, 0.03),
            (MSO_SHAPE.RECTANGLE, x + 1.0, y + 0.28, 0.8, 0.025),
        ]
    else:
        x, y = 0.2, 0.2
        shapes = [
            (MSO_SHAPE.RECTANGLE, x, y, 1.8, 0.04),
            (MSO_SHAPE.RECTANGLE, x, y + 0.15, 1.3, 0.03),
            (MSO_SHAPE.RECTANGLE, x, y + 0.28, 0.8, 0.025),
        ]

    for i, (shape_type, sx, sy, sw, sh) in enumerate(shapes):
        shape = slide.shapes.add_shape(shape_type, Inches(sx), Inches(sy), Inches(sw), Inches(sh))
        shape.fill.solid()
        opacity = 0.8 - (i * 0.2)
        rv, gv, bv = color[0], color[1], color[2]
        shape.fill.fore_color.rgb = RGBColor(
            min(255, int(rv + (255 - rv) * (1 - opacity))),
            min(255, int(gv + (255 - gv) * (1 - opacity))),
            min(255, int(bv + (255 - bv) * (1 - opacity))),
        )
        shape.line.fill.background()


def _add_wave_line(slide, color: RGBColor, position: str):
    """Add a subtle wave/curve accent."""
    if position == "bottom":
        y = 7.0
    else:
        y = 0.1
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(y),
        Inches(13.33), Inches(0.06)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

    for i in range(3):
        accent = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(2 + i * 4), Inches(y - 0.03),
            Inches(0.12), Inches(0.12)
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = color
        accent.line.fill.background()


def _add_world_map_dots(slide, color: RGBColor):
    """Add world map outline using positioned dots — represents Xebia's global presence."""
    world_dots = [
        (4.2, 2.8), (4.5, 2.6), (4.8, 2.4), (5.0, 2.5), (5.3, 2.3),
        (5.5, 2.5), (5.8, 2.4), (6.0, 2.6), (6.3, 2.5), (6.5, 2.3),
        (6.8, 2.5), (7.0, 2.7), (7.3, 2.6), (7.5, 2.8), (7.8, 2.7),
        (8.0, 2.9), (8.3, 3.0), (8.5, 2.8), (8.8, 3.1), (9.0, 3.0),
        (4.0, 3.0), (4.3, 3.2), (4.5, 3.4), (4.8, 3.3), (5.0, 3.5),
        (5.3, 3.4), (5.5, 3.6), (5.8, 3.5), (6.0, 3.7), (6.3, 3.6),
        (6.5, 3.8), (6.8, 3.7), (7.0, 3.9), (7.3, 3.8), (7.5, 4.0),
        (3.5, 3.5), (3.8, 3.7), (4.0, 3.9), (4.3, 4.0), (4.5, 4.2),
        (9.2, 3.2), (9.4, 3.4), (9.6, 3.3), (9.8, 3.5), (9.5, 3.6),
        (9.0, 4.0), (9.3, 4.2), (9.5, 4.4), (9.7, 4.3), (9.9, 4.5),
        (7.8, 4.2), (8.0, 4.4), (8.2, 4.3), (8.5, 4.5), (8.7, 4.4),
        (3.0, 4.0), (3.2, 4.2), (3.5, 4.1), (3.7, 4.3), (3.3, 4.5),
        (5.0, 2.0), (5.5, 1.8), (6.0, 2.0), (6.5, 1.9), (7.0, 2.1),
        (7.5, 2.0), (8.0, 2.2), (8.5, 2.1),
    ]

    xebia_offices = [
        (5.2, 2.8, "Netherlands"),
        (5.4, 2.6, "Belgium"),
        (5.6, 3.0, "France"),
        (7.5, 3.2, "India"),
        (8.0, 3.5, "India"),
        (3.5, 3.0, "USA"),
        (9.0, 4.8, "Australia"),
        (6.2, 3.8, "UAE"),
    ]

    dot_size = 0.07
    for x, y in world_dots:
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(y),
            Inches(dot_size), Inches(dot_size)
        )
        dot.fill.solid()
        r, g, b = color[0], color[1], color[2]
        dot.fill.fore_color.rgb = RGBColor(
            min(255, int(r + (255 - r) * 0.7)),
            min(255, int(g + (255 - g) * 0.7)),
            min(255, int(b + (255 - b) * 0.7)),
        )
        dot.line.fill.background()

    office_dot_size = 0.14
    for x, y, label in xebia_offices:
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(y),
            Inches(office_dot_size), Inches(office_dot_size)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = color
        dot.line.fill.background()

        pulse = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x - 0.04), Inches(y - 0.04),
            Inches(office_dot_size + 0.08), Inches(office_dot_size + 0.08)
        )
        pulse.fill.solid()
        r, g, b = color[0], color[1], color[2]
        pulse.fill.fore_color.rgb = RGBColor(
            min(255, int(r + (255 - r) * 0.6)),
            min(255, int(g + (255 - g) * 0.6)),
            min(255, int(b + (255 - b) * 0.6)),
        )
        pulse.line.fill.background()
