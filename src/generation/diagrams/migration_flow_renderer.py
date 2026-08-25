"""Migration Flow Renderer — multi-zone left-to-right architecture diagrams.

Renders a horizontal flow of architecture zones with dashed-border containers,
properly-sized technology icons, connector arrows, journey labels, and
cross-cutting bottom bands.

Design reference: professional solution-architecture slides with nested zones,
dashed borders, large icons with labels, and colored connector arrows.
"""

from __future__ import annotations

from pathlib import Path

from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from generation.design_engine.primitives import (
    rgb, add_rounded_rectangle, add_rectangle, gradient_fill,
    set_fill_opacity, set_dash_style, send_to_back,
)
from generation.design_engine.palette import PURPLE, NEUTRALS
from generation.diagrams.diagram_primitives import (
    add_textbox, add_icon_placeholder, add_dashed_container,
)

try:
    from images.icon_library import IconLibrary
    _icon_registry = IconLibrary()
except Exception:
    try:
        from images.tech_icon_registry import TechIconRegistry
        _icon_registry = TechIconRegistry()
    except Exception:
        _icon_registry = None


# ── Zone color themes ─────────────────────────────────────────

ZONE_THEMES = {
    "orange": {
        "border": "#E07B20",
        "bg": "#FEF6EE",
        "group_bg": "#FFF8F0",
        "accent": "#D4700F",
        "title": "#C46A18",
        "text": "#FFFFFF",
        "label": "#B85C0A",
        "arrow": "#D4700F",
    },
    "teal": {
        "border": "#0E8B7B",
        "bg": "#EFF9F8",
        "group_bg": "#F0FAF9",
        "accent": "#0D7A6B",
        "title": "#0B7266",
        "text": "#FFFFFF",
        "label": "#0A6459",
        "arrow": "#0D7A6B",
    },
    "blue": {
        "border": "#2574A9",
        "bg": "#EFF5FB",
        "group_bg": "#F2F7FC",
        "accent": "#1F6391",
        "title": "#1E5F8A",
        "text": "#FFFFFF",
        "label": "#1B5680",
        "arrow": "#1F6391",
    },
    "purple": {
        "border": PURPLE.BRAND,
        "bg": PURPLE.BG,
        "group_bg": "#F8F2F7",
        "accent": PURPLE.DEEP,
        "title": PURPLE.BRAND,
        "text": "#FFFFFF",
        "label": PURPLE.BRAND,
        "arrow": PURPLE.BRAND,
    },
    "green": {
        "border": "#1E8449",
        "bg": "#EEF8F2",
        "group_bg": "#F2FAF5",
        "accent": "#1A7840",
        "title": "#196F3D",
        "text": "#FFFFFF",
        "label": "#166B37",
        "arrow": "#1A7840",
    },
    "dark": {
        "border": NEUTRALS.CHARCOAL,
        "bg": "#F5F5F7",
        "group_bg": "#F8F8FA",
        "accent": NEUTRALS.CHARCOAL,
        "title": NEUTRALS.NEAR_BLACK,
        "text": "#FFFFFF",
        "label": NEUTRALS.CHARCOAL,
        "arrow": NEUTRALS.CHARCOAL,
    },
}


class MigrationFlowRenderer:
    """Renders a multi-zone left-to-right architecture flow diagram."""

    def __init__(self, slide, style, diagram_data: dict):
        self.slide = slide
        self.style = style
        self.data = diagram_data

        self.content_left = 0.25
        self.content_top = 1.15
        self.content_width = 12.85
        self.content_height = 6.00
        self.font = style.heading_font if hasattr(style, 'heading_font') else "Arial"
        self.body_font = style.body_font if hasattr(style, 'body_font') else "Arial"

    # ── Public ────────────────────────────────────────────────

    def render(self):
        zones = self.data.get("zones", [])
        bottom_bands = self.data.get("bottom_bands", [])
        journey_labels = self.data.get("journey_labels", [])

        if not zones:
            return

        bottom_h = len(bottom_bands) * 0.38 + (0.06 if bottom_bands else 0)
        journey_h = 0.32 if journey_labels else 0
        zones_h = self.content_height - bottom_h - journey_h

        # Outer container
        outer = add_rounded_rectangle(
            self.slide, self.content_left - 0.08, self.content_top - 0.08,
            self.content_width + 0.16, self.content_height + 0.16,
            fill_color="#F7F8FA", line_color="#E0E2E6", line_width=1.0,
        )
        send_to_back(outer, self.slide)

        arrow_gap = 0.28
        num_arrows = len(zones) - 1
        total_arrow_w = num_arrows * arrow_gap
        zone_spacing = 0.06
        total_spacing = (len(zones) - 1) * zone_spacing
        total_zone_w = self.content_width - total_arrow_w - total_spacing

        ratios = [z.get("width_ratio", 1.0) for z in zones]
        total_ratio = sum(ratios)
        zone_widths = [(r / total_ratio) * total_zone_w for r in ratios]

        x = self.content_left
        zone_positions: list[tuple[float, float]] = []

        for i, zone in enumerate(zones):
            w = zone_widths[i]
            self._draw_zone(zone, x, self.content_top, w, zones_h)
            zone_positions.append((x, w))
            x += w

            if i < len(zones) - 1:
                mid_y = self.content_top + zones_h / 2
                arrow_x = x + zone_spacing / 2
                self._draw_connector_arrow(
                    arrow_x, mid_y, arrow_gap - zone_spacing,
                    zones[i].get("color", "purple"),
                    zones[i + 1].get("color", "purple"),
                )
                x += arrow_gap + zone_spacing

        if journey_labels:
            label_y = self.content_top + zones_h + 0.04
            self._draw_journey_labels(journey_labels, zone_positions,
                                      label_y, arrow_gap + zone_spacing)

        if bottom_bands:
            band_y = self.content_top + zones_h + journey_h + 0.02
            self._draw_bottom_bands(bottom_bands, band_y)

    # ── Zone ──────────────────────────────────────────────────

    def _draw_zone(self, zone: dict, x: float, y: float, w: float, h: float):
        theme = ZONE_THEMES.get(zone.get("color", "purple"), ZONE_THEMES["purple"])
        border_style = zone.get("border_style", "solid")
        pad = 0.08

        # Zone container with colored border
        zone_shape = add_rounded_rectangle(
            self.slide, x, y, w, h,
            fill_color=theme["bg"],
            line_color=theme["border"],
            line_width=1.8,
        )
        if border_style == "dashed":
            set_dash_style(zone_shape, dash="dash",
                           color=theme["border"], width=1.8)

        # Title badge — colored pill at top-center
        title = zone.get("title", "")
        if title:
            title_h = 0.26
            title_w = min(w - 0.16, max(1.2, len(title) * 0.072 + 0.24))
            title_x = x + (w - title_w) / 2
            title_y = y - title_h / 2

            title_bg = add_rounded_rectangle(
                self.slide, title_x, title_y, title_w, title_h,
                fill_color=theme["border"],
            )
            gradient_fill(title_bg, theme["border"],
                          self._darken(theme["border"], 0.15), angle=0)

            add_textbox(self.slide, title_x + 0.06, title_y + 0.03,
                        title_w - 0.12, title_h - 0.06,
                        title, 7.5, "#FFFFFF", bold=True,
                        alignment=PP_ALIGN.CENTER, font_name=self.font)

        # Subtitle/tag (optional)
        subtitle = zone.get("subtitle", "")
        if subtitle:
            sub_w = min(w - 0.2, len(subtitle) * 0.06 + 0.2)
            add_textbox(self.slide, x + w - sub_w - 0.08, y + 0.04,
                        sub_w, 0.18, subtitle, 6, theme["title"],
                        bold=False, font_name=self.body_font)

        groups = zone.get("groups", [])
        if not groups:
            return

        groups_y = y + 0.22
        available_h = h - 0.30
        group_gap = 0.06
        num_groups = len(groups)
        group_h = (available_h - (num_groups - 1) * group_gap) / num_groups
        group_h = min(group_h, 1.8)

        for i, group in enumerate(groups):
            gy = groups_y + i * (group_h + group_gap)
            self._draw_group(group, x + pad, gy, w - pad * 2, group_h, theme)

    # ── Group ─────────────────────────────────────────────────

    def _draw_group(self, group: dict, x: float, y: float, w: float,
                    h: float, theme: dict):
        # Dashed container for group
        grp = add_rounded_rectangle(
            self.slide, x, y, w, h,
            fill_color=theme["group_bg"],
            line_color=theme["border"],
            line_width=0.8,
        )
        set_dash_style(grp, dash="dash", color=theme["border"], width=0.8)
        set_fill_opacity(grp, 0.45)

        label = group.get("label", "")
        label_h = 0.18
        if label:
            add_textbox(self.slide, x + 0.06, y + 0.03, w - 0.12, label_h,
                        label, 6.5, theme["label"], bold=True,
                        font_name=self.font)

        items = group.get("items", [])
        if not items:
            return

        items_y = y + label_h + 0.04
        items_h = h - label_h - 0.10

        style_hint = group.get("style", "text")

        if style_hint == "icons":
            self._draw_item_icons(items, x + 0.06, items_y,
                                  w - 0.12, items_h, theme)
        elif style_hint == "pills" and w >= 1.2:
            self._draw_item_pills(items, x + 0.06, items_y,
                                  w - 0.12, items_h, theme)
        elif style_hint == "flow":
            self._draw_item_flow(items, x + 0.06, items_y,
                                 w - 0.12, items_h, theme)
        else:
            items_text = " · ".join(items)
            add_textbox(self.slide, x + 0.06, items_y, w - 0.12, items_h,
                        items_text, 5.5, NEUTRALS.DARK_GRAY,
                        font_name=self.body_font)

    # ── Icon Items ───────────────────────────────────────────

    def _draw_item_icons(self, items: list, x: float, y: float,
                         w: float, h: float, theme: dict):
        if not items:
            return

        icon_size = 0.40
        label_h = 0.16
        item_total_h = icon_size + label_h + 0.03

        col_w = max(0.58, min(0.90, w / min(len(items), 4)))
        cols = max(1, int(w / col_w))
        remaining_space = w - cols * col_w
        gap_x = remaining_space / max(cols - 1, 1) if cols > 1 else 0

        for i, item_name in enumerate(items):
            col = i % cols
            row = i // cols
            ix = x + col * (col_w + gap_x)
            iy = y + row * (item_total_h + 0.04)

            if iy + item_total_h > y + h:
                break

            self._add_tech_icon(
                ix + (col_w - icon_size) / 2, iy,
                icon_size, item_name, theme,
            )
            add_textbox(self.slide,
                        ix, iy + icon_size + 0.03,
                        col_w, label_h,
                        item_name, 5.5, NEUTRALS.DARK_GRAY,
                        alignment=PP_ALIGN.CENTER,
                        font_name=self.body_font)

    def _add_tech_icon(self, x: float, y: float, size: float,
                       name: str, theme: dict):
        from generation.slide_builders import _resolve_tech_icon
        icon_path = _resolve_tech_icon(name)
        if not icon_path and _icon_registry:
            icon_path = _icon_registry.get_icon(name)

        if icon_path and icon_path.exists():
            try:
                self.slide.shapes.add_picture(
                    str(icon_path),
                    Inches(x), Inches(y),
                    Inches(size), Inches(size),
                )
                return
            except Exception:
                pass

        if _icon_registry:
            abbr, color = _icon_registry.get_fallback(name)
        else:
            words = name.strip().split()
            abbr = "".join(w[0] for w in words[:3]).upper() if len(words) > 1 else name[:3].upper()
            color = theme.get("border", PURPLE.BRAND)

        add_icon_placeholder(self.slide, x, y, size, abbr, color)

    # ── Pill Items ───────────────────────────────────────────

    def _draw_item_pills(self, items: list, x: float, y: float,
                         w: float, h: float, theme: dict):
        pill_h = 0.18
        pill_gap_x = 0.05
        pill_gap_y = 0.04
        # Cap at the full row width, not half of it — a pill only needs to
        # share a row with another if both actually fit; the wrap logic
        # below already moves an oversized pill to its own row. The old
        # half-width cap truncated any single term longer than ~8 chars
        # (e.g. "ExpressRoute", "Deduplication") regardless of room.
        max_pill_w = max(0.5, w - 2 * pill_gap_x)

        px, py = x, y
        for item in items:
            text_len = len(item)
            pill_size = 5.5 if text_len <= 14 else max(4.5, 5.5 - 0.1 * (text_len - 14))
            pill_w = min(max_pill_w, max(0.48, text_len * 0.058 + 0.14))

            if px + pill_w > x + w and px > x:
                px = x
                py += pill_h + pill_gap_y
                if py + pill_h > y + h:
                    break

            add_rounded_rectangle(self.slide, px, py, pill_w, pill_h,
                                  fill_color=theme["border"],
                                  line_color=None)
            add_textbox(self.slide, px + 0.04, py + 0.02,
                        pill_w - 0.08, pill_h - 0.04,
                        item, pill_size, "#FFFFFF", alignment=PP_ALIGN.CENTER,
                        font_name=self.body_font)
            px += pill_w + pill_gap_x

    # ── Flow Items ───────────────────────────────────────────

    def _draw_item_flow(self, items: list, x: float, y: float,
                        w: float, h: float, theme: dict):
        if not items:
            return

        num = len(items)
        arrow_space = 0.12
        total_arrows = (num - 1) * arrow_space
        item_w = (w - total_arrows) / num
        item_h = min(h, 0.22)
        iy = y + (h - item_h) / 2

        for i, item in enumerate(items):
            ix = x + i * (item_w + arrow_space)
            add_rounded_rectangle(self.slide, ix, iy, item_w, item_h,
                                  fill_color=theme["accent"])
            add_textbox(self.slide, ix + 0.03, iy + 0.02,
                        item_w - 0.06, item_h - 0.04,
                        item, 5, "#FFFFFF", alignment=PP_ALIGN.CENTER,
                        font_name=self.body_font)

            if i < num - 1:
                ax = ix + item_w + 0.02
                from generation.design_engine.primitives import add_triangle
                add_triangle(self.slide, ax, iy + item_h / 2 - 0.03,
                             0.06, 0.06, fill_color=theme["accent"],
                             rotation=90)

    # ── Connector Arrows ─────────────────────────────────────

    def _draw_connector_arrow(self, x: float, mid_y: float,
                              gap_w: float,
                              from_color: str, to_color: str):
        """Draw a proper line+arrowhead connector between zones."""
        theme_from = ZONE_THEMES.get(from_color, ZONE_THEMES["purple"])
        arrow_color = theme_from["arrow"]

        line_thickness = 0.025
        line_w = gap_w - 0.14
        line_x = x + 0.02

        if line_w > 0.05:
            add_rectangle(self.slide, line_x, mid_y - line_thickness / 2,
                          line_w, line_thickness, fill_color=arrow_color)

        head_x = line_x + line_w
        head_w = 0.12
        head_h = 0.14
        head = self.slide.shapes.add_shape(
            MSO_SHAPE.ISOSCELES_TRIANGLE,
            Inches(head_x), Inches(mid_y - head_h / 2),
            Inches(head_w), Inches(head_h),
        )
        head.fill.solid()
        head.fill.fore_color.rgb = rgb(arrow_color)
        head.line.fill.background()
        head.rotation = 90

    # ── Journey Labels ────────────────────────────────────────

    def _draw_journey_labels(self, labels: list, zone_positions: list,
                             y: float, arrow_w: float):
        for label_data in labels:
            label = label_data.get("label", "")
            from_idx = label_data.get("from_zone_index", 0)
            to_idx = label_data.get("to_zone_index", len(zone_positions) - 1)

            from_idx = max(0, min(from_idx, len(zone_positions) - 1))
            to_idx = max(0, min(to_idx, len(zone_positions) - 1))

            x_start = zone_positions[from_idx][0]
            to_x, to_w = zone_positions[to_idx]
            x_end = to_x + to_w

            span_w = x_end - x_start
            if span_w < 0.5:
                continue

            bracket_h = 0.02
            bracket_color = NEUTRALS.MID_GRAY

            # Horizontal bar
            add_rectangle(self.slide, x_start, y + 0.10, span_w, bracket_h,
                          fill_color=bracket_color)
            # Left tick
            add_rectangle(self.slide, x_start, y + 0.06, bracket_h, 0.06,
                          fill_color=bracket_color)
            # Right tick
            add_rectangle(self.slide, x_end - bracket_h, y + 0.06, bracket_h, 0.06,
                          fill_color=bracket_color)

            add_textbox(self.slide, x_start, y + 0.14, span_w, 0.16,
                        label, 6, NEUTRALS.DARK_GRAY, bold=True,
                        alignment=PP_ALIGN.CENTER, font_name=self.font)

    # ── Bottom Bands ──────────────────────────────────────────

    def _draw_bottom_bands(self, bands: list, start_y: float):
        band_h = 0.34
        band_gap = 0.04

        for i, band_data in enumerate(bands):
            y = start_y + i * (band_h + band_gap)
            color = band_data.get("color", PURPLE.BRAND)
            if color in ZONE_THEMES:
                color = ZONE_THEMES[color]["border"]

            # Band background
            add_rounded_rectangle(self.slide, self.content_left, y,
                                  self.content_width, band_h,
                                  fill_color="#F0F0F3")

            # Icon if available
            band_icon_name = band_data.get("icon", "")
            icon_rendered = False
            icon_w = 0.28
            if band_icon_name and _icon_registry:
                icon_path = _icon_registry.get_icon(band_icon_name)
                if icon_path and icon_path.exists():
                    try:
                        self.slide.shapes.add_picture(
                            str(icon_path),
                            Inches(self.content_left + 0.08),
                            Inches(y + (band_h - icon_w) / 2),
                            Inches(icon_w), Inches(icon_w),
                        )
                        icon_rendered = True
                    except Exception:
                        pass

            # Label pill — width and font scale with text length so a long
            # governance-style label ("Enterprise Governance & Cross-Cutting
            # Controls") doesn't wrap past the fixed-height band and clip.
            label_text = band_data.get("label", "")
            label_w = min(3.6, max(1.6, len(label_text) * 0.052 + 0.3))
            label_size = 6.5 if len(label_text) <= 24 else max(5, 6.5 - 0.05 * (len(label_text) - 24))
            label_x = self.content_left + (0.42 if icon_rendered else 0.04)
            add_rounded_rectangle(self.slide, label_x,
                                  y + 0.04, label_w, band_h - 0.08,
                                  fill_color=color)
            add_textbox(self.slide, label_x + 0.06,
                        y + (band_h - 0.24) / 2,
                        label_w - 0.12, 0.24,
                        label_text, label_size, "#FFFFFF",
                        bold=True, font_name=self.font)

            # Items
            items = band_data.get("items", [])
            if items:
                items_x = label_x + label_w + 0.12
                items_w = self.content_width - (items_x - self.content_left) - 0.08
                items_text = "  ·  ".join(items)
                add_textbox(self.slide, items_x, y + (band_h - 0.16) / 2,
                            items_w, 0.16, items_text, 6, NEUTRALS.DARK_GRAY,
                            font_name=self.body_font)

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
