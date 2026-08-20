"""Architecture Diagram Renderer — multi-zone reference architecture slides.

Renders nested dashed-border containers, source/sink columns,
medallion flow nodes, directional arrows, and governance bands.
"""

from __future__ import annotations

from pptx.enum.text import PP_ALIGN

from generation.design_engine.primitives import rgb, add_rounded_rectangle
from generation.design_engine.palette import PURPLE, NEUTRALS
from generation.diagrams.diagram_primitives import (
    add_textbox, add_dashed_container, add_icon_placeholder,
    add_horizontal_arrow, add_vertical_arrow, add_labeled_box,
    add_band,
)


_PURPLE_CYCLE = [
    PURPLE.BRAND, PURPLE.LIGHT, PURPLE.MID, PURPLE.MUTED,
    PURPLE.DEEP, PURPLE.SOFT,
]


class ArchitectureDiagramRenderer:
    """Renders a multi-zone architecture diagram on a single slide."""

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

        self._node_positions: dict[str, tuple[float, float]] = {}

    def render(self):
        columns = self.data.get("columns", [])
        bottom_bands = self.data.get("bottom_bands", [])
        zones = self.data.get("zones", [])
        flow_nodes = self.data.get("flow_nodes", [])

        has_left_col = any(c.get("position") == "left" for c in columns)
        has_right_col = any(c.get("position") == "right" for c in columns)

        left_col_w = 2.0 if has_left_col else 0
        right_col_w = 2.0 if has_right_col else 0
        bottom_h = len(bottom_bands) * 0.55 + (0.1 if bottom_bands else 0)

        center_left = self.content_left + left_col_w + (0.15 if has_left_col else 0)
        center_width = (self.content_width - left_col_w - right_col_w
                        - (0.15 if has_left_col else 0)
                        - (0.15 if has_right_col else 0))
        center_height = self.content_height - bottom_h

        if zones:
            self._draw_zones(zones, center_left, self.content_top,
                             center_width, center_height)

        if flow_nodes:
            self._draw_flow_nodes(flow_nodes, center_left, self.content_top,
                                  center_width, center_height, len(zones))

        if has_left_col:
            left_col = next(c for c in columns if c.get("position") == "left")
            self._draw_column(left_col, self.content_left, self.content_top,
                              left_col_w, center_height)

        if has_right_col:
            right_col = next(c for c in columns if c.get("position") == "right")
            right_x = self.content_left + self.content_width - right_col_w
            self._draw_column(right_col, right_x, self.content_top,
                              right_col_w, center_height)

        connections = self.data.get("connections", [])
        if connections:
            self._draw_connections(connections, has_left_col, has_right_col,
                                   center_left, center_width)

        if bottom_bands:
            band_y = self.content_top + center_height + 0.10
            self._draw_bottom_bands(bottom_bands, band_y)

    def _draw_zones(self, zones, x, y, w, h, depth=0):
        """Draw nested dashed-border containers."""
        if not zones:
            return

        padding = 0.12
        label_h = 0.30

        for i, zone in enumerate(zones):
            zone_id = zone.get("id", f"zone_{i}")
            label = zone.get("label", "")
            color_hint = zone.get("color", "accent")

            border_color = PURPLE.BRAND if color_hint == "accent" else PURPLE.MUTED
            fill = "#FAFAFF" if depth == 0 else None

            add_dashed_container(
                self.slide, x + padding, y + padding,
                w - padding * 2, h - padding * 2,
                label=label, border_color=border_color,
                fill_color=fill, font_name=self.font,
            )

            children = zone.get("children", [])
            if children:
                child_y = y + padding + label_h
                child_h = h - padding * 2 - label_h
                self._draw_zones(children, x + padding, child_y,
                                 w - padding * 2, child_h, depth + 1)

    def _draw_flow_nodes(self, nodes, cx, cy, cw, ch, zone_depth):
        """Draw medallion-style flow nodes horizontally across the center zone."""
        num_nodes = len(nodes)
        if num_nodes == 0:
            return

        inset = 0.25 + zone_depth * 0.12
        area_left = cx + inset + 0.1
        area_width = cw - inset * 2 - 0.2

        node_w = min(1.6, (area_width - (num_nodes - 1) * 0.20) / num_nodes)
        node_h = 0.70
        gap = (area_width - num_nodes * node_w) / max(num_nodes - 1, 1)

        nodes_y = cy + ch * 0.45

        for i, node in enumerate(nodes):
            nx = area_left + i * (node_w + gap)

            style_type = node.get("style", "medallion")
            color_idx = i % len(_PURPLE_CYCLE)
            fill = _PURPLE_CYCLE[color_idx]

            add_rounded_rectangle(self.slide, nx, nodes_y, node_w, node_h,
                                  fill_color=fill,
                                  line_color=PURPLE.DEEP, line_width=1)
            add_textbox(self.slide, nx + 0.05, nodes_y + 0.08,
                        node_w - 0.10, 0.25,
                        node.get("label", ""), 9, "#FFFFFF",
                        bold=True, alignment=PP_ALIGN.CENTER,
                        font_name=self.font)

            subtitle = node.get("subtitle", "")
            if subtitle:
                add_textbox(self.slide, nx + 0.05, nodes_y + 0.35,
                            node_w - 0.10, 0.30,
                            subtitle, 7, "#E0E0E0",
                            alignment=PP_ALIGN.CENTER,
                            font_name=self.body_font)

            node_id = node.get("id", f"node_{i}")
            self._node_positions[node_id] = (nx + node_w / 2, nodes_y + node_h / 2)

            if i < num_nodes - 1:
                arrow_start_x = nx + node_w + 0.02
                arrow_end_x = area_left + (i + 1) * (node_w + gap) - 0.02
                if arrow_end_x - arrow_start_x > 0.15:
                    add_horizontal_arrow(self.slide, arrow_start_x,
                                         nodes_y + node_h / 2,
                                         arrow_end_x, color=PURPLE.MUTED)

    def _draw_column(self, col_data, x, y, w, h):
        """Draw a source/sink column with stacked items."""
        label = col_data.get("label", "")
        items = col_data.get("items", [])

        add_textbox(self.slide, x + 0.05, y, w - 0.10, 0.25,
                    label, 8, self.style.title_color, bold=True,
                    alignment=PP_ALIGN.CENTER, font_name=self.font)

        num_items = len(items)
        if num_items == 0:
            return

        item_area_top = y + 0.30
        item_area_h = h - 0.35
        item_h = min(0.60, (item_area_h - (num_items - 1) * 0.08) / num_items)
        item_gap = (item_area_h - num_items * item_h) / max(num_items - 1, 1) if num_items > 1 else 0

        for i, item in enumerate(items):
            iy = item_area_top + i * (item_h + item_gap)
            icon_label = item.get("icon_label", item.get("name", "?")[:2])
            color_idx = i % len(_PURPLE_CYCLE)

            icon_size = min(0.35, item_h - 0.08)
            icon_x = x + 0.10
            icon_y = iy + (item_h - icon_size) / 2
            add_icon_placeholder(self.slide, icon_x, icon_y, icon_size,
                                 icon_label, _PURPLE_CYCLE[color_idx])

            text_x = icon_x + icon_size + 0.08
            text_w = w - icon_size - 0.30
            add_textbox(self.slide, text_x, iy + 0.04, text_w, 0.20,
                        item.get("name", ""), 8, self.style.title_color,
                        bold=True, font_name=self.body_font)

            subtitle = item.get("subtitle", "")
            if subtitle and item_h > 0.35:
                add_textbox(self.slide, text_x, iy + 0.24, text_w, 0.20,
                            subtitle, 6, "#666666", font_name=self.body_font)

        col_id = col_data.get("position", "col")
        mid_y = y + h / 2
        self._node_positions[col_id] = (x + w / 2, mid_y)
        if col_data.get("position") == "left":
            self._node_positions["sources"] = (x + w, mid_y)
        elif col_data.get("position") == "right":
            self._node_positions["serve"] = (x, mid_y)

    def _draw_connections(self, connections, has_left, has_right,
                          center_left, center_width):
        """Draw arrows between named nodes/columns."""
        for conn in connections:
            from_id = conn.get("from", "")
            to_id = conn.get("to", "")
            color = conn.get("color", PURPLE.MUTED)
            if color == "red":
                color = "#C00000"
            elif color == "blue":
                color = PURPLE.BRAND

            from_pos = self._node_positions.get(from_id)
            to_pos = self._node_positions.get(to_id)
            if not from_pos or not to_pos:
                continue

            if abs(from_pos[1] - to_pos[1]) < 0.3:
                add_horizontal_arrow(self.slide, from_pos[0], from_pos[1],
                                     to_pos[0], color=color)
            else:
                add_vertical_arrow(self.slide, from_pos[0], from_pos[1],
                                   to_pos[1], color=color)

    def _draw_bottom_bands(self, bands, start_y):
        """Draw governance/security bands at the bottom."""
        band_h = 0.48
        band_gap = 0.06

        for i, band_data in enumerate(bands):
            y = start_y + i * (band_h + band_gap)
            color_idx = i % len(_PURPLE_CYCLE)
            add_band(
                self.slide, self.content_left, y,
                self.content_width, band_h,
                label=band_data.get("label", ""),
                items=band_data.get("items"),
                description=band_data.get("description", ""),
                fill_color=NEUTRALS.COOL_GRAY,
                accent_color=_PURPLE_CYCLE[color_idx],
                font_name=self.font,
            )
