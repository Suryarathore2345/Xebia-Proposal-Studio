"""Gemini client — used only by the Claude/Gemini testing toggle in the
chat UI, so the two can be compared side by side. Not part of the
production path; remove this module together with the toggle once
testing is done.

Reuses SECTION_SCHEMA from anthropic_client so both providers are asked
for the exact same plan structure — the only variable is which model
fills it in.
"""

import os
import json
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from llm.anthropic_client import SECTION_SCHEMA, REVIEW_SYSTEM_PROMPT

MODEL = "gemini-3.6-flash"

_clients: list = []


def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _get_clients() -> list:
    """Return Gemini clients in priority order — as many GEMINI_API_KEY_N
    (or a bare GEMINI_API_KEY as key 1) as are set, tried in order on
    rate-limit/quota failure."""
    global _clients
    if _clients:
        return _clients

    _load_env()
    keys = [os.environ.get("GEMINI_API_KEY_1", "") or os.environ.get("GEMINI_API_KEY", "")]
    n = 2
    while True:
        key = os.environ.get(f"GEMINI_API_KEY_{n}", "")
        if not key:
            break
        keys.append(key)
        n += 1
    keys = [k for k in keys if k]

    if not keys:
        raise RuntimeError("No GEMINI_API_KEY / GEMINI_API_KEY_1..N set in .env or environment")

    _clients = [genai.Client(api_key=k) for k in keys]
    return _clients


def _is_rate_limited(err: Exception) -> bool:
    msg = str(err).lower()
    return "429" in msg or "rate limit" in msg or "quota" in msg or "resource_exhausted" in msg


def _call_with_failover(**kwargs):
    """Try each configured key in order, only failing over on a rate-limit/quota error."""
    clients = _get_clients()
    last_err = None
    for i, client in enumerate(clients):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            last_err = e
            if _is_rate_limited(e) and i < len(clients) - 1:
                print(f"[GeminiClient] Key {i + 1} rate-limited, failing over to key {i + 2}")
                continue
            raise
    raise last_err


def generate_text(prompt: str, max_tokens: int = 2000) -> str:
    """JSON text completion — used by the design engine (theme/blueprint
    selection) when the chat toggle is set to Gemini, so those calls stay
    consistent with the provider chosen for the main content. Every caller
    of this helper expects JSON back, so response_mime_type is forced —
    without it Gemini's plain-text completion was prone to truncating
    mid-string before finishing the JSON object."""
    response = _call_with_failover(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        ),
    )
    return response.text


SYSTEM_PROMPT = f"""You are Xebia Proposal Studio, an AI assistant that creates premium, enterprise-grade proposals for Xebia, a global IT consultancy.

Your job: have a natural conversation to gather requirements, then generate a structured proposal plan with RICH, SPECIFIC content — never generic filler.

CONVERSATION BEHAVIOR:
- If the user's request is vague or missing key details, ask clarifying questions. Ask ONE round of 2-3 focused questions maximum.
- Key details to gather: customer name, project objective, technologies involved, timeline, team size, budget range.
- Be professional but conversational. Keep responses concise.
- When you have enough information (at minimum: customer name and project objective), generate the proposal plan.

WHEN ASKING QUESTIONS (not ready to generate yet):
Return a JSON object: {{"ready": false, "message": "Your conversational response here with questions"}}

WHEN GENERATING A PROPOSAL PLAN:
Return ONLY a JSON object (no markdown, no code fences) with "ready": true and the full plan. The top level of that object MUST include ALL of these keys, every single time — never omit any of them:
{{
  "ready": true,
  "title": "Proposal title",
  "customer": "Customer name",
  "industry": "Customer's industry",
  "objective": "One-line objective",
  "storyline": ["cover", "table_of_contents", "executive_summary", "corporate_overview", "understanding_of_scope", "proposed_solution", "architecture", "technology_stack", "delivery_approach", "timeline", "team_structure", "commercials", "payment_milestones", "support_model", "licensing_estimate", "risk_mitigation", "case_studies", "next_steps", "closing"],
  "sections": {{ ... one entry per storyline item, schema below ... }}
}}
"storyline" is the array of section keys, in the order they should appear — pick the ones relevant to this proposal from the list above, do not invent new ones. Every key in "sections" must have a matching entry in "storyline". Include "table_of_contents" as the SECOND entry (right after "cover") only when the proposal will have more than ~10 sections — omit it for shorter decks. "payment_milestones", "support_model", and "licensing_estimate" are OPTIONAL — include them only for enterprise/complex engagements, and when included keep "commercials", "payment_milestones", "support_model", "licensing_estimate" together as one contiguous block in that order (commercials first); skip all three for smaller or simpler proposals.

{SECTION_SCHEMA}

CONTENT QUALITY RULES:
1. EVERY section must have meaningful, specific content. No empty sections, no placeholder text like "TBD" or "To be discussed".
2. Use at least 6-7 DIFFERENT layout types across the proposal. Never use "content" for more than 2 slides.
3. All text must be specific to the customer's project — mention their name, industry, technologies, and challenges.
4. Architecture section is MANDATORY with real technology names and logical layer organization.
5. Stats and metrics should be realistic and quantified.
6. Bullets should be concise (under 15 words each) but specific.
7. For commercials, use rates in the $150-250/hr range unless specified.
8. If corporate_overview (or any other section) references Xebia's company scale, use these exact verified figures — do not invent alternate numbers: 6,500+ professionals, 16 countries, 25+ years (founded 2001), $400M FY24 revenue. A separate slide renders these automatically; your text must not contradict them (e.g. never write a different headcount like "5,000+ specialists").
9. NEVER present an unvalidated quantitative outcome (TCO reduction %, performance improvement % or multiplier like "10x faster", uptime/downtime claims, "zero downtime", "real-time") as a guaranteed result. Frame every such claim as a target pending validation: "Target 35-40% reduction in platform TCO, to be validated during discovery and benchmarking" — never "This delivers 35% lower TCO." An absolute claim like "0 downtime" must become "minimized downtime through phased migration, parallel validation, and controlled cutover" instead. This applies to stats_highlight "value"/"label" pairs too — e.g. value="5x", label="Target Query Speedup (Benchmark TBD)", not value="10x", label="Faster Query Performance" with no qualifier.

CRITICAL RULES:
- ALWAYS use the customer name and project details provided by the USER. NEVER copy client names or specifics from reference material.
- Reference material is for STRUCTURE and STYLE only.
- Always return valid JSON. No markdown formatting around it."""


def generate_proposal_plan(user_input: str, references: list[dict] = None,
                           conversation_history: list[dict] = None,
                           images: list[dict] = None,
                           layout_references: list[dict] = None,
                           slide_references: list[dict] = None) -> dict:
    """Generate a structured proposal plan via Gemini (testing-only path)."""

    ref_context = ""
    if references:
        ref_snippets = [f"- {r.get('text', '')[:200]}" for r in references[:8]]
        ref_context = (
            "\n\n[STYLE REFERENCE ONLY — do NOT copy names, clients, or specifics from these.]\n"
            + "\n".join(ref_snippets)
        )

    layout_context = ""
    if layout_references:
        layout_snippets = [
            f"- [{r.get('metadata', {}).get('slide_type', 'content')}] {r.get('text', '')[:200]}"
            for r in layout_references[:10]
        ]
        layout_context = "\n\n[LAYOUT REFERENCES]\n" + "\n".join(layout_snippets)

    slide_context = ""
    if slide_references:
        slide_snippets = [f"- {r.get('text', '')[:200]}" for r in slide_references[:6]]
        slide_context = "\n\n[RELATED PAST SLIDES]\n" + "\n".join(slide_snippets)

    conv_context = ""
    if conversation_history:
        msgs = [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in conversation_history[-10:]]
        conv_context = "\n\nConversation so far:\n" + "\n".join(msgs)

    date_context = f"\n\n[Today's date: {date.today().isoformat()}. Use this for the cover date unless the user specifies otherwise.]"

    user_message = user_input + ref_context + layout_context + slide_context + conv_context + date_context

    contents = []
    if images:
        for img in images:
            img_path = Path(img.get("path", ""))
            if img_path.exists():
                mime = img.get("mime_type", "image/png")
                contents.append(types.Part.from_bytes(data=img_path.read_bytes(), mime_type=mime))
    contents.append(user_message)

    response = _call_with_failover(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=16000,
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)

    result = json.loads(text)
    return _fill_missing_top_level(result)


_REVIEW_JSON_NOTE = """

RESPONSE FORMAT: Return a single JSON object (no markdown, no code fences) with the fields
described above (at minimum "ready": true, plus only the top-level fields and "sections"
entries you are actually changing — omit anything left as-is). Do not wrap it in a tool
call or any other structure."""


def review_and_improve_plan(plan: dict) -> dict:
    """Send a generated plan back to Gemini for the same content/flow/layout
    critique pass Claude gets (see review_and_improve_plan in anthropic_client)
    — reuses REVIEW_SYSTEM_PROMPT so both providers are held to the same bar.
    Gemini omits sections it isn't changing exactly like Claude's version, so
    a partial response can only leave sections unchanged, never blank them."""
    plan_json = json.dumps(plan, indent=2)
    user_message = f"Here is the generated proposal plan to review:\n\n{plan_json}"

    response = _call_with_failover(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=REVIEW_SYSTEM_PROMPT + _REVIEW_JSON_NOTE,
            temperature=0.3,
            max_output_tokens=16000,
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)

    revision = json.loads(text)

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


def _fill_missing_top_level(result: dict) -> dict:
    """Gemini (unlike Claude's forced tool-use) sometimes returns "sections"
    without the required top-level fields alongside it. Derive them from
    the section contents rather than silently generating an empty-looking
    plan."""
    if not result.get("ready"):
        return result

    sections = result.get("sections", {})

    if not result.get("storyline"):
        result["storyline"] = list(sections.keys())

    cover = sections.get("cover", {})
    if not result.get("title"):
        result["title"] = cover.get("title") or "Untitled Proposal"
    if not result.get("customer"):
        result["customer"] = cover.get("customer") or "Client"
    if not result.get("objective"):
        exec_summary = sections.get("executive_summary", {})
        result["objective"] = cover.get("subtitle") or exec_summary.get("summary", "")[:150]
    if not result.get("industry"):
        result["industry"] = "technology"

    return result
