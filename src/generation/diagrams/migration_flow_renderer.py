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
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from generation.design_engine.primitives import (
    rgb, add_rounded_rectangle, add_rectangle, gradient_fill,
    set_fill_opacity, set_dash_style, send_to_back, add_right_triangle,
)
from generation.design_engine.palette import PURPLE, NEUTRALS, STAGE
from generation.diagrams.diagram_primitives import (
    add_textbox, add_icon_placeholder, add_dashed_container,
    add_horizontal_arrow,
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

def _stage_zone_theme(stage: "type[STAGE]") -> dict:
    """Build a ZONE_THEMES entry from a palette STAGE.* token — arrow
    color always matches accent for the four pipeline-stage colors."""
    return {
        "border": stage.border, "bg": stage.bg, "group_bg": stage.group_bg,
        "accent": stage.accent, "title": stage.title, "text": "#FFFFFF",
        "label": stage.label, "arrow": stage.accent,
    }


ZONE_THEMES = {
    "orange": _stage_zone_theme(STAGE.ORANGE),
    "teal": _stage_zone_theme(STAGE.TEAL),
    "blue": _stage_zone_theme(STAGE.BLUE),
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
    "green": _stage_zone_theme(STAGE.GREEN),
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


# "tiles" group style geometry — a named tuple of constants shared between
# _estimate_group_h (sizing) and _draw_item_tiles (drawing) so they can't
# drift apart the way icons' plain label_h once did (see the "before" bug
# in migration_flow_renderer's own history: a mismatch here doesn't error,
# it just silently drops content).
_TILE_ICON_SIZE = 0.50
_TILE_MIN_W = 1.35
_TILE_MAX_W = 1.90
# Textbox height needs real text height (bold 7pt ~0.09-0.12in measured via
# PIL) PLUS PowerPoint's own default 0.05in top+bottom margins (confirmed
# via TextFrame.margin_top/bottom) — 0.16in was sized against the font
# size alone and came up short once actually measured.
_TILE_TITLE_H = 0.22
_TILE_SUBTITLE_H = 0.34
_TILE_PAD = 0.10
_TILE_TOTAL_H = _TILE_PAD * 2 + _TILE_ICON_SIZE + 0.04 + _TILE_TITLE_H + _TILE_SUBTITLE_H


def _item_name(item) -> str:
    """Bare technology/service name for icon lookup — a dict item's
    "qualifier" is descriptive context, not part of the product name, so
    it must never be passed to icon resolution."""
    if isinstance(item, dict):
        return item.get("name", "")
    return str(item)


def _icon_label_needs_2_lines(items: list, col_w: float) -> bool:
    """Whether any item's label is long enough to wrap to a 2nd line at
    the compact 5.5pt icon-label size and the given column width. Checks
    actual rendered text length, not just "has a qualifier dict" — a
    plain string the model wrote with its own long parenthetical (e.g.
    "Fabric Pipelines (SSIS Replacement)") needs the same extra room a
    structured qualifier does, confirmed by measuring real generated
    output where exactly this shape of item overflowed."""
    avg_char_w_in = 5.5 * 0.0072
    chars_per_line = max(1, (col_w - 0.06) / avg_char_w_in)
    return any(len(_item_label(it)) > chars_per_line for it in items)


def _item_label(item) -> str:
    """Display label for an item — plain string items render as-is;
    {"name", "qualifier"} items render as "Name · qualifier", matching
    the two-tier labeling convention found in Xebia's own enterprise-grade
    reference decks (e.g. "Delta Lake · Unity Catalog-governed tables")."""
    if isinstance(item, dict):
        name = item.get("name", "")
        qualifier = item.get("qualifier", "")
        return f"{name} · {qualifier}" if qualifier else name
    return str(item)


def _item_subtitle(item) -> str:
    """A dict item's qualifier, used as a standalone second line by the
    "tiles" style (bold title / italic subtitle stacked, rather than
    joined inline with "·") — the same field, a different rendering,
    matching how real reference decks caption a tile like "Lakehouse
    Bronze" with "Typically, Raw & different file formats" underneath."""
    if isinstance(item, dict):
        return item.get("qualifier", "")
    return ""


def _item_accent(item, theme: dict) -> str:
    """Per-item accent override for the "tiles" style (e.g. a medallion
    tier's own color — bronze/silver/gold — rather than the whole zone's
    single theme color); falls back to the zone theme's border color when
    the item doesn't specify one."""
    if isinstance(item, dict):
        accent = item.get("accent")
        if accent:
            return accent
    return theme["border"]


class MigrationFlowRenderer:
    """Renders a multi-zone left-to-right architecture flow diagram."""

    def __init__(self, slide, style, diagram_data: dict):
        self.slide = slide
        self.style = style
        self.data = diagram_data

        self.content_left = 0.25
        # content_top used to be a flat 1.15 constant, which put zone
        # title badges (they straddle content_top, extending ~0.13in
        # above it) directly inside the slide title placeholder's own
        # vertical range — confirmed by measuring real rendered output.
        # But the title placeholder's height varies by template (e.g.
        # xebia_carrington's title bottoms out around y=1.4, xebia_retail
        # and xebia_synapse extend to y=1.84-1.85), so a second flat
        # constant would just be wrong for a different subset of
        # templates. Read the actual title placeholder from this slide
        # instead, and clear its real bottom edge plus a fixed margin.
        self.content_top = self._safe_content_top(slide)
        self.content_width = 12.85
        # Bottom boundary (content_top + content_height) targets ~7.15in,
        # regardless of where content_top landed — a taller title
        # placeholder eats into available diagram height rather than
        # pushing the diagram's bottom edge closer to the slide edge.
        self.content_height = max(3.5, 7.15 - self.content_top)
        self.font = style.heading_font if hasattr(style, 'heading_font') else "Arial"
        self.body_font = style.body_font if hasattr(style, 'body_font') else "Arial"

        # Final drawn bounding box of every zone/item that declares an
        # "id" — populated as _draw_zone/_draw_item_icons/_draw_item_tiles/
        # _draw_item_pills actually place things, consumed by
        # _draw_connections() at the very end of render() once every
        # position is known. A dict on self rather than a value threaded
        # through every draw method's signature, since all of those are
        # already methods of this one renderer instance.
        self.positions: dict[str, tuple[float, float, float, float]] = {}

    @staticmethod
    def _safe_content_top(slide) -> float:
        """Bottom edge of this slide's title placeholder, plus margin —
        falls back to a conservative 1.6in if there's no title
        placeholder (idx 0) to read, or its geometry is missing."""
        margin = 0.20
        fallback = 1.60
        try:
            title_ph = slide.placeholders[0]
            bottom = Emu(title_ph.top).inches + Emu(title_ph.height).inches
            return max(fallback, bottom + margin)
        except Exception:
            return fallback

    def _record_position(self, item_or_zone, x: float, y: float,
                         w: float, h: float):
        """Remember a drawn shape's bounding box under its own "id", if it
        declares one — the raw material _draw_connections() needs to
        connect two specific named things instead of two whole zones."""
        if isinstance(item_or_zone, dict):
            item_id = item_or_zone.get("id")
            if item_id:
                self.positions[item_id] = (x, y, w, h)

    # ── Public ────────────────────────────────────────────────

    def render(self):
        zones = self.data.get("zones", [])
        bottom_bands = self.data.get("bottom_bands", [])
        journey_labels = self.data.get("journey_labels", [])
        legend = self.data.get("legend", [])
        divider = self.data.get("divider")

        if not zones:
            return

        bottom_h = len(bottom_bands) * 0.38 + (0.06 if bottom_bands else 0)
        journey_h = 0.32 if journey_labels else 0
        legend_h = 0.22 if legend else 0
        max_zones_h = self.content_height - bottom_h - journey_h - legend_h

        # Zone height used to be a fixed share of content_height regardless
        # of how much a zone actually holds — a zone with one small group
        # still got the full ~5.5" row, leaving roughly half of it empty
        # with the connector arrows floating in that void. Size the shared
        # row height to whatever the tallest zone's content actually needs,
        # capped by the old budget so it never overflows the slide.
        ratios_preview = [z.get("width_ratio", 1.0) for z in zones]
        total_ratio_preview = sum(ratios_preview) or 1.0
        preview_widths = [(r / total_ratio_preview) *
                          (self.content_width - (len(zones) - 1) * (0.28 + 0.06))
                          for r in ratios_preview]
        natural_h = max(
            (self._estimate_zone_content_h(z, w)
             for z, w in zip(zones, preview_widths)),
            default=max_zones_h,
        )
        zones_h = min(max(natural_h, 1.3), max_zones_h)
        total_h = zones_h + journey_h + bottom_h + legend_h

        # Outer container — sized to what the diagram actually uses, not the
        # old fixed content_height budget, or shrinking the zones above just
        # moves the empty space here instead of removing it.
        outer = add_rounded_rectangle(
            self.slide, self.content_left - 0.08, self.content_top - 0.08,
            self.content_width + 0.16, total_h + 0.16,
            fill_color="#F7F8FA", line_color="#E0E2E6", line_width=1.0,
        )
        send_to_back(outer, self.slide)

        # Small angled corner accent, top-right — matches the branded
        # "framed" look real Xebia reference decks give their architecture
        # diagrams (a plain flat card reads as generic/generated). Drawn
        # right after the outer card and left at the top of the z-order at
        # this point, so it sits above the card's own fill but under every
        # zone/group/item drawn from here on.
        corner_size = 0.42
        corner = add_right_triangle(
            self.slide,
            self.content_left + self.content_width + 0.08 - corner_size,
            self.content_top - 0.08,
            corner_size, corner_size,
            fill_color=PURPLE.SOFT, rotation=180,
        )
        set_fill_opacity(corner, 0.55)

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

        if divider and zone_positions:
            idx = max(0, min(divider.get("position_after_zone", 0),
                             len(zone_positions) - 1))
            zx, zw = zone_positions[idx]
            divider_x = zx + zw + (arrow_gap + zone_spacing) / 2
            self._draw_divider(divider_x, self.content_top, zones_h,
                               divider.get("label", ""))

        if journey_labels:
            label_y = self.content_top + zones_h + 0.04
            self._draw_journey_labels(journey_labels, zone_positions,
                                      label_y, arrow_gap + zone_spacing)

        if bottom_bands:
            band_y = self.content_top + zones_h + journey_h + 0.02
            self._draw_bottom_bands(bottom_bands, band_y)

        if legend:
            legend_y = self.content_top + zones_h + journey_h + bottom_h + 0.04
            self._draw_legend(legend, legend_y)

        connections = self.data.get("connections", [])
        if connections:
            # Only runs after every zone/group/item above has been drawn
            # and recorded its position in self.positions — a connection
            # naming an id that was never drawn (typo, or the item just
            # doesn't exist in this diagram) is silently skipped rather
            # than raising, same tolerance-for-bad-LLM-output posture as
            # the rest of this renderer.
            self._draw_connections(connections)

    # ── Content-height estimation ────────────────────────────

    def _estimate_group_h(self, group: dict, group_w: float) -> float:
        """Natural height a group needs for its label + items, before padding."""
        label_h = 0.18 if group.get("label") else 0.0
        items = group.get("items", [])
        avail_w = max(0.3, group_w - 0.12)
        style_hint = group.get("style", "text")

        if not items:
            items_h = 0.0
        elif style_hint == "icons":
            # Mirrors _draw_item_icons's row-height logic so the zone/
            # group budget this feeds actually accounts for the extra
            # room a long item needs — otherwise the fix in
            # _draw_item_icons just moves the overflow into the group's
            # own boundary instead of removing it.
            col_w = max(0.58, min(0.90, avail_w / min(len(items), 4)))
            item_total_h = 0.40 + (0.30 if _icon_label_needs_2_lines(items, col_w) else 0.16) + 0.03
            cols = max(1, int(avail_w / col_w))
            rows = -(-len(items) // cols)
            items_h = rows * item_total_h
        elif style_hint == "pills":
            pill_h, gap_x = 0.18, 0.05
            max_pill_w = max(0.5, avail_w - 2 * gap_x)
            px, rows = 0.0, 1
            for item in items:
                pill_w = min(max_pill_w, max(0.48, len(_item_label(item)) * 0.058 + 0.14))
                if px + pill_w > avail_w and px > 0:
                    rows += 1
                    px = 0.0
                px += pill_w + gap_x
            items_h = rows * pill_h + (rows - 1) * 0.04
        elif style_hint == "flow":
            items_h = 0.22
        elif style_hint == "tiles":
            # Mirrors _draw_item_tiles's own geometry exactly — same
            # lesson as the "icons" branch above, this budget is what
            # _draw_group sizes the card from, so it has to match what
            # gets drawn or the fix just moves the overflow elsewhere.
            col_w = max(_TILE_MIN_W, min(_TILE_MAX_W, avail_w / min(len(items), 3)))
            cols = max(1, int(avail_w / col_w))
            rows = -(-len(items) // cols)
            items_h = rows * _TILE_TOTAL_H
        else:
            items_h = 0.20

        return label_h + (0.04 if label_h and items_h else 0) + items_h

    def _estimate_zone_content_h(self, zone: dict, zone_w: float) -> float:
        """Total height a zone's title + groups actually need, plus padding."""
        children = zone.get("children")
        if children:
            n = len(children)
            ratios = [c.get("width_ratio", 1.0) for c in children]
            total_ratio = sum(ratios) or 1.0
            avail_w = max(0.2, zone_w - 0.16 - (n - 1) * 0.08)
            child_widths = [(r / total_ratio) * avail_w for r in ratios]
            inner_h = max(
                (self._estimate_zone_content_h(c, cw)
                 for c, cw in zip(children, child_widths)),
                default=1.0,
            )
            return 0.30 + inner_h + 0.08  # this level's title/pad overhead

        groups = zone.get("groups", [])
        if not groups:
            return 1.3

        pad = 0.12
        inner_w = zone_w - pad * 2
        group_gap = 0.06
        group_heights = [max(0.35, self._estimate_group_h(g, inner_w) + 0.10)
                         for g in groups]
        return 0.22 + sum(group_heights) + (len(groups) - 1) * group_gap + pad

    # ── Zone ──────────────────────────────────────────────────

    def _draw_zone(self, zone: dict, x: float, y: float, w: float, h: float):
        theme = ZONE_THEMES.get(zone.get("color", "purple"), ZONE_THEMES["purple"])
        # A zone with a "boundary_type" (subscription/vnet/workspace) is an
        # administrative/logical boundary, not a deployed component, so it
        # defaults to a dashed border — matching the dashed=boundary /
        # solid=component convention consistently used across Xebia's own
        # reference decks (never the other way around). An explicit
        # "border_style" always wins over the boundary_type default.
        boundary_type = zone.get("boundary_type", "none")
        border_style = zone.get("border_style") or (
            "dashed" if boundary_type != "none" else "solid")
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
        self._record_position(zone, x, y, w, h)

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

        # Nested boundary zones (subscription > VNet > subnet, etc.) —
        # z-order + inset sizing reproduces real reference decks' visual
        # nesting without a general recursive layout engine (§2.2): a
        # single child reads as a smaller inset box (the concentric
        # "subscription containing a VNet" look), multiple children read
        # as adjacent named strips (the "Identity sub | Connectivity sub |
        # Landing Zone sub" look) — same mechanism, just child count.
        children = zone.get("children")
        if children:
            self._draw_children(children, x + pad, y + 0.30,
                                w - pad * 2, h - 0.30 - pad)
            return

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

    def _draw_children(self, children: list, x: float, y: float,
                       w: float, h: float):
        """Lay out nested child zones side-by-side within a parent
        boundary, recursing through _draw_zone so each child can itself
        have further children (arbitrary nesting depth), groups, or both."""
        n = len(children)
        if n == 0:
            return
        gap = 0.08
        ratios = [c.get("width_ratio", 1.0) for c in children]
        total_ratio = sum(ratios) or 1.0
        total_gap = (n - 1) * gap
        avail_w = max(0.2, w - total_gap)

        cx = x
        for child, ratio in zip(children, ratios):
            cw = (ratio / total_ratio) * avail_w
            self._draw_zone(child, cx, y, cw, h)
            cx += cw + gap

    # ── Group ─────────────────────────────────────────────────

    def _draw_group(self, group: dict, x: float, y: float, w: float,
                    h: float, theme: dict):
        # Solid container for group — a group holds actual deployed
        # components, not an administrative/logical boundary. Reference
        # architecture decks consistently use dashed borders ONLY for
        # boundary-type containers (subscription/VNet/workspace/on-prem
        # divider) and solid for everything that's a real component; a
        # group of icons/pills is the latter, so it defaults to solid.
        # A group can still opt into a dashed boundary look via
        # "border_style": "dashed" when it genuinely represents one.
        #
        # The card is drawn at its own natural content height, capped to
        # the slice `h` it was allotted — not always stretched to fill
        # that whole slice. `_draw_zone` divides a zone's height evenly
        # across however many groups it has regardless of how much
        # content each one holds, so a 2-item group next to a
        # content-dense one used to get a card 30%+ taller than its
        # content needed (confirmed by measuring real generated output).
        # `h` itself — the slice — is untouched, so later groups in this
        # zone still start where they always did; only this card's own
        # drawn height shrinks to fit.
        natural_h = self._estimate_group_h(group, w)
        card_h = max(0.35, min(h, natural_h + 0.10))

        grp = add_rounded_rectangle(
            self.slide, x, y, w, card_h,
            fill_color=theme["group_bg"],
            line_color=theme["border"],
            line_width=0.8,
        )
        if group.get("border_style") == "dashed":
            set_dash_style(grp, dash="dash", color=theme["border"], width=0.8)
        set_fill_opacity(grp, 0.45)

        label = group.get("label", "")
        # Must match _estimate_group_h's label_h exactly (0 when there's no
        # label) — that function is what card_h was sized from, so
        # reserving 0.18 here unconditionally silently ate into the items
        # area on any label-less group, shrinking items_h below what
        # _draw_item_icons' own per-row math needs and making it break
        # out on the very first row (zero items drawn, no error, no
        # placeholder — the card just renders empty).
        label_h = 0.18 if label else 0.0
        if label:
            add_textbox(self.slide, x + 0.06, y + 0.03, w - 0.12, label_h,
                        label, 6.5, theme["label"], bold=True,
                        font_name=self.font)

        items = group.get("items", [])
        if not items:
            return

        items_y = y + label_h + 0.04
        items_h = card_h - label_h - 0.10

        style_hint = group.get("style", "text")

        if style_hint == "icons":
            self._draw_item_icons(items, x + 0.06, items_y,
                                  w - 0.12, items_h, theme)
        elif style_hint == "tiles":
            self._draw_item_tiles(items, x + 0.06, items_y,
                                  w - 0.12, items_h, theme)
        elif style_hint == "pills" and w >= 1.2:
            self._draw_item_pills(items, x + 0.06, items_y,
                                  w - 0.12, items_h, theme)
        elif style_hint == "flow":
            self._draw_item_flow(items, x + 0.06, items_y,
                                 w - 0.12, items_h, theme)
        else:
            items_text = "  ·  ".join(_item_label(i) for i in items)
            add_textbox(self.slide, x + 0.06, items_y, w - 0.12, items_h,
                        items_text, 5.5, NEUTRALS.DARK_GRAY,
                        font_name=self.body_font)

    # ── Icon Items ───────────────────────────────────────────

    def _draw_item_icons(self, items: list, x: float, y: float,
                         w: float, h: float, theme: dict):
        if not items:
            return

        icon_size = 0.40
        col_w = max(0.58, min(0.90, w / min(len(items), 4)))
        # Grow the whole grid's row height when ANY item's label is long
        # enough to wrap at this column width, so rows stay aligned —
        # plain short items keep the original compact height otherwise.
        label_h = 0.30 if _icon_label_needs_2_lines(items, col_w) else 0.16
        item_total_h = icon_size + label_h + 0.03

        cols = max(1, int(w / col_w))
        remaining_space = w - cols * col_w
        gap_x = remaining_space / max(cols - 1, 1) if cols > 1 else 0

        for i, item in enumerate(items):
            col = i % cols
            row = i // cols
            ix = x + col * (col_w + gap_x)
            iy = y + row * (item_total_h + 0.04)

            if iy + item_total_h > y + h:
                break

            self._add_tech_icon(
                ix + (col_w - icon_size) / 2, iy,
                icon_size, _item_name(item), theme,
            )
            add_textbox(self.slide,
                        ix, iy + icon_size + 0.03,
                        col_w, label_h,
                        _item_label(item), 5.5, NEUTRALS.DARK_GRAY,
                        alignment=PP_ALIGN.CENTER,
                        font_name=self.body_font)
            self._record_position(item, ix, iy, col_w, item_total_h)

    # ── Tile Items ───────────────────────────────────────────

    def _draw_item_tiles(self, items: list, x: float, y: float,
                         w: float, h: float, theme: dict):
        """Icon-top / bold-title / italic-subtitle cards, each with its own
        light background and an optional per-item accent color — the
        "Lakehouse Bronze / Typically, Raw & different file formats" style
        tile found in Xebia's own reference decks (MOHESR slide 16), for
        a handful of named, individually-captioned things (medallion tiers,
        environment stages) rather than a dense icon grid of many peers."""
        if not items:
            return

        col_w = max(_TILE_MIN_W, min(_TILE_MAX_W, w / min(len(items), 3)))
        cols = max(1, int(w / col_w))
        remaining_space = w - cols * col_w
        gap_x = remaining_space / max(cols - 1, 1) if cols > 1 else 0

        for i, item in enumerate(items):
            col = i % cols
            row = i // cols
            tx = x + col * (col_w + gap_x)
            ty = y + row * (_TILE_TOTAL_H + 0.04)

            if ty + _TILE_TOTAL_H > y + h:
                break

            accent = _item_accent(item, theme)
            tile_w = col_w - 0.06
            add_rounded_rectangle(
                self.slide, tx, ty, tile_w, _TILE_TOTAL_H,
                fill_color="#FFFFFF", line_color=accent, line_width=1.0,
            )

            icon_x = tx + (tile_w - _TILE_ICON_SIZE) / 2
            self._add_tech_icon(icon_x, ty + _TILE_PAD, _TILE_ICON_SIZE,
                                _item_name(item), {"border": accent})

            title_y = ty + _TILE_PAD + _TILE_ICON_SIZE + 0.04
            add_textbox(self.slide, tx + 0.04, title_y, tile_w - 0.08,
                        _TILE_TITLE_H, _item_name(item), 7, accent,
                        bold=True, alignment=PP_ALIGN.CENTER,
                        font_name=self.font)

            subtitle = _item_subtitle(item)
            if subtitle:
                sub_box = add_textbox(
                    self.slide, tx + 0.05, title_y + _TILE_TITLE_H,
                    tile_w - 0.10, _TILE_SUBTITLE_H,
                    subtitle, 5.5, NEUTRALS.MID_GRAY,
                    alignment=PP_ALIGN.CENTER, font_name=self.body_font,
                )
                for para in sub_box.text_frame.paragraphs:
                    para.font.italic = True

            self._record_position(item, tx, ty, tile_w, _TILE_TOTAL_H)

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
            label = _item_label(item)
            text_len = len(label)
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
                        label, pill_size, "#FFFFFF", alignment=PP_ALIGN.CENTER,
                        font_name=self.body_font)
            self._record_position(item, px, py, pill_w, pill_h)
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
                        _item_label(item), 5, "#FFFFFF", alignment=PP_ALIGN.CENTER,
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

    # ── Named Connections ─────────────────────────────────────

    @staticmethod
    def _pick_anchor_points(box_a: tuple, box_b: tuple) -> tuple:
        """Pick the pair of edge-midpoints on two boxes that face each
        other, so the connector runs the short way round instead of
        crossing back through either box. box_* are (x, y, w, h)."""
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        a_cx, a_cy = ax + aw / 2, ay + ah / 2
        b_cx, b_cy = bx + bw / 2, by + bh / 2
        dx, dy = b_cx - a_cx, b_cy - a_cy

        if abs(dy) >= abs(dx):
            # Predominantly vertical relationship — connect top/bottom edges.
            if dy >= 0:
                return (a_cx, ay + ah), (b_cx, by)
            return (a_cx, ay), (b_cx, by + bh)
        # Predominantly horizontal — connect left/right edges.
        if dx >= 0:
            return (ax + aw, a_cy), (bx, b_cy)
        return (ax, a_cy), (bx + bw, b_cy)

    def _draw_connections(self, connections: list):
        """Elbow-routed connectors between two specifically-named,
        already-drawn items/zones — for the occasional real, named
        relationship a diagram needs beyond its normal zone-to-zone flow
        (e.g. a medallion tier feeding an MDM step, matching how MOHESR
        slide 16's own "Silver -> MDM" and "MDM -> Gold" connectors work).
        Deliberately plain lines with no arrowhead: the reference-deck
        audit found unarrowed lines are actually the MORE common notation
        for this kind of cross-cutting/callout relationship, real directed
        arrows being reserved for the main data-flow direction, which the
        normal zone-to-zone arrows already cover."""
        for conn in connections:
            from_id = conn.get("from")
            to_id = conn.get("to")
            box_a = self.positions.get(from_id)
            box_b = self.positions.get(to_id)
            if not box_a or not box_b:
                continue

            (x1, y1), (x2, y2) = self._pick_anchor_points(box_a, box_b)
            color = conn.get("color") or NEUTRALS.MID_GRAY
            connector = self.slide.shapes.add_connector(
                MSO_CONNECTOR.ELBOW,
                Inches(x1), Inches(y1), Inches(x2), Inches(y2),
            )
            connector.line.color.rgb = rgb(color)
            connector.line.width = Pt(1.0)

            label = conn.get("label", "")
            if label:
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                label_w = max(0.5, len(label) * 0.05 + 0.1)
                add_textbox(self.slide, mid_x - label_w / 2, mid_y - 0.09,
                           label_w, 0.16, label, 5.5, color,
                           alignment=PP_ALIGN.CENTER, font_name=self.body_font)

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

            # Items — discrete boxes, one per named item, not a joined text
            # string. Reference architecture decks consistently render
            # cross-cutting governance/security items ("Purview", "Key
            # Vault", "Entra ID"...) as equally-spaced individual boxes
            # inside the band, not a comma/dot-separated line of text.
            items = band_data.get("items", [])
            if items:
                items_x = label_x + label_w + 0.12
                items_w = self.content_width - (items_x - self.content_left) - 0.08
                n = len(items)
                gap = 0.06
                item_w = min(2.2, max(0.5, (items_w - (n - 1) * gap) / n))
                item_h = band_h - 0.14
                iy = y + 0.07
                for i, item in enumerate(items):
                    ix = items_x + i * (item_w + gap)
                    if ix + item_w > items_x + items_w + 0.02:
                        break
                    add_rounded_rectangle(self.slide, ix, iy, item_w, item_h,
                                          fill_color="#FFFFFF",
                                          line_color=color, line_width=0.75)
                    label = _item_label(item)
                    size = 6 if len(label) <= 16 else max(4.5, 6 - 0.08 * (len(label) - 16))
                    add_textbox(self.slide, ix + 0.03, iy + (item_h - 0.16) / 2,
                                item_w - 0.06, 0.16, label, size,
                                NEUTRALS.DARK_GRAY, alignment=PP_ALIGN.CENTER,
                                font_name=self.body_font)

    # ── Legend ────────────────────────────────────────────────

    def _draw_legend(self, legend: list, y: float):
        """Bottom-left swatch + label row explaining the diagram's own
        notation (e.g. dashed border = subscription/VNet boundary, solid
        line = data flow). Only 2 of 16 audited Xebia reference decks use
        a legend, but both are the most polished ("enterprise-grade")
        diagrams in the corpus — cheap to add, add it only when the
        diagram actually mixes boundary types or flow semantics, not by
        default on every diagram."""
        x = self.content_left + 0.06
        swatch_w = 0.28
        color = NEUTRALS.DARK_GRAY

        for entry in legend:
            symbol = entry.get("symbol", "solid")
            label = entry.get("label", "")
            mid_y = y + 0.08

            if symbol == "dashed":
                for tx in (x, x + 0.10, x + 0.20):
                    add_rectangle(self.slide, tx, mid_y - 0.01, 0.05, 0.02,
                                 fill_color=color)
            elif symbol == "arrow":
                add_horizontal_arrow(self.slide, x, mid_y, x + swatch_w,
                                     color=color, thickness=0.02)
            else:  # "solid" / "line" / default
                add_rectangle(self.slide, x, mid_y - 0.01, swatch_w, 0.02,
                              fill_color=color)

            label_x = x + swatch_w + 0.06
            label_w = max(0.4, len(label) * 0.045 + 0.1)
            add_textbox(self.slide, label_x, y, label_w, 0.18,
                        label, 6, color, font_name=self.body_font)
            x = label_x + label_w + 0.22

    # ── Divider ───────────────────────────────────────────────

    def _draw_divider(self, x: float, y: float, h: float, label: str = ""):
        """Vertical dashed divider line spanning the zones area — e.g. an
        on-prem/Azure split. Reference decks (MOHESR slide 15) use exactly
        this: a bare dashed line, not a container, to separate two regions
        that don't otherwise get their own zone boundary."""
        connector = self.slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x), Inches(y + h),
        )
        set_dash_style(connector, dash="dash", color=NEUTRALS.MID_GRAY, width=1.25)

        if label:
            label_w = 1.3
            add_textbox(self.slide, x - label_w / 2, y - 0.20, label_w, 0.16,
                        label, 6, NEUTRALS.MID_GRAY, alignment=PP_ALIGN.CENTER,
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
