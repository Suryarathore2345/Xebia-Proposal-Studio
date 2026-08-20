"""Service Grid Renderer — categorized technology/service grid slides.

Renders horizontal category rows with colored label bands on the left
and icon+label grids on the right. Used for landing zones, platform
overviews, and technology landscapes.
"""

from __future__ import annotations

from pptx.enum.text import PP_ALIGN

from generation.design_engine.primitives import (
    rgb, add_rounded_rectangle, add_rectangle, set_fill_opacity,
)
from generation.design_engine.palette import PURPLE, NEUTRALS
from generation.diagrams.diagram_primitives import (
    add_textbox, add_icon_placeholder, add_labeled_box,
)


_SHADE_MAP = {
    "light": ("#F5EFF5", PURPLE.SOFT),
    "medium": ("#EDE4ED", PURPLE.MID),
    "dark": ("#D4A5D4", PURPLE.BRAND),
    "deep": ("#B75EB7", PURPLE.DEEP),
}

_SHADE_CYCLE = ["light", "medium", "dark", "deep"]


class ServiceGridRenderer:
    """Renders a categorized service/technology grid on a single slide."""

    def __init__(self, slide, style, diagram_data: dict):
        self.slide = slide
        self.style = style
        self.data = diagram_data

        self.content_left = 0.50
        self.content_top = 1.60
        self.content_width = 12.30
        self.content_height = 5.50
        self.font = style.heading_font if hasattr(style, 'heading_font') else "Arial"
        self.body_font = style.body_font if hasattr(style, 'body_font') else "Arial"

    def render(self):
        subtitle = self.data.get("subtitle", "")
        if subtitle:
            add_textbox(self.slide, self.content_left, self.content_top - 0.30,
                        self.content_width, 0.28, subtitle, 9, "#555555",
                        font_name=self.body_font)

        categories = self.data.get("categories", [])
        bottom_banner = self.data.get("bottom_banner")
        callout = self.data.get("callout")

        banner_h = 0.50 if bottom_banner else 0
        callout_h = 0.55 if callout else 0
        reserved_bottom = banner_h + callout_h + (0.1 if banner_h or callout_h else 0)

        num_cats = len(categories)
        if num_cats == 0:
            return

        available_h = self.content_height - reserved_bottom
        row_gap = 0.08
        row_h = min(1.1, (available_h - (num_cats - 1) * row_gap) / num_cats)
        label_w = 2.0

        for i, cat in enumerate(categories):
            y = self.content_top + i * (row_h + row_gap)
            shade_key = cat.get("color_shade", _SHADE_CYCLE[i % len(_SHADE_CYCLE)])
            bg_color, accent_color = _SHADE_MAP.get(shade_key, _SHADE_MAP["light"])

            self._draw_category_row(cat, y, row_h, label_w, bg_color, accent_color)

        bottom_y = self.content_top + num_cats * (row_h + row_gap)

        if bottom_banner:
            self._draw_bottom_banner(bottom_banner, bottom_y)
            bottom_y += banner_h + 0.08

        if callout:
            self._draw_callout(callout, bottom_y)

    def _draw_category_row(self, cat, y, row_h, label_w, bg_color, accent_color):
        """Draw one horizontal category band with items."""
        row_bg = add_rounded_rectangle(
            self.slide, self.content_left, y,
            self.content_width, row_h,
            fill_color=bg_color,
        )
        set_fill_opacity(row_bg, 0.35)

        add_rounded_rectangle(
            self.slide, self.content_left + 0.06, y + 0.06,
            label_w, row_h - 0.12,
            fill_color=accent_color,
        )
        add_textbox(
            self.slide, self.content_left + 0.12, y + (row_h - 0.22) / 2,
            label_w - 0.12, 0.22,
            cat.get("label", ""), 10, "#FFFFFF",
            bold=True, font_name=self.font,
        )

        items = cat.get("items", [])
        if not items:
            return

        items_x = self.content_left + label_w + 0.25
        items_w = self.content_width - label_w - 0.35
        self._draw_items_row(items, items_x, y, items_w, row_h, accent_color)

    def _draw_items_row(self, items, x_start, y, area_w, row_h, accent_color):
        """Draw a row of icon+label items."""
        num_items = len(items)
        if num_items == 0:
            return

        icon_size = min(0.36, row_h - 0.30)
        item_w = min(1.8, (area_w - (num_items - 1) * 0.12) / num_items)
        gap = (area_w - num_items * item_w) / max(num_items - 1, 1) if num_items > 1 else 0

        for i, item in enumerate(items):
            ix = x_start + i * (item_w + gap)
            icon_label = item.get("icon_label", item.get("name", "?")[:2])

            icon_x = ix + (item_w - icon_size) / 2
            icon_y = y + 0.08
            add_icon_placeholder(self.slide, icon_x, icon_y, icon_size,
                                 icon_label, accent_color)

            name = item.get("name", "")
            label_y = icon_y + icon_size + 0.04
            label_h = row_h - icon_size - 0.18
            if label_h > 0.1:
                add_textbox(self.slide, ix, label_y, item_w, label_h,
                            name, 7, "#333333", alignment=PP_ALIGN.CENTER,
                            font_name=self.body_font)

    def _draw_bottom_banner(self, banner, y):
        """Dark band across the bottom with text."""
        banner_h = 0.45
        style_type = banner.get("style", "dark_band")

        if style_type == "dark_band":
            fill = NEUTRALS.NEAR_BLACK
            text_color = "#FFFFFF"
        else:
            fill = NEUTRALS.COOL_GRAY
            text_color = "#333333"

        add_rounded_rectangle(self.slide, self.content_left, y,
                              self.content_width, banner_h,
                              fill_color=fill)
        add_textbox(self.slide, self.content_left + 0.20, y + 0.08,
                    self.content_width - 0.40, banner_h - 0.16,
                    banner.get("text", ""), 9, text_color,
                    alignment=PP_ALIGN.CENTER, font_name=self.body_font)

    def _draw_callout(self, callout, y):
        """Highlighted callout box."""
        callout_h = 0.50
        style_type = callout.get("style", "highlight_box")

        fill = "#F5EFF5" if style_type == "highlight_box" else "#FFFFFF"
        border = PURPLE.BRAND

        add_rounded_rectangle(self.slide, self.content_left + 0.5, y,
                              self.content_width - 1.0, callout_h,
                              fill_color=fill, line_color=border,
                              line_width=1.5)
        add_textbox(self.slide, self.content_left + 0.70, y + 0.08,
                    self.content_width - 1.40, callout_h - 0.16,
                    callout.get("text", ""), 9, "#333333",
                    alignment=PP_ALIGN.CENTER, font_name=self.body_font)
