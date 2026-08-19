"""Xebia Proposal PPT Generator.

Takes a structured proposal plan (dict/YAML) and generates a complete
Xebia-branded PPTX deck by dispatching each section to the appropriate
slide builder.
"""

from pathlib import Path
from pptx.util import Inches

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generation.slide_builders import (
    create_presentation,
    get_active_theme,
    build_cover_slide,
    build_toc_slide,
    build_section_divider,
    build_executive_summary_slide,
    build_content_slide,
    build_two_column_slide,
    build_timeline_slide,
    build_team_slide,
    build_commercials_slide,
    build_closing_slide,
    build_slide_by_layout,
    build_global_presence_slide,
    build_xebia_capabilities_slide,
)
from images.pexels_client import fetch_slide_image


SECTION_BUILDERS = {
    "cover": "_build_cover",
    "table_of_contents": "_build_toc",
    "executive_summary": "_build_exec_summary",
    "corporate_overview": "_build_content_section",
    "understanding_of_scope": "_build_content_section",
    "proposed_solution": "_build_content_section",
    "architecture": "_build_content_section",
    "technology_stack": "_build_content_section",
    "delivery_approach": "_build_content_section",
    "timeline": "_build_timeline",
    "team_structure": "_build_team",
    "commercials": "_build_commercials",
    "risk_mitigation": "_build_content_section",
    "case_studies": "_build_content_section",
    "next_steps": "_build_content_section",
    "closing": "_build_closing",
}


class ProposalPPTGenerator:
    """Generates a complete Xebia-branded PPTX from a proposal plan."""

    def __init__(self, plan: dict):
        self.plan = plan
        proposal_context = {
            "industry": plan.get("industry", ""),
            "customer": plan.get("customer", ""),
            "title": plan.get("title", ""),
        }
        self.prs = create_presentation(proposal_context)
        self.theme = get_active_theme()
        self.slide_number = 0
        self._image_cache: dict[str, str | None] = {}

    def _fetch_image(self, data: dict, slide_type: str = "content") -> str | None:
        query = data.get("image_query")
        if not query:
            return None
        if query in self._image_cache:
            return self._image_cache[query]
        path = fetch_slide_image(query, slide_type)
        self._image_cache[query] = path
        return path

    def generate(self, output_path: str | Path) -> Path:
        """Generate the full deck and save to output_path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        storyline = self.plan.get("storyline", [])
        sections = self.plan.get("sections", {})

        xebia_slides_added = False

        for section_key in storyline:
            section_data = sections.get(section_key, {})
            builder_name = SECTION_BUILDERS.get(section_key, "_build_content_section")
            builder = getattr(self, builder_name)
            builder(section_key, section_data)

            if section_key == "corporate_overview" and not xebia_slides_added:
                build_xebia_capabilities_slide(self.prs, self._next_slide_num())
                build_global_presence_slide(self.prs, self._next_slide_num())
                xebia_slides_added = True

        self.prs.save(str(output_path))
        return output_path

    def _next_slide_num(self) -> int:
        self.slide_number += 1
        return self.slide_number

    def _build_cover(self, key: str, data: dict):
        build_cover_slide(
            self.prs,
            title=data.get("title", self.plan.get("title", "Xebia Proposal")),
            subtitle=data.get("subtitle", self.plan.get("objective", "")),
            customer=data.get("customer", self.plan.get("customer", "")),
            date=data.get("date", ""),
            image_path=self._fetch_image(data, "cover"),
        )
        self._next_slide_num()

    def _build_toc(self, key: str, data: dict):
        storyline = self.plan.get("storyline", [])
        display_names = []
        for s in storyline:
            if s in ("cover", "table_of_contents", "closing"):
                continue
            name = s.replace("_", " ").title()
            section_data = self.plan.get("sections", {}).get(s, {})
            name = section_data.get("title", name)
            display_names.append(name)

        build_toc_slide(self.prs, display_names, self._next_slide_num())

    def _build_exec_summary(self, key: str, data: dict):
        build_section_divider(self.prs, data.get("title", "Executive Summary"),
                              self._next_slide_num(),
                              image_path=self._fetch_image(data, "section_divider"))
        build_executive_summary_slide(
            self.prs,
            title=data.get("title", "Executive Summary"),
            summary_text=data.get("summary", ""),
            key_points=data.get("key_points", []),
            slide_number=self._next_slide_num(),
        )

    def _build_content_section(self, key: str, data: dict):
        title = data.get("title", key.replace("_", " ").title())
        build_section_divider(self.prs, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "section_divider"))

        slides = data.get("slides", [])
        if slides:
            for slide_data in slides:
                layout = slide_data.get("layout")
                if layout:
                    build_slide_by_layout(
                        self.prs, layout, slide_data,
                        slide_number=self._next_slide_num(),
                    )
                else:
                    build_content_slide(
                        self.prs,
                        title=slide_data.get("title", title),
                        body_text=slide_data.get("body", ""),
                        bullets=slide_data.get("bullets", []),
                        slide_number=self._next_slide_num(),
                    )
        else:
            layout = data.get("layout")
            if layout:
                build_slide_by_layout(
                    self.prs, layout, data,
                    slide_number=self._next_slide_num(),
                )
            else:
                build_content_slide(
                    self.prs,
                    title=title,
                    body_text=data.get("body", ""),
                    bullets=data.get("bullets", []),
                    slide_number=self._next_slide_num(),
                )

    def _build_two_col_section(self, key: str, data: dict):
        title = data.get("title", key.replace("_", " ").title())
        build_section_divider(self.prs, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "section_divider"))

        layout = data.get("layout")
        if layout:
            build_slide_by_layout(
                self.prs, layout, data,
                slide_number=self._next_slide_num(),
            )
        elif data.get("left") and data.get("right"):
            build_two_column_slide(
                self.prs,
                title=title,
                left_title=data["left"].get("title", ""),
                left_bullets=data["left"].get("bullets", []),
                right_title=data["right"].get("title", ""),
                right_bullets=data["right"].get("bullets", []),
                slide_number=self._next_slide_num(),
            )
        else:
            build_content_slide(
                self.prs, title=title,
                body_text=data.get("body", ""),
                bullets=data.get("bullets", []),
                slide_number=self._next_slide_num(),
            )

    def _build_timeline(self, key: str, data: dict):
        title = data.get("title", "Timeline")
        build_section_divider(self.prs, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "timeline"))
        build_timeline_slide(
            self.prs,
            title=title,
            phases=data.get("phases", []),
            slide_number=self._next_slide_num(),
        )

    def _build_team(self, key: str, data: dict):
        title = data.get("title", "Team Structure")
        build_section_divider(self.prs, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "team"))
        build_team_slide(
            self.prs,
            title=title,
            team_members=data.get("members", []),
            slide_number=self._next_slide_num(),
        )

    def _build_commercials(self, key: str, data: dict):
        title = data.get("title", "Commercials")
        build_section_divider(self.prs, title, self._next_slide_num(),
                              image_path=self._fetch_image(data, "content"))
        build_commercials_slide(
            self.prs,
            title=title,
            rows=data.get("rows", []),
            total=data.get("total", ""),
            assumptions=data.get("assumptions", []),
            slide_number=self._next_slide_num(),
        )

    def _build_closing(self, key: str, data: dict):
        build_closing_slide(
            self.prs,
            title=data.get("title", "Thank You"),
            contact_name=data.get("contact_name", ""),
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            slide_number=self._next_slide_num(),
            image_path=self._fetch_image(data, "closing"),
        )


def generate_proposal_pptx(plan: dict, output_path: str | Path) -> Path:
    """Convenience function to generate a PPTX from a plan dict."""
    generator = ProposalPPTGenerator(plan)
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
