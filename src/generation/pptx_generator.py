"""Xebia Proposal PPT Generator — Blueprint-driven dynamic design.

Orchestrates the full pipeline:
  1. Generate a DesignTheme per proposal via Claude (purple spectrum)
  2. Select blueprints for each slide via Claude (30+ visual combinations)
  3. Render blueprint backgrounds/accents, then fill content via builders
  4. Enforce variety constraints (no repetition, balanced dark/light)
  5. Integrate Pexels stock images where available
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generation.design_generator import DesignPalette, SlideStyle
from generation.design_engine.theme_generator import DesignTheme, generate_theme
from generation.design_engine.slide_designer import design_slides, SlideDesignSpec
from generation.design_engine.blueprints import get_blueprint
from generation.design_engine.palette import PURPLE, NEUTRALS
from generation.template_engine import pick_template, get_available_templates

from generation.slide_builders import (
    create_presentation,
    build_cover_slide,
    build_toc_slide,
    build_section_divider,
    build_executive_summary_slide,
    build_content_slide,
    build_content_photo_slide,
    build_two_column_slide,
    build_timeline_slide,
    build_team_slide,
    build_commercials_slide,
    build_closing_slide,
    build_slide_by_layout,
    build_global_presence_slide,
    build_xebia_capabilities_slide,
    build_migration_flow_slide,
)
from images.pexels_client import fetch_slide_image


PHOTO_ELIGIBLE_LAYOUTS = {"content", "two_column", "key_value"}

LAYER_COLOR_MAP = {
    "blue": "blue", "teal": "teal", "purple": "purple",
    "green": "green", "orange": "orange", "red": "orange",
}
ZONE_COLOR_CYCLE = ["orange", "teal", "blue", "purple", "green"]


def _layers_to_migration_flow(layers: list[dict]) -> dict:
    """Convert LLM architecture layers to migration_flow diagram format."""
    zones = []
    for i, layer in enumerate(layers):
        color_name = layer.get("color", "")
        zone_color = LAYER_COLOR_MAP.get(color_name, ZONE_COLOR_CYCLE[i % len(ZONE_COLOR_CYCLE)])

        components = layer.get("components", [])
        groups = [{
            "label": layer.get("name", f"Layer {i+1}"),
            "items": components,
            "style": "icons",
        }]
        zones.append({
            "title": layer.get("name", f"Layer {i+1}"),
            "color": zone_color,
            "groups": groups,
        })

    return {"zones": zones}


def _theme_to_palette(theme: DesignTheme) -> DesignPalette:
    """Bridge: convert DesignTheme to legacy DesignPalette for builders."""
    cycle = theme.accent_cycle or [theme.primary_accent, theme.secondary_accent]
    return DesignPalette(
        primary=theme.primary_accent,
        secondary=theme.secondary_accent,
        accent1=cycle[0] if len(cycle) > 0 else theme.primary_accent,
        accent2=cycle[1] if len(cycle) > 1 else theme.secondary_accent,
        accent3=cycle[2] if len(cycle) > 2 else theme.primary_accent,
        bg_light="#FFFFFF",
        bg_dark=NEUTRALS.BLACK,
        bg_warm=NEUTRALS.OFF_WHITE,
        bg_card=theme.card_fill,
        text_dark=theme.text_heading_light,
        text_medium=theme.text_body_light,
        text_light="#FFFFFF",
    )


def _make_style(theme: DesignTheme, palette: DesignPalette,
                spec: SlideDesignSpec) -> SlideStyle:
    """Create a SlideStyle from a DesignTheme and per-slide spec."""
    bp = get_blueprint(spec.blueprint_id)
    is_dark = bp.is_dark

    return SlideStyle(
        heading_font=theme.heading_font,
        body_font=theme.body_font,
        composition="none",
        accent_color=spec.accent_override or theme.primary_accent,
        card_style=theme.card_style,
        title_color="#FFFFFF" if is_dark else theme.text_heading_light,
        body_color="#D4D4D8" if is_dark else theme.text_body_light,
        card_bg="#2A2A3A" if is_dark else theme.card_fill,
        border_color="#3F3F50" if is_dark else theme.card_border,
        palette=palette,
        blueprint_id=spec.blueprint_id,
        design_theme=theme,
    )


class ProposalPPTGenerator:
    """Generates a complete Xebia-branded PPTX with blueprint-driven design."""

    def __init__(self, plan: dict, template_name: str | None = None,
                 embed_images: list[dict] = None, provider: str = "claude"):
        self.plan = plan
        self.embed_images = embed_images or []
        self.provider = provider

        self._embed_image_paths = {
            img["id"]: img["path"] for img in self.embed_images
            if img.get("path") and Path(img["path"]).exists()
        }
        self._image_placements_by_key: dict[tuple, dict] = {}
        for placement in plan.get("image_placements", []) or []:
            key = (placement.get("section", ""), placement.get("slide_index", 0) or 0)
            self._image_placements_by_key[key] = placement

        tpl = pick_template(template_name)
        self.template_info = tpl
        print(f"[PPTGenerator] Template: {tpl['name']} ({tpl['family']})")

        print(f"[PPTGenerator] Generating design theme via {provider}...")
        self.theme = generate_theme(plan, provider=provider)
        print(f"[PPTGenerator] Theme: {self.theme.theme_name}")
        print(f"[PPTGenerator] Fonts: {self.theme.heading_font}/{self.theme.body_font}, "
              f"card_style={self.theme.card_style}")
        if self.theme.rationale:
            print(f"[PPTGenerator] Rationale: {self.theme.rationale}")

        print(f"[PPTGenerator] Selecting slide blueprints via {provider}...")
        self.specs = design_slides(plan, self.theme, provider=provider)
        bp_ids = [s.blueprint_id for s in self.specs]
        unique = len(set(bp_ids))
        print(f"[PPTGenerator] {len(self.specs)} slides, {unique} unique blueprints")

        self.palette = _theme_to_palette(self.theme)

        from generation.design_generator import ProposalDesignSystem
        self._ds = ProposalDesignSystem(
            palette=self.palette,
            heading_font=self.theme.heading_font,
            body_font=self.theme.body_font,
            card_style=self.theme.card_style,
        )
        self.prs = create_presentation(self._ds, template_path=tpl["path"])

        self._spec_map = {s.slide_id: s for s in self.specs}
        self._spec_index = 0
        self._image_cache: dict[str, str | None] = {}
        self._photo_side_counter = 0
        self._divider_counter = 0

    def _next_spec(self) -> SlideDesignSpec:
        if self._spec_index < len(self.specs):
            spec = self.specs[self._spec_index]
            self._spec_index += 1
            return spec
        fallback = SlideDesignSpec(
            slide_id=f"extra_{self._spec_index}",
            slide_type="content",
            blueprint_id="white_full_accent_line",
            accent_override=self.theme.primary_accent,
        )
        self._spec_index += 1
        return fallback

    def _style_for_spec(self, spec: SlideDesignSpec) -> SlideStyle:
        return _make_style(self.theme, self.palette, spec)

    def _next_slide_num(self) -> int:
        return self._spec_index

    def _fetch_image(self, data: dict, slide_type: str = "content") -> str | None:
        query = data.get("image_query")
        if not query:
            return None
        if query in self._image_cache:
            return self._image_cache[query]
        path = fetch_slide_image(query, slide_type)
        self._image_cache[query] = path
        return path

    def _next_photo_side(self) -> bool:
        self._photo_side_counter += 1
        return self._photo_side_counter % 2 == 0

    def _next_divider_light(self) -> bool:
        self._divider_counter += 1
        return self._divider_counter % 3 == 0

    def _maybe_insert_companion_image(self, section_key: str, slide_index: int, base_title: str):
        """If the plan places a user-uploaded image on this slide, insert it as
        a dedicated photo slide immediately following it — never overlaid onto
        an already-rendered layout, so specialized renders (architecture,
        tables, stat grids) are never disturbed."""
        placement = self._image_placements_by_key.pop((section_key, slide_index), None)
        if not placement:
            return
        image_path = self._embed_image_paths.get(placement.get("image_id"))
        if not image_path:
            return

        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_content_photo_slide(
            self.prs, style,
            title=f"{base_title} — Reference" if base_title else "Reference Image",
            body_text=placement.get("caption", ""),
            image_path=image_path,
            prefer_left=(placement.get("position") == "left"),
            slide_number=self._next_slide_num(),
        )

    def generate(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        storyline = self.plan.get("storyline", [])
        sections = self.plan.get("sections", {})
        xebia_slides_added = False

        for section_key in storyline:
            section_data = sections.get(section_key, {})

            if section_key == "cover":
                self._build_cover(section_data)
            elif section_key == "table_of_contents":
                self._build_toc(section_data)
            elif section_key == "closing":
                self._build_closing(section_data)
            elif section_key == "executive_summary":
                self._build_exec_summary(section_data)
            elif section_key == "timeline":
                self._build_timeline(section_data)
            elif section_key == "team_structure":
                self._build_team(section_data)
            elif section_key == "commercials":
                self._build_commercials(section_data)
            else:
                self._build_content_section(section_key, section_data)

            if section_key == "corporate_overview" and not xebia_slides_added:
                spec = self._next_spec()
                style = self._style_for_spec(spec)
                build_xebia_capabilities_slide(self.prs, style, self._next_slide_num())
                spec = self._next_spec()
                style = self._style_for_spec(spec)
                build_global_presence_slide(self.prs, style, self._next_slide_num())
                xebia_slides_added = True

        self.prs.save(str(output_path))
        print(f"[PPTGenerator] Saved: {output_path} ({self._spec_index} slides)")
        return output_path

    # ── Section builders ──────────────────────────────────────

    def _build_cover(self, data: dict):
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_cover_slide(
            self.prs, style,
            title=data.get("title", self.plan.get("title", "Xebia Proposal")),
            subtitle=data.get("subtitle", self.plan.get("objective", "")),
            customer=data.get("customer", self.plan.get("customer", "")),
            date=data.get("date", ""),
            image_path=self._fetch_image(data, "cover"),
            layout_name=self.template_info.get("cover_layout"),
        )
        self._maybe_insert_companion_image("cover", 0, data.get("title", "Cover"))

    def _build_toc(self, data: dict):
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        storyline = self.plan.get("storyline", [])
        display_names = []
        for s in storyline:
            if s in ("cover", "table_of_contents", "closing"):
                continue
            section_data = self.plan.get("sections", {}).get(s, {})
            name = section_data.get("title", s.replace("_", " ").title())
            display_names.append(name)
        build_toc_slide(self.prs, style, display_names, self._next_slide_num(),
                        layout_name=self.template_info.get("toc_layout"))

    def _build_exec_summary(self, data: dict):
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_section_divider(self.prs, style, data.get("title", "Executive Summary"),
                              self._next_slide_num(),
                              image_path=self._fetch_image(data, "section_divider"),
                              use_light=self._next_divider_light(),
                              layout_name=self.template_info.get("chapter_layout"))

        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_executive_summary_slide(
            self.prs, style,
            title=data.get("title", "Executive Summary"),
            summary_text=data.get("summary", ""),
            key_points=data.get("key_points", []),
            slide_number=self._next_slide_num(),
        )
        self._maybe_insert_companion_image("executive_summary", 0, data.get("title", "Executive Summary"))

    def _build_content_section(self, key: str, data: dict):
        title = data.get("title", key.replace("_", " ").title())

        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_section_divider(self.prs, style, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "section_divider"),
                              use_light=self._next_divider_light(),
                              layout_name=self.template_info.get("chapter_layout"))

        slides = data.get("slides", [])
        if slides:
            for i, slide_data in enumerate(slides):
                layout = slide_data.get("layout")
                image_path = self._fetch_image(slide_data, "content")
                spec = self._next_spec()
                style = self._style_for_spec(spec)
                slide_title = slide_data.get("title", title)

                if layout == "architecture" and slide_data.get("layers"):
                    diagram = _layers_to_migration_flow(slide_data["layers"])
                    build_migration_flow_slide(
                        self.prs, style,
                        title=slide_data.get("title", title),
                        diagram=diagram,
                        slide_number=self._next_slide_num(),
                    )
                elif layout and layout in PHOTO_ELIGIBLE_LAYOUTS and image_path:
                    use_dark = self._photo_side_counter % 4 == 3
                    build_content_photo_slide(
                        self.prs, style,
                        title=slide_title,
                        body_text=slide_data.get("body", ""),
                        bullets=slide_data.get("bullets", []),
                        image_path=image_path,
                        prefer_left=self._next_photo_side(),
                        use_dark=use_dark,
                        slide_number=self._next_slide_num(),
                    )
                elif layout:
                    build_slide_by_layout(
                        self.prs, layout, style, slide_data,
                        slide_number=self._next_slide_num(),
                    )
                else:
                    if image_path:
                        build_content_photo_slide(
                            self.prs, style,
                            title=slide_title,
                            body_text=slide_data.get("body", ""),
                            bullets=slide_data.get("bullets", []),
                            image_path=image_path,
                            prefer_left=self._next_photo_side(),
                            slide_number=self._next_slide_num(),
                        )
                    else:
                        build_content_slide(
                            self.prs, style,
                            title=slide_title,
                            body_text=slide_data.get("body", ""),
                            bullets=slide_data.get("bullets", []),
                            slide_number=self._next_slide_num(),
                        )
                self._maybe_insert_companion_image(key, i, slide_title)
        else:
            layout = data.get("layout")
            spec = self._next_spec()
            style = self._style_for_spec(spec)
            if layout:
                build_slide_by_layout(
                    self.prs, layout, style, data,
                    slide_number=self._next_slide_num(),
                )
            else:
                build_content_slide(
                    self.prs, style,
                    title=title,
                    body_text=data.get("body", ""),
                    bullets=data.get("bullets", []),
                    slide_number=self._next_slide_num(),
                )
            self._maybe_insert_companion_image(key, 0, title)

    def _build_timeline(self, data: dict):
        title = data.get("title", "Timeline")
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_section_divider(self.prs, style, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "timeline"),
                              use_light=self._next_divider_light(),
                              layout_name=self.template_info.get("chapter_layout"))
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_timeline_slide(self.prs, style, title=title,
                             phases=data.get("phases", []),
                             slide_number=self._next_slide_num())
        self._maybe_insert_companion_image("timeline", 0, title)

    def _build_team(self, data: dict):
        title = data.get("title", "Team Structure")
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_section_divider(self.prs, style, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "team"),
                              use_light=self._next_divider_light(),
                              layout_name=self.template_info.get("chapter_layout"))
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_team_slide(self.prs, style, title=title,
                         team_members=data.get("members", []),
                         slide_number=self._next_slide_num())
        self._maybe_insert_companion_image("team_structure", 0, title)

    def _build_commercials(self, data: dict):
        title = data.get("title", "Commercials")
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_section_divider(self.prs, style, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "content"),
                              use_light=self._next_divider_light(),
                              layout_name=self.template_info.get("chapter_layout"))
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_commercials_slide(self.prs, style, title=title,
                                rows=data.get("rows", []),
                                total=data.get("total", ""),
                                assumptions=data.get("assumptions", []),
                                slide_number=self._next_slide_num())
        self._maybe_insert_companion_image("commercials", 0, title)

    def _build_closing(self, data: dict):
        spec = self._next_spec()
        style = self._style_for_spec(spec)
        build_closing_slide(
            self.prs, style,
            title=data.get("title", "Thank You"),
            contact_name=data.get("contact_name", ""),
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            slide_number=self._next_slide_num(),
            image_path=self._fetch_image(data, "closing"),
            layout_name=self.template_info.get("closing_layout"),
        )
        self._maybe_insert_companion_image("closing", 0, data.get("title", "Thank You"))


def generate_proposal_pptx(plan: dict, output_path: str | Path,
                           template_name: str | None = None,
                           embed_images: list[dict] = None,
                           provider: str = "claude") -> Path:
    """Convenience function to generate a PPTX from a plan dict."""
    generator = ProposalPPTGenerator(plan, template_name=template_name,
                                     embed_images=embed_images, provider=provider)
    return generator.generate(output_path)


if __name__ == "__main__":
    import yaml

    if len(sys.argv) < 3:
        print("Usage: python pptx_generator.py <plan.yaml> <output.pptx>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        plan = yaml.safe_load(f)

    out = generate_proposal_pptx(plan, sys.argv[2])
    print(f"Generated: {out}")
