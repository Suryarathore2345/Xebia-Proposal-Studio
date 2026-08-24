"""Gemini LLM client for proposal content generation — 3-phase pipeline."""

import os
import json
from pathlib import Path

from google import genai
from google.genai import types

_clients: list[genai.Client] = []
_current_key_index = 0
_MODEL = "gemini-3.6-flash"


def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _init_clients():
    global _clients
    if _clients:
        return

    _load_env()

    keys = []
    key1 = os.environ.get("GEMINI_API_KEY", "")
    if key1:
        keys.append(key1)
    key2 = os.environ.get("GEMINI_API_KEY_2", "")
    if key2:
        keys.append(key2)
    key3 = os.environ.get("GEMINI_API_KEY_3", "")
    if key3:
        keys.append(key3)

    if not keys:
        raise RuntimeError("No GEMINI_API_KEY set in .env or environment")

    _clients = [genai.Client(api_key=k) for k in keys]


def _get_client() -> genai.Client:
    _init_clients()
    return _clients[_current_key_index]


def _rotate_key():
    global _current_key_index
    _init_clients()
    if len(_clients) > 1:
        _current_key_index = (_current_key_index + 1) % len(_clients)


def _call_gemini(system_prompt: str, contents, temperature: float = 0.7,
                 max_output_tokens: int = 8000) -> str:
    """Call Gemini with automatic key rotation on rate limit errors."""
    _init_clients()
    attempts = len(_clients)
    last_error = None

    for _ in range(attempts):
        client = _get_client()
        try:
            response = client.models.generate_content(
                model=_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                last_error = e
                _rotate_key()
                continue
            raise

    raise last_error


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _repair_truncated_json(text)


def _repair_truncated_json(text: str) -> dict:
    """Attempt to repair JSON truncated by token limits."""
    text = text.strip()
    if not text.startswith("{"):
        idx = text.find("{")
        if idx >= 0:
            text = text[idx:]
        else:
            raise json.JSONDecodeError("No JSON object found", text, 0)

    open_braces = 0
    open_brackets = 0
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            open_braces += 1
        elif ch == '}':
            open_braces -= 1
        elif ch == '[':
            open_brackets += 1
        elif ch == ']':
            open_brackets -= 1

    if in_string:
        text += '"'

    last_good = len(text)
    while open_braces > 0 or open_brackets > 0:
        chunk = text[:last_good].rstrip()
        last_comma = max(chunk.rfind(','), chunk.rfind('"'), chunk.rfind('}'), chunk.rfind(']'))

        if open_brackets > 0:
            text += ']'
            open_brackets -= 1
        elif open_braces > 0:
            text += '}'
            open_braces -= 1

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for trim in [',]', ',}', ',"', ", ", ","]:
            attempt = text
            while True:
                idx = attempt.rfind(trim[0])
                if idx < 0:
                    break
                attempt = attempt[:idx] + trim[1:] if len(trim) > 1 else attempt[:idx]
                closers = ""
                ob, obr = 0, 0
                for ch in attempt:
                    if ch == '{': ob += 1
                    elif ch == '}': ob -= 1
                    elif ch == '[': obr += 1
                    elif ch == ']': obr -= 1
                closers = ']' * max(0, obr) + '}' * max(0, ob)
                try:
                    return json.loads(attempt + closers)
                except json.JSONDecodeError:
                    continue
                break

        raise json.JSONDecodeError("Could not repair truncated JSON", text, len(text))


# ---------------------------------------------------------------------------
# Phase 1: Slide Planning
# ---------------------------------------------------------------------------

SLIDE_PLAN_PROMPT = """You are Xebia Proposal Studio, an AI assistant that creates premium, enterprise-grade proposals for Xebia, a global IT consultancy.

Your job: have a natural conversation to gather requirements, then generate a SLIDE PLAN — a detailed outline of every slide the proposal will contain.

CONVERSATION BEHAVIOR:
- If the user's request is vague or missing key details, ask clarifying questions. Ask ONE round of 2-3 focused questions maximum.
- Key details to gather: customer name, project objective, technologies involved, timeline, team size, budget range.
- Also try to understand: current pain points, existing tech stack, compliance requirements, stakeholders.
- Be professional but conversational. Keep responses concise.
- When you have enough information (at minimum: customer name and project objective), generate the slide plan.

WHEN ASKING QUESTIONS (not ready to generate yet):
Return a JSON object:
{"ready": false, "message": "Your conversational response here with questions"}

WHEN GENERATING A SLIDE PLAN:
Return ONLY a JSON object (no markdown, no code fences):
{
  "ready": true,
  "title": "Proposal title — specific to this engagement",
  "customer": "Customer name exactly as the user provided it",
  "industry": "Customer's industry",
  "objective": "One-line objective",
  "slide_plan": [
    {
      "section": "cover",
      "slides": [
        {"purpose": "Opening slide", "layout": "cover", "key_points": ["project title", "customer name", "date"]}
      ]
    },
    {
      "section": "table_of_contents",
      "slides": [
        {"purpose": "Agenda overview", "layout": "toc", "key_points": ["list all sections"]}
      ]
    },
    {
      "section": "executive_summary",
      "slides": [
        {"purpose": "Summarize engagement in 2-3 sentences", "layout": "content", "key_points": ["client challenge", "Xebia approach", "expected outcome"]}
      ]
    },
    ...more sections with 1-3 slides each...
  ]
}

MANDATORY SECTIONS (include ALL of these):
cover, table_of_contents, executive_summary, corporate_overview, understanding_of_scope, proposed_solution, architecture, technology_stack, delivery_approach, timeline, team_structure, commercials, risk_mitigation, case_studies, next_steps, closing

SLIDE PLANNING RULES:
1. Plan 20-30 meaningful slides total (not counting section dividers — those are added automatically).
2. Each slide must have a clear PURPOSE connected to the user's prompt. Reference the client by name in every purpose.
3. The architecture section MUST have at least 1 slide using layout "migration_flow" — this renders a professional multi-zone architecture diagram.
4. Use VARIED layouts. Available layouts: content, two_column, icon_grid, process_flow, comparison_table, stats_highlight, key_value, architecture, technology, challenges, timeline, team, migration_flow, service_grid, architecture_diagram.
5. Never use "content" layout for more than 3 slides total. Prefer visual layouts.
6. understanding_of_scope should have 2-3 slides (current state, challenges, scope overview).
7. proposed_solution should have 2-3 slides (solution overview, components, expected outcomes).
8. case_studies should have 2-3 slides (different relevant engagements).
9. Every key_points list must contain SPECIFIC items about this client's project — no generic filler.

CRITICAL RULES:
- ALWAYS use the customer name and project details provided by the USER. NEVER copy or reuse organization names from reference material.
- Reference material is ONLY for understanding structure and style.
- Always return valid JSON. No markdown formatting around it."""


def generate_slide_plan(user_input: str, references: list[dict] = None,
                        conversation_history: list[dict] = None,
                        images: list[dict] = None) -> dict:
    """Phase 1: Generate a slide-by-slide plan from user input."""
    ref_context = ""
    if references:
        ref_snippets = [f"- {r.get('text', '')[:200]}" for r in references[:8]]
        ref_context = (
            "\n\n[STYLE REFERENCE ONLY — do NOT copy names, clients, or specifics from these. "
            "Use them only to understand Xebia's writing style and proposal structure.]\n"
            + "\n".join(ref_snippets)
        )

    conv_context = ""
    if conversation_history:
        msgs = [f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conversation_history[-10:]]
        conv_context = "\n\nConversation so far:\n" + "\n".join(msgs)

    user_message = user_input + ref_context + conv_context

    contents = []
    if images:
        for img in images:
            img_path = Path(img.get("path", ""))
            if img_path.exists():
                mime = img.get("mime_type", "image/png")
                contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type=mime))
        if contents:
            user_message += "\n\n[Reference images are attached. Analyze them to understand the architecture, technology stack, and design patterns shown. Incorporate relevant details into the proposal.]"

    contents.append(user_message)

    text = _call_gemini(SLIDE_PLAN_PROMPT, contents, temperature=0.7, max_output_tokens=8000)
    return _parse_json_response(text)


# ---------------------------------------------------------------------------
# Phase 2: Content Generation
# ---------------------------------------------------------------------------

CONTENT_GEN_PROMPT = """You are Xebia Proposal Studio's content engine. You receive a slide plan and must generate RICH, DETAILED, CLIENT-SPECIFIC content for every slide.

You will be given:
1. A slide plan with sections and their planned slides
2. The original user prompt with project details
3. Reference material for style guidance

YOUR OUTPUT must be a single JSON object with this exact structure:
{
  "title": "Proposal title",
  "customer": "Customer name",
  "industry": "...",
  "objective": "...",
  "storyline": ["cover", "table_of_contents", "executive_summary", ...],
  "sections": { ...one key per section with full content... }
}

SECTION CONTENT SCHEMAS — follow these EXACTLY for each section:

"cover": {"title": "...", "subtitle": "one-line value proposition mentioning the client", "customer": "...", "date": "YYYY-MM-DD"}

"executive_summary": {
  "title": "Executive Summary",
  "summary": "2-3 sentences: mention the customer's specific challenge, Xebia's tailored approach, and quantified expected outcome",
  "key_points": ["4-6 specific, quantified points — e.g. 'Reduce data pipeline latency from 4 hours to under 15 minutes'"]
}

"corporate_overview": {
  "title": "About Xebia",
  "layout": "icon_grid",
  "items": [{"label": "capability area", "description": "1-2 sentence detail"}, ...] (6-8 items)
}

"understanding_of_scope": {
  "title": "Understanding of Scope",
  "slides": [
    {"title": "Current State Assessment", "layout": "content", "body": "paragraph about client's current situation with specific technologies and pain points", "bullets": ["specific scope items"]},
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
      "layout": "migration_flow",
      "diagram": {
        "zones": [
          {
            "title": "Source Systems",
            "color": "orange",
            "groups": [
              {"label": "Databases", "items": ["Oracle", "SQL Server", "PostgreSQL"], "style": "icons"},
              {"label": "APIs", "items": ["SAP OData", "REST APIs"], "style": "pills"}
            ]
          },
          {
            "title": "Ingestion Layer",
            "color": "teal",
            "groups": [
              {"label": "Pipelines", "items": ["Azure Data Factory", "Synapse Pipelines"], "style": "icons"}
            ]
          },
          {
            "title": "Processing & Analytics",
            "color": "blue",
            "groups": [
              {"label": "Compute", "items": ["Spark", "Dataflows Gen2"], "style": "icons"},
              {"label": "Storage", "items": ["OneLake", "Delta Tables"], "style": "pills"}
            ]
          },
          {
            "title": "Serving & Consumption",
            "color": "purple",
            "groups": [
              {"label": "BI & Reporting", "items": ["Power BI", "Direct Lake"], "style": "icons"}
            ]
          }
        ],
        "bottom_bands": [
          {"label": "Security & Governance", "items": ["Entra ID", "Key Vault", "Purview"]}
        ]
      }
    }
  ]
}
ARCHITECTURE IS MANDATORY. Always use "migration_flow" layout with the zones/groups/items format shown above.
Use real technology names relevant to the project. Include 3-5 zones with 1-2 groups each. Choose zone colors from: orange, teal, blue, purple, green, dark.
Group styles: "icons" (for technology products — tries to show actual icons), "pills" (for items shown as rounded tags), "flow" (for sequential items), "text" (plain text list).

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
  "steps": [{"label": "Phase Name", "description": "what happens in this phase"}, ...] (4-6 steps)
}

"timeline": {
  "title": "Project Timeline",
  "phases": [{"name": "Phase 1: ...", "duration": "Week 1-4", "description": "key deliverables and milestones"}, ...] (4-6 phases)
}

"team_structure": {
  "title": "Proposed Team",
  "members": [
    {"name": "realistic name", "role": "Solution Architect|Data Engineer|Cloud Engineer|DevOps Engineer|QA Lead|Project Manager|Business Analyst", "expertise": "specific technologies relevant to this project"},
    ... (4-8 members)
  ]
}

"commercials": {
  "title": "Investment Summary",
  "rows": [
    {"item": "Role Name", "hours": "total hours", "rate": "hourly rate", "cost": "total cost"},
    ...
  ],
  "total": "grand total",
  "assumptions": ["Payment terms", "Travel excluded", "Rate validity period", ...]
}

"risk_mitigation": {
  "title": "Risk Mitigation",
  "slides": [
    {
      "title": "Risks & Mitigation",
      "layout": "challenges",
      "challenges": [
        {"challenge": "specific risk for THIS project", "impact": "business impact", "solution": "concrete mitigation"},
        ... (4-6 risks)
      ]
    }
  ]
}

"case_studies": {
  "title": "Relevant Experience",
  "slides": [
    {"title": "Client – Project", "layout": "key_value", "pairs": [
      {"key": "Client", "value": "..."},
      {"key": "Challenge", "value": "..."},
      {"key": "Solution", "value": "..."},
      {"key": "Impact", "value": "quantified result"},
      {"key": "Technologies", "value": "..."}
    ]},
    ... (2-3 case studies in the SAME industry/technology domain)
  ]
}

"next_steps": {
  "title": "Next Steps",
  "layout": "process_flow",
  "steps": [{"label": "Step", "description": "specific action item with timeline"}, ...] (3-5 steps)
}

"closing": {"title": "Thank You", "contact_name": "...", "contact_email": "...", "body": "personalized closing message mentioning the customer"}

AVAILABLE SLIDE LAYOUTS (use the best one for each slide):
- "content": title + body + bullets. For general text.
- "two_column": two side-by-side columns with "left"/"right" having "title" and "bullets".
- "icon_grid": grid of labeled cards with "items": [{"label", "description"}].
- "process_flow": numbered horizontal steps with "steps": [{"label", "description"}].
- "comparison_table": styled table with "headers" and "rows".
- "stats_highlight": large KPI numbers with "stats": [{"value", "label"}].
- "key_value": left-right pairs with "pairs": [{"key", "value"}].
- "migration_flow": professional multi-zone architecture diagram with "diagram": {"zones": [...], "bottom_bands": [...]}.
- "architecture": basic layered diagram with "layers": [{"name", "components", "color"}]. Use migration_flow instead when possible.
- "technology": tech cards with "technologies": [{"name", "category", "description"}].
- "challenges": 3-column challenge/impact/solution with "challenges": [{"challenge", "impact", "solution"}].
- "timeline": phase bars with "phases": [{"name", "duration", "description"}].
- "team": member cards with "members": [{"name", "role", "expertise"}].
- "service_grid": service/capability grid with "diagram": {"zones": [...]}.
- "architecture_diagram": complex multi-zone diagram with "diagram": {"zones": [...]}.

IMAGE QUERIES:
Every slide object should include an "image_query" field — a 2-4 word search phrase for a relevant stock photo.

CONTENT QUALITY RULES:
1. EVERY section must have meaningful, specific content. No empty sections, no "TBD".
2. Use at least 8 DIFFERENT layout types across the proposal. Never use "content" for more than 2 slides.
3. ALL text must reference the customer's name, industry, technologies, and specific challenges.
4. Architecture section MUST use "migration_flow" layout with zones/groups/items format.
5. Stats and metrics must be realistic and quantified.
6. Team members need realistic names, specific roles, and relevant expertise.
7. Case studies must be plausible Xebia engagements in the same industry/technology.
8. Bullets: concise (under 15 words each) but specific. No generic consulting jargon.
9. The client name must appear in at least every 3rd slide's content.
10. For commercials, use rates in the $150-250/hr range unless specified.
11. DO NOT include section dividers in the output — they are added automatically by the renderer.

CRITICAL RULES:
- ALWAYS use the customer name and project details from the slide plan. NEVER copy organization names from reference material.
- Reference material is ONLY for understanding Xebia's writing style and proposal structure.
- Always return valid JSON. No markdown formatting around it."""


def generate_slide_content(slide_plan: dict, user_input: str,
                           references: list[dict] = None) -> dict:
    """Phase 2: Generate rich content for every slide based on the plan."""
    ref_context = ""
    if references:
        ref_snippets = [f"- {r.get('text', '')[:200]}" for r in references[:8]]
        ref_context = (
            "\n\n[STYLE REFERENCE ONLY — do NOT copy names, clients, or specifics.]\n"
            + "\n".join(ref_snippets)
        )

    prompt = f"""SLIDE PLAN TO GENERATE CONTENT FOR:
{json.dumps(slide_plan, indent=2)}

ORIGINAL USER REQUEST:
{user_input}
{ref_context}

Generate the complete proposal content following the slide plan above. Every section in the plan must have full, rich, client-specific content. Use the exact customer name "{slide_plan.get('customer', 'the client')}" throughout."""

    text = _call_gemini(CONTENT_GEN_PROMPT, prompt, temperature=0.7, max_output_tokens=16000)
    result = _parse_json_response(text)

    if "ready" not in result:
        result["ready"] = True
    if "customer" not in result:
        result["customer"] = slide_plan.get("customer", "")
    if "title" not in result:
        result["title"] = slide_plan.get("title", "Proposal")

    return result


# ---------------------------------------------------------------------------
# Phase 3: Post-Generation Review
# ---------------------------------------------------------------------------

REVIEW_PROMPT = """You are a quality reviewer for Xebia Proposal Studio. You review generated proposal content to ensure it meets enterprise quality standards.

You will receive:
1. The original user prompt describing what the proposal should cover
2. The generated proposal plan JSON
3. Text extracted from all generated slides

Your job: evaluate the proposal's quality and suggest specific fixes.

Return a JSON object:
{
  "score": 1-10,
  "issues": [
    {
      "section": "section_key",
      "issue": "specific problem",
      "fix": "concrete fix"
    }
  ],
  "missing_topics": ["topic that should be covered but isn't"],
  "content_patches": {
    "section_key": {
      ...partial update to merge into the section's content...
    }
  }
}

SCORING CRITERIA:
- 9-10: Exceptional — client-specific throughout, varied layouts, rich detail, architecture present
- 7-8: Good — mostly specific, good layout variety, minor gaps
- 5-6: Mediocre — some generic content, limited layout variety, missing sections
- 3-4: Poor — mostly generic, repetitive layouts, missing architecture
- 1-2: Unacceptable — placeholder text, wrong client name, empty sections

THINGS TO CHECK:
1. Does every section reference the client's name and specific project?
2. Is the architecture section using migration_flow layout with real technology names?
3. Are at least 8 different layout types used?
4. Are metrics and stats specific and realistic?
5. Are case studies in the right industry/technology domain?
6. Is the team composition appropriate for the project scope?
7. Are commercials realistic for the team and timeline?
8. Are there any generic/placeholder phrases like "industry-leading", "best-in-class", "state-of-the-art"?

CONTENT PATCHES:
- Only include patches for sections scoring below 7
- Patches are MERGED into the existing section content
- Include the FULL replacement content for patched fields

Always return valid JSON. No markdown formatting."""


def review_proposal(user_input: str, plan: dict,
                    slide_texts: list[str]) -> dict:
    """Phase 3: Review generated proposal and suggest quality improvements."""
    client = _get_client()

    slides_text = "\n\n".join(
        f"--- Slide {i+1} ---\n{text}" for i, text in enumerate(slide_texts)
    )

    prompt = f"""ORIGINAL USER REQUEST:
{user_input}

GENERATED PROPOSAL PLAN:
{json.dumps(plan, indent=2)[:8000]}

EXTRACTED SLIDE TEXT ({len(slide_texts)} slides):
{slides_text[:6000]}

Review this proposal for quality, relevance, and completeness. The customer is "{plan.get('customer', 'unknown')}"."""

    text = _call_gemini(REVIEW_PROMPT, prompt, temperature=0.3, max_output_tokens=4000)
    return _parse_json_response(text)


# ---------------------------------------------------------------------------
# Legacy compatibility — still used during transition
# ---------------------------------------------------------------------------

def generate_proposal_plan(user_input: str, references: list[dict] = None,
                           conversation_history: list[dict] = None,
                           images: list[dict] = None) -> dict:
    """Legacy single-call function — delegates to Phase 1 slide planning."""
    return generate_slide_plan(user_input, references, conversation_history, images)
