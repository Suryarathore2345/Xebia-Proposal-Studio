"""Claude client for proposal content generation.

Shared Anthropic client used by the main proposal planner and by the
design engine (theme selection, blueprint selection, architecture
diagrams) so there is one place that owns API-key loading and model
config.
"""

import os
import json
from datetime import date
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"

_client = None


def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_client() -> anthropic.Anthropic:
    """Return the shared Anthropic client, creating it on first use."""
    global _client
    if _client is not None:
        return _client

    _load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env or environment")

    _client = anthropic.Anthropic(api_key=api_key)
    return _client


SECTION_SCHEMA = """SECTION STRUCTURE — every key inside "sections" must use these EXACT field names, or the renderer will not find the content:

"cover": {"title": "...", "subtitle": "one-line value proposition", "customer": "...", "date": "YYYY-MM-DD"}

"table_of_contents": {"title": "Table of Contents"}
Include "table_of_contents" as the SECOND storyline entry (right after "cover") whenever the proposal will have more than ~10 sections — skip it for shorter decks where it would just be filler.

"executive_summary": {
  "title": "Executive Summary",
  "summary": "2-3 sentence overview of the engagement — mention the customer's challenge, Xebia's approach, and expected outcome",
  "key_points": ["4-6 specific, quantified points — e.g. 'Reduce data pipeline latency from 4 hours to under 15 minutes'"]
}

"corporate_overview": {
  "title": "About Xebia",
  "layout": "icon_grid",
  "items": [{"label": "capability area", "description": "1-2 sentence detail"}, ...] (6-8 items covering relevant Xebia capabilities)
}

"understanding_of_scope": {
  "title": "Understanding of Scope",
  "slides": [
    {"title": "Current State Assessment", "layout": "content", "body": "paragraph about client's current situation", "bullets": ["specific scope items"]},
    {"title": "Key Challenges", "layout": "challenges", "challenges": [{"challenge": "...", "impact": "business impact", "solution": "Xebia's approach"}]},
    {"title": "Scope Overview", "layout": "comparison_table", "headers": ["Area", "In Scope", "Out of Scope"], "rows": [["...", "...", "..."]]}
  ]
}

"proposed_solution": {
  "title": "Proposed Solution",
  "slides": [
    {"title": "Solution Overview", "layout": "two_column", "left": {"title": "Current State", "bullets": [...]}, "right": {"title": "Target State", "bullets": [...]}},
    {"title": "Key Solution Components", "layout": "icon_grid", "items": [{"label": "...", "description": "..."}]},
    {"title": "Expected Outcomes", "layout": "stats_highlight", "stats": [{"value": "40%", "label": "Cost Reduction"}, ...]}
  ]
}

"architecture": {
  "title": "Solution Architecture",
  "slides": [
    {
      "title": "Target Architecture",
      "layout": "architecture",
      "layers": [
        {"name": "Layer Name", "components": ["Component1", "Component2", "Component3"], "color": "blue|teal|purple|green|orange"},
        ... (4-6 layers, top to bottom: Sources → Ingestion → Processing → Storage → Serving → Consumption)
      ]
    },
    {
      "title": "e.g. End-to-End Data Flow",
      "layout": "migration_flow",
      "diagram": {
        "title": "Diagram title (shown as slide title)",
        "subtitle": "Optional one-line subtitle",
        "zones": [
          {
            "id": "unique_zone_id",
            "title": "Zone Title (under 30 chars)",
            "color": "orange|teal|blue|purple|green|dark",
            "width_ratio": 1.0,
            "groups": [
              {"label": "Group Label (under 25 chars)", "items": ["Item 1", "Item 2"], "style": "icons|pills|flow|text"}
            ]
          }
        ],
        "bottom_bands": [{"label": "Band Label", "items": ["Cross-cutting item 1", "Item 2"], "color": "purple"}],
        "journey_labels": [{"label": "Transformation Journey Name", "from_zone_index": 0, "to_zone_index": 2}]
      }
    }
  ]
}
ARCHITECTURE IS MANDATORY. Always include at least one "architecture" or "migration_flow" slide with realistic, project-specific technology names.

Two layout options for architecture content — pick based on what the proposal needs:
- "architecture": simple stacked layers, top to bottom. Good for a single clean overview. 4-6 layers, 2-4 components each, colors from blue/teal/purple/green/orange.
- "migration_flow": a left-to-right zone diagram (3-6 zones), each with 2-5 groups of 2-5 short items. Prefer it whenever the architecture is complex enough to benefit from a visual flow. zones: color one of orange (source/current-state), teal (migration/transformation), blue (target cloud), purple (data/analytics platform), green (outcomes/value), dark (governance) — don't repeat colors on adjacent zones. width_ratio: 1.0 standard, 0.5-0.7 for a narrow outcome zone (needs at least ~1.2 width_ratio-equivalent space for "pills" or "icons" styles to render — keep those groups in normal or wide zones, not the narrowest ones). groups: "style":"icons" for real, named technologies/products (this is the ONLY style that renders an actual icon image per item — use it for Azure/AWS/Fabric services, databases, and other recognized tools, e.g. "Azure Data Factory", "Oracle Database", "Power BI"); "pills" for short text badges with no icon (generic/non-recognized items); "flow" only for a strategy sequence (e.g. Rehost → Replatform → Refactor); "text" otherwise. Item labels: 2-4 words, no sentences. bottom_bands (0-2) for cross-cutting concerns (governance, security, monitoring). journey_labels (0-2) to call out the 1-2 major transformation stories.

For a data platform / migration proposal, generate 2-3 DISTINCT migration_flow diagrams that each earn their place — e.g. "Current-State Architecture" (today's fragmented/legacy setup), "Target Architecture" or "End-to-End Data Flow" (the proposed platform, source to consumption), and optionally a third focused view (e.g. medallion/lakehouse layers, or the analytics/consumption layer) — never repeat the same zones/content across multiple diagrams. For a smaller or simpler proposal, one "architecture" slide is enough — don't pad with diagrams that don't add information.

NEVER include both an "architecture" (pyramid layers) slide AND a "migration_flow" slide that describe the same breakdown (e.g. both walking through the identical Bronze/Silver/Gold medallion layers) — that reads as padding, not depth. If you use both layout types in one proposal, they must serve genuinely different purposes: e.g. the "architecture" slide is the single canonical layer reference (used once), while "migration_flow" diagrams are flow/lineage-oriented (source-to-consumption data movement) or show a distinct lifecycle view (current-state vs. target-state) — not a second rendering of the same layer list in a different shape.

OPTIONAL — options considered: when there are genuinely 2+ viable architectural approaches for this engagement and one was chosen (e.g. two different MDM strategies, two hosting models), add ONE extra slide inside the "architecture" section's "slides" array with "layout": "comparison_table", headers like ["Criteria", "Option 1: X", "Option 2: Y"], and rows comparing them on cost/complexity/timeline/fit — state which option is recommended in the surrounding text. Skip this entirely when there's only one sensible approach; don't manufacture a false choice.

"technology_stack": {
  "title": "Technology Stack",
  "slides": [
    {
      "title": "Technology Stack",
      "layout": "technology",
      "technologies": [
        {"name": "Tech Name", "category": "Platform|Analytics|Integration|Security|DevOps", "description": "1-sentence role in the solution"},
        ... (6-10 technologies)
      ]
    }
  ]
}

"delivery_approach": {
  "title": "Delivery Approach",
  "layout": "process_flow",
  "steps": [{"label": "Phase Name", "description": "what happens"}, ...] (4-6 steps)
}

"timeline": {
  "title": "Project Timeline",
  "phases": [
    {"name": "Phase 1: ...", "duration": "Week 1-4", "start_week": 1, "duration_weeks": 4},
    ... (4-8 phases/workstreams)
  ]
}
This renders as a real week-ruled Gantt chart (bars, not description cards) — keep phase names short (they're a row label, not a place for detail; put step-by-step detail in "delivery_approach" instead). "duration" is the human-readable label shown on the bar (keep it consistent with start_week/duration_weeks). "start_week" and "duration_weeks" are integers (week 1 = project start) that drive the bar's position and width — workstreams that genuinely run in parallel should OVERLAP in their week ranges (e.g. a "Data Governance" phase starting mid-way through "Data Ingestion" rather than only after it finishes) instead of always being purely sequential — real delivery plans have concurrent workstreams.

"team_structure": {
  "title": "Proposed Team",
  "members": [
    {"name": "realistic Indian/international name", "role": "Solution Architect|Data Engineer|Cloud Engineer|DevOps Engineer|QA Lead|Project Manager|Business Analyst", "expertise": "specific technologies"},
    ... (4-8 members appropriate for the project)
  ]
}

"commercials": {
  "title": "Investment Summary",
  "rows": [
    {"item": "Role Name", "hours": "total hours", "rate": "hourly rate", "cost": "total cost"},
    ... (one row per team role)
  ],
  "total": "grand total",
  "assumptions": ["Payment terms", "Travel excluded", "Rate validity period", ...]
}

SITUATIONAL SECTIONS — "payment_milestones", "support_model", "licensing_estimate" below are OPTIONAL. Include them for enterprise/complex engagements (large team, multi-phase delivery, regulated industry) where a real proposal would need this level of commercial detail. Skip all three for smaller or simpler proposals — don't pad every deck with them regardless of deal size. When included, keep "commercials", "payment_milestones", "support_model", and "licensing_estimate" as ONE CONTIGUOUS block in that order (commercials first) — readers need the total investment before milestones/support/licensing detail, and interleaving them with "risk_mitigation" or other sections breaks that financial narrative.

"payment_milestones": {
  "title": "Payment Milestones",
  "slides": [
    {"title": "Payment Milestones", "layout": "comparison_table",
     "headers": ["Milestone", "% of Contract Value", "Trigger Condition"],
     "rows": [["Mobilization", "25%", "Contract signed, project kickoff"], ...] (3-5 milestones)}
  ]
}

"support_model": {
  "title": "Support Model",
  "layout": "icon_grid",
  "items": [{"label": "Support tier name (e.g. 'L1 — Business Hours')", "description": "response/resolution SLA and scope"}, ...] (3-5 tiers)
}

"licensing_estimate": {
  "title": "Licensing & Infrastructure Estimate",
  "slides": [
    {"title": "Licensing & Infrastructure Estimate", "layout": "comparison_table",
     "headers": ["Component", "Est. Monthly Cost", "Est. Annual Cost"],
     "rows": [["Microsoft Fabric Capacity (F64)", "$8,400", "$100,800"], ...] (3-6 components)}
  ]
}
Keep this separate from "commercials" (which covers Xebia's services/labor cost only) — this section covers the customer's own cloud/platform spend, billed directly to them.

"risk_mitigation": {
  "title": "Risk Mitigation",
  "slides": [
    {
      "title": "Risks & Mitigation",
      "layout": "challenges",
      "challenges": [
        {"challenge": "specific risk", "impact": "business impact if unmitigated", "solution": "concrete mitigation strategy"},
        ... (3-5 risks)
      ]
    }
  ]
}

"case_studies": {
  "title": "Relevant Experience",
  "slides": [
    {"title": "Client Name – Project", "layout": "key_value", "pairs": [
      {"key": "Client", "value": "..."},
      {"key": "Challenge", "value": "..."},
      {"key": "Solution", "value": "..."},
      {"key": "Impact", "value": "quantified result"},
      {"key": "Technologies", "value": "..."}
    ]},
    ... (2-3 case studies)
  ]
}

"next_steps": {
  "title": "Next Steps",
  "layout": "process_flow",
  "steps": [{"label": "Step", "description": "action item"}, ...] (3-5 steps)
}

"closing": {"title": "Thank You", "contact_name": "...", "contact_email": "...", "body": "..."}

AVAILABLE SLIDE LAYOUTS (choose the best one for each piece of content):
- "content": title + body + bullets. For general text.
- "two_column": two side-by-side columns. For comparisons, current/target state. Needs "left"/"right" with "title" and "bullets".
- "icon_grid": grid of labeled cards. For capabilities, features. Needs "items": [{"label", "description"}].
- "process_flow": numbered horizontal steps. For methodologies, workflows. Needs "steps": [{"label", "description"}].
- "comparison_table": styled table. For feature matrices. Needs "headers": [...] and "rows": [[...]].
- "stats_highlight": large KPI numbers. For impact metrics. Needs "stats": [{"value", "label"}].
- "key_value": left-right pairs. For project details, case studies. Needs "pairs": [{"key", "value"}].
- "architecture": multi-layer diagram with component boxes. For solution architecture. Needs "layers": [{"name", "components", "color"}].
- "migration_flow": left-to-right multi-zone architecture diagram with real technology icons. For richer/multiple architecture views. Needs "diagram": {"title", "zones": [...], "bottom_bands", "journey_labels"} — see the architecture section schema above for the full shape.
- "technology": tech cards with categories. For tech stack. Needs "technologies": [{"name", "category", "description"}].
- "challenges": 3-column challenge/impact/solution. For risks, challenges. Needs "challenges": [{"challenge", "impact", "solution"}].
- "timeline": phase bars (timeline sections only). Needs "phases".
- "team": member cards (team sections only). Needs "members".

TECHNOLOGY NAMING — the deck has a local icon library covering AWS, Azure, Microsoft Fabric, and common data/DevOps tools (Databricks, Spark, Kafka, Kubernetes, Airflow, dbt, Snowflake, PostgreSQL, MongoDB, Redis, Terraform, etc.). Whenever a technology in "technologies", "architecture" components, or elsewhere matches one of these, use its common/official name (e.g. "Azure Data Factory", "Amazon S3", "Apache Airflow") so the icon resolves — don't invent alternate spellings.

REUSING REFERENCE MATERIAL:
You will be given layout/slide/section references pulled from past Xebia proposals via semantic search. Use them to understand real structural patterns Xebia uses — which layout fits which content type, how dense a slide typically is, how architecture layers are usually grouped — and adapt that structure to this proposal. Do NOT copy client names, numbers, or specifics from them.

IMAGE QUERIES:
Every slide object should include an "image_query" field — a 2-4 word search phrase for finding a relevant stock photo.
Examples: "cloud infrastructure", "data analytics dashboard", "agile team collaboration", "cybersecurity network".
Make queries specific to the slide's topic. The image_query is used to fetch a Pexels stock photo for visual enhancement.

USER-UPLOADED IMAGES:
Some images attached to this message are user uploads meant to be embedded in the final deck (marked "embed" below), as opposed to images provided only as style/architecture reference (marked "reference"). For every "embed" image, look at it, decide which single section/slide it belongs on and where, and add an entry to "image_placements":
{"image_id": "<the id given for that image>", "section": "<storyline key, e.g. architecture>", "slide_index": 0, "position": "right|left|full", "caption": "short caption describing the image"}
slide_index is the 0-based index into that section's "slides" array (0 if the section has no "slides" array). Only place an image where it is actually relevant to the content on that slide — never place it arbitrarily."""


SYSTEM_PROMPT = f"""You are Xebia Proposal Studio, an AI assistant that creates premium, enterprise-grade proposals for Xebia, a global IT consultancy.

Your job: have a natural conversation to gather requirements, then generate a structured proposal plan with RICH, SPECIFIC content — never generic filler.

CONVERSATION BEHAVIOR:
- If the user's request is vague or missing key details, ask clarifying questions. Ask ONE round of 2-3 focused questions maximum.
- Key details to gather: customer name, project objective, technologies involved, timeline, team size, budget range.
- Also try to understand: current pain points, existing tech stack, compliance requirements, stakeholders.
- Be professional but conversational. Keep responses concise.
- When you have enough information (at minimum: customer name and project objective), generate the proposal plan.

WHEN ASKING QUESTIONS (not ready to generate yet):
Call the submit_proposal_plan tool with "ready": false and a "message" field containing your conversational response with questions. Leave every other field empty/omitted.

WHEN GENERATING A PROPOSAL PLAN:
Call the submit_proposal_plan tool with "ready": true and the full plan, using every field listed under "sections" for every section in your storyline.

{SECTION_SCHEMA}

CONTENT QUALITY RULES:
1. EVERY section must have meaningful, specific content. No empty sections, no placeholder text like "TBD" or "To be discussed".
2. Use at least 6-7 DIFFERENT layout types across the proposal. Never use "content" for more than 2 slides.
3. All text must be specific to the customer's project — mention their name, industry, technologies, and challenges.
4. Architecture section is MANDATORY with real technology names and logical layer organization.
5. Stats and metrics should be realistic and quantified (percentages, timeframes, counts).
6. Team members should have realistic names, specific roles, and relevant expertise.
7. Case studies should be plausible Xebia engagements in the same industry/technology domain.
8. Bullets should be concise (under 15 words each) but specific. No generic consulting jargon.
9. Each section's "slides" array can have multiple slides — use this to avoid overloading any single slide with too much content.
10. For commercials, use rates in the $150-250/hr range unless specified. Calculate hours realistically based on timeline and team size.
11. EVERY slide must have an "image_query" field for stock photo fetching.
12. Include "payment_milestones", "support_model", and "licensing_estimate" only for enterprise/complex engagements (see their schemas above) — omit them for smaller or simpler proposals rather than padding every deck with the same sections regardless of deal size.

CRITICAL RULES:
- ALWAYS use the customer name and project details provided by the USER. NEVER copy or reuse organization names, project names, client names, contact details, or specific business context from reference material.
- Reference material is provided ONLY as examples of proposal STRUCTURE and STYLE. Extract patterns like section organization, writing tone, and level of detail — but REPLACE all specifics with the user's actual customer information.
- If the user says the customer is "Meghnani Groups", every section must use "Meghnani Groups" — never substitute a name from a reference document.
- Always call the submit_proposal_plan tool. Never respond in plain text."""


REVIEW_SYSTEM_PROMPT = f"""You are a senior proposal reviewer at Xebia. You will be shown a complete proposal plan JSON (the same schema used to generate it) and must flag and rewrite only what needs fixing before it gets rendered into the final PPTX/DOCX.

{SECTION_SCHEMA}

Check the plan against this checklist, in order of priority:
1. CONTENT: generic filler, vague claims, missing quantification, sections that don't mention the actual customer/industry/technologies.
2. FLOW: does the storyline read as a coherent narrative (problem → approach → proof → ask)? Are any mandatory sections thin or missing?
3. LAYOUT VARIETY: is "content" layout overused? Are at least 6-7 different layout types used across the deck?
4. ARCHITECTURE: is the architecture section realistic, with real technology names appropriate to this project, in a sensible layer order?
5. CONSISTENCY: do technology names, customer name, and numbers stay consistent across every section? Do stats in commercials match the team/timeline described elsewhere?
6. COMPLETENESS: any section with empty arrays, placeholder text, or missing required fields for its layout?

HOW TO RESPOND — this is critical:
Call the submit_proposal_plan tool with "ready": true. Under "sections", include ONLY the sections you are actually changing, each with its FULL corrected content using the exact field names from the schema above — do not include a section at all if you are leaving it as-is. Sections you omit are kept exactly as originally generated, so leaving an unchanged section out is correct and expected, not an oversight. Likewise, only include "title", "customer", "industry", "objective", "storyline", or "image_placements" if you are changing that specific field; omit anything you're not touching.

Never invent replacement facts: keep the same customer name, industry, and any user-provided details — you may only sharpen, complete, or restructure content within a section, never replace real customer specifics with invented ones. If a section is already good, simply leave it out of your response."""


PROPOSAL_PLAN_TOOL = {
    "name": "submit_proposal_plan",
    "description": "Submit either a clarifying-question response or a complete proposal plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ready": {"type": "boolean", "description": "true if the full plan is included, false if asking clarifying questions"},
            "message": {"type": "string", "description": "Conversational response — clarifying questions when ready=false, or a short confirmation when ready=true"},
            "title": {"type": "string"},
            "customer": {"type": "string"},
            "industry": {"type": "string"},
            "objective": {"type": "string"},
            "storyline": {"type": "array", "items": {"type": "string"}},
            "sections": {"type": "object", "description": "Keyed by storyline section name, see system prompt for schema per section"},
            "image_placements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "image_id": {"type": "string"},
                        "section": {"type": "string"},
                        "slide_index": {"type": "integer"},
                        "position": {"type": "string", "enum": ["left", "right", "full"]},
                        "caption": {"type": "string"},
                    },
                    "required": ["image_id", "section", "position"],
                },
            },
        },
        "required": ["ready"],
    },
}


def _extract_tool_input(response) -> dict:
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            "Claude's response was cut off by max_tokens before finishing the tool call "
            "— the plan would be incomplete/malformed. Retry with a smaller ask or raise max_tokens."
        )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_proposal_plan":
            return block.input
    raise RuntimeError("Claude did not call submit_proposal_plan")


def _build_image_content(images: list[dict]) -> list[dict]:
    content = []
    for img in images:
        img_path = Path(img.get("path", ""))
        if not img_path.exists():
            continue
        import base64
        mime = img.get("mime_type", "image/png")
        data = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")
        label = img.get("type", "reference")
        image_id = img.get("id", "")
        content.append({"type": "text", "text": f"[Image id={image_id}, type={label}]"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": data},
        })
    return content


def generate_proposal_plan(user_input: str, references: list[dict] = None,
                           conversation_history: list[dict] = None,
                           images: list[dict] = None,
                           layout_references: list[dict] = None,
                           slide_references: list[dict] = None) -> dict:
    """Generate a structured proposal plan from user input and reference context."""
    client = get_client()

    ref_context = ""
    if references:
        ref_snippets = [f"- {r.get('text', '')[:200]}" for r in references[:8]]
        ref_context = (
            "\n\n[STYLE REFERENCE ONLY — do NOT copy names, clients, or specifics from these. "
            "Use them only to understand Xebia's writing style and proposal structure.]\n"
            + "\n".join(ref_snippets)
        )

    layout_context = ""
    if layout_references:
        layout_snippets = [
            f"- [{r.get('metadata', {}).get('slide_type', 'content')}] {r.get('text', '')[:200]}"
            for r in layout_references[:10]
        ]
        layout_context = (
            "\n\n[LAYOUT/STRUCTURE REFERENCES — one example per slide type seen in past proposals. "
            "Use these to understand how Xebia structures each slide type, not for wording.]\n"
            + "\n".join(layout_snippets)
        )

    slide_context = ""
    if slide_references:
        slide_snippets = [f"- {r.get('text', '')[:200]}" for r in slide_references[:6]]
        slide_context = (
            "\n\n[RELATED PAST SLIDES — adapt structure/approach, replace all specifics.]\n"
            + "\n".join(slide_snippets)
        )

    conv_context = ""
    if conversation_history:
        msgs = []
        for msg in conversation_history[-10:]:
            role = msg.get("role", "user")
            msgs.append(f"{role}: {msg.get('content', '')}")
        conv_context = "\n\nConversation so far:\n" + "\n".join(msgs)

    date_context = f"\n\n[Today's date: {date.today().isoformat()}. Use this for the cover date unless the user specifies otherwise.]"

    user_message = user_input + ref_context + layout_context + slide_context + conv_context + date_context

    content = [{"type": "text", "text": user_message}]
    if images:
        content.extend(_build_image_content(images))

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[PROPOSAL_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_proposal_plan"},
        messages=[{"role": "user", "content": content}],
    )

    return _extract_tool_input(response)


def review_and_improve_plan(plan: dict) -> dict:
    """Send a generated plan back to Claude for a content/flow/layout critique pass.

    Claude returns only the sections it wants to change (see
    REVIEW_SYSTEM_PROMPT) — anything it omits is kept byte-identical to the
    original plan, so a partial/rushed review response can only leave
    sections unchanged, never blank them out.
    """
    client = get_client()

    plan_json = json.dumps(plan, indent=2)
    user_message = f"Here is the generated proposal plan to review:\n\n{plan_json}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=[{
            "type": "text",
            "text": REVIEW_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[PROPOSAL_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_proposal_plan"},
        messages=[{"role": "user", "content": user_message}],
    )

    revision = _extract_tool_input(response)

    merged = dict(plan)
    for key in ("title", "customer", "industry", "objective", "storyline", "image_placements"):
        if revision.get(key):
            merged[key] = revision[key]

    revised_sections = revision.get("sections") or {}
    if revised_sections:
        merged_sections = dict(plan.get("sections", {}))
        merged_sections.update(revised_sections)
        merged["sections"] = merged_sections

    return merged


def generate_text(prompt: str, max_tokens: int = 2000) -> str:
    """Plain text completion — used by the design engine (theme/blueprint
    selection) so it can be driven by whichever provider the chat toggle
    picked, not hardcoded to Claude.

    Extended thinking is explicitly disabled: this model enables it by
    default, and on structured-JSON calls like blueprint selection it can
    consume the entire max_tokens budget on invisible reasoning, leaving
    nothing (or a truncated fragment) for the actual JSON — the exact cause
    of blueprint selection silently falling back to rule-based design on
    larger decks. These calls need reliable structured output, not hidden
    reasoning, so thinking is off rather than just raising max_tokens."""
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def generate_section_content(section_type: str, context: str,
                              references: list[dict] = None) -> dict:
    """Generate content for a single proposal section."""
    client = get_client()

    ref_context = ""
    if references:
        snippets = [f"- {r.get('text', '')[:200]}" for r in references[:5]]
        ref_context = "\nReference content:\n" + "\n".join(snippets)

    prompt = f"""Generate content for a "{section_type}" section of a Xebia proposal.

Context: {context}
{ref_context}

Return a JSON object with the section content. Include "title", "body" or "summary", and "bullets" or other relevant fields.
Return ONLY valid JSON, no markdown."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)
