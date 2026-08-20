"""Architecture diagram content generator.

Takes a user's architecture requirements and reference content,
then uses Gemini to produce structured diagram data that the
MigrationFlowRenderer (or other renderers) can consume directly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google import genai
from google.genai import types


def _get_client() -> genai.Client:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env or environment")

    return genai.Client(api_key=api_key)


ARCHITECTURE_SYSTEM_PROMPT = r"""You are an expert enterprise solution architect creating architecture diagram content for client-facing consulting proposals.

Your job: analyze the user's architecture requirements and any reference material, then produce a structured JSON specification for a multi-zone left-to-right architecture flow diagram.

The diagram will be rendered on a 16:9 PowerPoint slide (13.333" × 7.5"). It must communicate the transformation story in 5–10 seconds. Prioritize storytelling and visual clarity over technical completeness.

OUTPUT FORMAT — return ONLY a valid JSON object with this exact structure:

{
  "title": "Diagram title (shown as slide title)",
  "subtitle": "Optional one-line subtitle",
  "zones": [
    {
      "id": "unique_zone_id",
      "title": "Zone Title (keep under 30 chars)",
      "color": "orange|teal|blue|purple|green|dark",
      "width_ratio": 1.0,
      "groups": [
        {
          "label": "Group Label (keep under 25 chars)",
          "items": ["Item 1", "Item 2", "Item 3"],
          "style": "text|pills|flow"
        }
      ]
    }
  ],
  "bottom_bands": [
    {
      "label": "Band Label",
      "items": ["Cross-cutting item 1", "Item 2", "Item 3"],
      "color": "purple"
    }
  ],
  "journey_labels": [
    {
      "label": "Transformation Journey Name",
      "from_zone_index": 0,
      "to_zone_index": 2
    }
  ]
}

FIELD DETAILS:

zones: Array of 3-6 zones displayed left to right. Each zone represents a major architectural domain.
  - id: unique identifier (snake_case)
  - title: zone header text — concise, business-friendly
  - color: visual theme — use "orange" for source/current state, "teal" for migration/transformation, "blue" for target cloud, "purple" for data/analytics platforms, "green" for outcomes/value, "dark" for governance
  - width_ratio: relative width (1.0 is standard, 0.5 is half, 1.2 is wider). Outcome zones should be narrower (0.5-0.7). Major platform zones can be wider (1.0-1.2).
  - groups: 2-5 logical groupings within the zone

groups: Sub-sections within a zone.
  - label: group heading — concise domain name
  - items: 2-5 items per group. Use SHORT labels (2-4 words max). Use service names, capability names, or component names — not sentences.
  - style: "text" (default, items as dot-separated text), "pills" (colored pill badges — use for services/tools), "flow" (left-to-right mini-flow with arrows — use for strategies/phases)

bottom_bands: 0-2 cross-cutting bands below the zones (governance, security, monitoring).
  - color: which zone_theme color to use for the label

journey_labels: 0-2 transformation journey spans shown as labeled brackets.
  - from_zone_index / to_zone_index: 0-based zone indices

DESIGN RULES:
1. MAXIMUM 5 zones. More than 5 becomes unreadable on a single slide.
2. MAXIMUM 5 groups per zone, MAXIMUM 5 items per group.
3. Item labels MUST be 2-4 words max. No sentences, no descriptions. Just names.
4. Group labels MUST be under 25 characters.
5. Zone titles MUST be under 30 characters.
6. Only include services/capabilities actually mentioned or clearly implied by the proposal. Never invent.
7. Use "flow" style sparingly — only for strategy sequences (e.g. Rehost → Replatform → Refactor).
8. Use "pills" style for technology/service listings that benefit from visual separation.
9. The outcome/value zone should be narrow (width_ratio 0.5-0.7) with high-level business outcomes.
10. Assign colors that make architectural sense — don't repeat colors for adjacent zones.
11. Bottom bands should only contain genuine cross-cutting concerns.
12. Journey labels should highlight the 1-2 major transformation stories.

IMPORTANT:
- Derive ALL content from the user's requirements and reference material.
- Do NOT add services, tools, or capabilities not supported by the input.
- Keep the diagram at PROPOSAL level — high-level groupings, not detailed service catalogs.
- Return ONLY valid JSON. No markdown, no code fences, no explanation."""


def generate_architecture_diagram(
    user_prompt: str,
    reference_content: list[dict] | None = None,
    context: str = "",
) -> dict:
    """Generate structured architecture diagram data from user requirements.

    Args:
        user_prompt: The user's architecture requirements/description.
        reference_content: Optional list of reference snippets with 'text' and
            'source_file' keys from the retrieval pipeline.
        context: Additional context about the proposal (customer, industry, etc.)

    Returns:
        Dict matching the MigrationFlowRenderer's diagram_data schema.
    """
    client = _get_client()

    parts = [user_prompt]

    if context:
        parts.append(f"\n\nProposal context:\n{context}")

    if reference_content:
        ref_snippets = []
        for r in reference_content[:12]:
            source = r.get("source_file", "reference")
            text = r.get("text", "")[:400]
            ref_snippets.append(f"[{source}]: {text}")
        parts.append(
            "\n\nReference material from existing proposals:\n"
            + "\n".join(ref_snippets)
        )

    user_message = "\n".join(parts)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=ARCHITECTURE_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=8000,
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)
