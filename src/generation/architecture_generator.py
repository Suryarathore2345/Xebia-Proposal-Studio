"""Architecture diagram content generator.

Two entry points:

- generate_architecture_diagram(): produce a diagram from a free-text
  requirement (used by scripts/test_architecture_gen.py, and available
  for any future direct-generation use case).
- elaborate_architecture_diagrams(): the live pipeline's dedicated
  second pass. The main proposal-plan call (llm/anthropic_client.py)
  already decides *how many* architecture/migration_flow slides a
  proposal needs and *what each one is for* — but it produces that
  content sharing one giant call's attention with ~15 other slide
  types. This pass re-elaborates each migration_flow diagram with a
  full token budget and diagram-scoped retrieval, so architecture depth
  isn't a casualty of the plan call's competing priorities. It is
  strictly additive: on any failure it leaves the plan's own diagram
  content untouched, so it can never make a proposal generation fail.
"""

from __future__ import annotations

import json

from llm.anthropic_client import get_client, MODEL, ARCHITECTURE_DIAGRAM_GUIDANCE


ARCHITECTURE_SYSTEM_PROMPT = f"""You are an expert enterprise solution architect creating architecture diagram content for client-facing consulting proposals.

Your job: analyze the user's architecture requirements and any reference material, then produce a structured JSON specification for a "migration_flow" diagram (or, if a simple single-overview layered stack is genuinely a better fit, an "architecture" layers list instead).

The diagram will be rendered on a 16:9 PowerPoint slide (13.333" x 7.5"). It must communicate the architecture clearly and, for an enterprise-grade proposal, with real depth — not a shallow 3-box sketch. Prioritize clarity and technical accuracy together; don't sacrifice one for the other.

OUTPUT FORMAT — return ONLY a valid JSON object with this exact structure (a bare "diagram" object — no "layout"/"title" wrapper, no surrounding section keys):

{{
  "title": "Diagram title (shown as slide title)",
  "subtitle": "Optional one-line subtitle",
  ...the rest of the "diagram" shape described below...
}}

{ARCHITECTURE_DIAGRAM_GUIDANCE}

IMPORTANT:
- Derive ALL content from the user's requirements and reference material — never invent services, tools, capabilities, CIDR ranges, or resource names not supported by the input.
- This is a re-elaboration pass, not a first draft in a vacuum: when a current draft is provided, keep its overall intent (the same zones/purpose it was already trying to serve) but deepen it — don't discard a sound structure just to produce something different.
- Return ONLY valid JSON (the diagram object itself). No markdown, no code fences, no explanation."""


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
    client = get_client()

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

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=ARCHITECTURE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)


def _diagram_search_query(slide: dict, plan: dict) -> str:
    """Build a retrieval query scoped to this one diagram — its own
    title/zone titles plus the proposal's industry/objective — rather
    than reusing the single generic query already used for the whole
    plan, so this pass can pull material more specific to this diagram."""
    diagram = slide.get("diagram", {})
    parts = [slide.get("title", ""), diagram.get("title", "")]
    parts += [z.get("title", "") for z in diagram.get("zones", [])]
    parts += [plan.get("industry", ""), plan.get("objective", "")]
    return " ".join(p for p in parts if p)


def _proposal_context(plan: dict, slide: dict) -> str:
    return (
        f"Customer: {plan.get('customer', '')}\n"
        f"Industry: {plan.get('industry', '')}\n"
        f"Objective: {plan.get('objective', '')}\n"
        f"This diagram's purpose within the proposal (as decided by the "
        f"overall plan): \"{slide.get('title', '')}\""
    )


def elaborate_architecture_diagrams(plan: dict, top_k: int = 12) -> dict:
    """Re-elaborate each migration_flow diagram in the plan's architecture
    section with a dedicated, focused Claude call.

    Mutates and returns `plan`. Never raises — any failure (missing API
    key, malformed JSON response, retrieval error) is caught per-diagram
    and leaves that slide's existing content exactly as the main planning
    call produced it, so this pass can only improve a diagram, never
    break the generation pipeline.
    """
    arch_section = plan.get("sections", {}).get("architecture", {})
    slides = arch_section.get("slides", [])

    for slide in slides:
        if slide.get("layout") != "migration_flow" or not slide.get("diagram"):
            continue

        try:
            from retrieval.search import search_for_proposal
            query = _diagram_search_query(slide, plan)
            refs = search_for_proposal(query, top_k=top_k) if query.strip() else {}
            reference_content = refs.get("content_references", [])
        except Exception as e:
            print(f"[architecture_generator] Reference search failed for "
                  f"'{slide.get('title', '')}' ({e}) — elaborating without it")
            reference_content = []

        current_diagram = slide["diagram"]
        user_prompt = (
            f"Re-elaborate the following architecture diagram with your full "
            f"attention on this one diagram — it was drafted as one of many "
            f"sections in a single larger proposal-generation pass and may be "
            f"shallower than an enterprise-grade proposal needs.\n\n"
            f"Current draft:\n{json.dumps(current_diagram, indent=2)}"
        )

        try:
            elaborated = generate_architecture_diagram(
                user_prompt,
                reference_content=reference_content,
                context=_proposal_context(plan, slide),
            )
            if elaborated.get("zones") or elaborated.get("layers"):
                elaborated.setdefault("title", current_diagram.get("title", ""))
                slide["diagram"] = elaborated
        except Exception as e:
            print(f"[architecture_generator] Elaboration failed for "
                  f"'{slide.get('title', '')}' ({e}) — keeping original diagram")
            continue

    return plan
