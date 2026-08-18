"""Gemini LLM client for proposal content generation."""

import os
import json
from pathlib import Path

from google import genai
from google.genai import types

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client

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

    _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are Xebia Proposal Studio, an AI assistant that helps create professional proposals for Xebia, a global IT consultancy.

Your job is to have a natural conversation with the user to gather requirements, then generate a structured proposal plan.

CONVERSATION BEHAVIOR:
- If the user's request is vague or missing key details, ask clarifying questions. Ask ONE round of 2-3 focused questions maximum.
- Key details to gather: customer name, project objective, technologies involved, timeline, team size, budget range.
- Be professional but conversational. Keep responses concise.
- When you have enough information (at minimum: customer name and project objective), generate the proposal plan.

WHEN GENERATING A PROPOSAL PLAN:
Return ONLY a JSON object (no markdown, no code fences) with this exact structure:
{
  "ready": true,
  "title": "Proposal title",
  "customer": "Customer name",
  "objective": "One-line objective",
  "storyline": ["cover", "table_of_contents", "executive_summary", "corporate_overview", "understanding_of_scope", "proposed_solution", "architecture", "delivery_approach", "timeline", "team_structure", "commercials", "case_studies", "next_steps", "closing"],
  "sections": {
    "cover": {"title": "...", "subtitle": "...", "customer": "...", "date": "..."},
    "executive_summary": {"title": "Executive Summary", "summary": "...", "key_points": ["...", "..."]},
    "corporate_overview": {"title": "About Xebia", "body": "...", "bullets": ["..."]},
    "understanding_of_scope": {"title": "Understanding of Scope", "slides": [{"title": "...", "body": "...", "bullets": ["..."]}]},
    "proposed_solution": {"title": "Proposed Solution", "left": {"title": "...", "bullets": ["..."]}, "right": {"title": "...", "bullets": ["..."]}},
    "architecture": {"title": "Architecture", "slides": [{"title": "...", "body": "...", "bullets": ["..."]}]},
    "delivery_approach": {"title": "Delivery Approach", "body": "...", "bullets": ["..."]},
    "timeline": {"title": "Timeline", "phases": [{"name": "...", "duration": "...", "description": "..."}]},
    "team_structure": {"title": "Team Structure", "members": [{"name": "...", "role": "...", "expertise": "..."}]},
    "commercials": {"title": "Investment", "rows": [{"item": "...", "hours": "...", "rate": "...", "cost": "..."}], "total": "...", "assumptions": ["..."]},
    "case_studies": {"title": "Relevant Experience", "slides": [{"title": "...", "body": "...", "bullets": ["..."]}]},
    "next_steps": {"title": "Next Steps", "bullets": ["..."]},
    "closing": {"title": "Thank You", "contact_name": "...", "contact_email": "...", "body": "We look forward to partnering with you."}
  }
}

WHEN ASKING QUESTIONS (not ready to generate yet):
Return a JSON object:
{"ready": false, "message": "Your conversational response here with questions"}

IMPORTANT:
- Use the reference material to inform content (technologies, approaches, case studies from Xebia's experience).
- Make the proposal content professional, specific, and tailored to the customer's industry.
- Fill in realistic Xebia team roles (Solution Architect, Data Engineer, etc.).
- For commercials, use reasonable consulting rates ($150-250/hr range) unless user specifies.
- Always return valid JSON. No markdown formatting around it."""


def generate_proposal_plan(user_input: str, references: list[dict] = None,
                           conversation_history: list[dict] = None) -> dict:
    """Generate a structured proposal plan from user input and reference context."""
    client = _get_client()

    ref_context = ""
    if references:
        ref_snippets = []
        for r in references[:8]:
            ref_snippets.append(
                f"- [{r.get('source_file', '')}] (score: {r.get('score', 0):.2f}): "
                f"{r.get('text', '')[:200]}"
            )
        ref_context = "\n\nRelevant reference material from past Xebia proposals:\n" + "\n".join(ref_snippets)

    conv_context = ""
    if conversation_history:
        msgs = []
        for msg in conversation_history[-10:]:
            role = msg.get("role", "user")
            msgs.append(f"{role}: {msg.get('content', '')}")
        conv_context = "\n\nConversation so far:\n" + "\n".join(msgs)

    user_message = user_input + ref_context + conv_context

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=8000,
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)


def generate_section_content(section_type: str, context: str,
                              references: list[dict] = None) -> dict:
    """Generate content for a single proposal section."""
    client = _get_client()

    ref_context = ""
    if references:
        snippets = [f"- {r.get('text', '')[:200]}" for r in references[:5]]
        ref_context = "\nReference content:\n" + "\n".join(snippets)

    prompt = f"""Generate content for a "{section_type}" section of a Xebia proposal.

Context: {context}
{ref_context}

Return a JSON object with the section content. Include "title", "body" or "summary", and "bullets" or other relevant fields.
Return ONLY valid JSON, no markdown."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2000,
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)
