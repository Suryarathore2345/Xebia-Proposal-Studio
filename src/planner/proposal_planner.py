"""Proposal planner — orchestrates chat, LLM, search, and generation."""

import re
import sys
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.search import search_for_proposal
from llm import anthropic_client
from generation.pptx_generator import generate_proposal_pptx
from generation.docx_generator import generate_proposal_docx

MIN_SECTIONS_FOR_TOC = 10

_ANONYMIZE_TEAM_PATTERN = re.compile(
    r"no\s+(?:individual\s+|invented\s+|team[\s-]?member\s+)*names?\b"
    r"|without\s+(?:individual\s+)?names?\b"
    r"|role[\s-]only\b"
    r"|anonymiz\w*\b"
    r"|never\s+by\s+named\s+person\b",
    re.IGNORECASE,
)


def _wants_anonymous_team(history: list[dict]) -> bool:
    """True if any user message in this conversation asked to omit
    individual team-member names. Checked independently of whether the
    planning LLM actually complied with an inline instruction to that
    effect — verified during testing that a chat-message instruction
    alone gets overridden by the schema's own "realistic name" example,
    so this makes the omission deterministic instead of hopeful."""
    for msg in history:
        if msg.get("role") == "user" and _ANONYMIZE_TEAM_PATTERN.search(msg.get("content", "")):
            return True
    return False


def _strip_team_names(plan: dict) -> dict:
    """Null out every team member's name — the deterministic guarantee
    behind _wants_anonymous_team, applied regardless of what the LLM
    actually returned."""
    members = plan.get("sections", {}).get("team_structure", {}).get("members", [])
    for m in members:
        if isinstance(m, dict):
            m["name"] = None
    return plan


def _ensure_table_of_contents(plan: dict) -> dict:
    """Insert a table_of_contents entry right after "cover" whenever the
    plan has enough sections to need one. Handled here in code rather than
    left purely to the prompt — the model doesn't reliably follow the
    "include for >10 sections" instruction on its own (observed both
    providers skip it even at 16 sections), so this makes it deterministic."""
    storyline = plan.get("storyline") or []
    if "table_of_contents" in storyline or len(storyline) < MIN_SECTIONS_FOR_TOC:
        return plan

    insert_at = 1 if storyline and storyline[0] == "cover" else 0
    storyline = list(storyline)
    storyline.insert(insert_at, "table_of_contents")
    plan["storyline"] = storyline
    plan.setdefault("sections", {}).setdefault(
        "table_of_contents", {"title": "Table of Contents"})
    return plan


class ProposalSession:
    """Manages a single proposal conversation session."""

    def __init__(self):
        self.session_id = uuid.uuid4().hex[:12]
        self.history: list[dict] = []
        self.plan: dict | None = None
        self.status = "chatting"
        self.generated_files: dict = {}
        self.images: list[dict] = []
        self.last_provider: str = "claude"

    @property
    def reference_images(self) -> list[dict]:
        return [img for img in self.images if img.get("type") == "reference"]

    @property
    def embed_images(self) -> list[dict]:
        return [img for img in self.images if img.get("type") == "embed"]

    def chat(self, user_message: str, provider: str = "claude") -> dict:
        if provider not in ("claude", "gemini"):
            provider = "claude"

        self.history.append({"role": "user", "content": user_message})
        self.last_provider = provider

        references = self._find_references(user_message)
        common_kwargs = dict(
            user_input=user_message,
            references=references.get("content_references", []) if references else [],
            conversation_history=self.history,
            layout_references=references.get("layout_references", []) if references else [],
            slide_references=references.get("slide_references", []) if references else [],
        )

        try:
            if provider == "gemini":
                from llm import gemini_client
                result = gemini_client.generate_proposal_plan(
                    images=self.images if self.images else None, **common_kwargs)
            else:
                result = anthropic_client.generate_proposal_plan(
                    images=self.images if self.images else None, **common_kwargs)
        except Exception as e:
            error_msg = f"I encountered an issue processing your request: {str(e)}"
            self.history.append({"role": "assistant", "content": error_msg})
            return {"ready": False, "message": error_msg}

        if result.get("ready"):
            try:
                if provider == "gemini":
                    from llm import gemini_client
                    reviewed = gemini_client.review_and_improve_plan(result)
                else:
                    reviewed = anthropic_client.review_and_improve_plan(result)
                if not reviewed.get("image_placements") and result.get("image_placements"):
                    reviewed["image_placements"] = result["image_placements"]
                result = reviewed
            except Exception as e:
                print(f"[ProposalSession] Review pass failed ({e}), using unreviewed plan")

            result = _ensure_table_of_contents(result)

            if _wants_anonymous_team(self.history):
                result = _strip_team_names(result)

            try:
                from generation.architecture_generator import elaborate_architecture_diagrams
                result = elaborate_architecture_diagrams(result)
            except Exception as e:
                # Belt-and-suspenders: elaborate_architecture_diagrams already
                # catches per-diagram failures internally and never raises,
                # but if something upstream of that (e.g. the import itself)
                # goes wrong, the plan must still ship with whatever
                # architecture content the main planning call produced.
                print(f"[ProposalSession] Architecture elaboration pass failed ({e}), using plan as-is")

            self.plan = result
            self.status = "plan_ready"
            self.history.append({
                "role": "assistant",
                "content": f"I've prepared a proposal plan: **{result.get('title', 'Proposal')}** for **{result.get('customer', 'your client')}**. Ready to generate the documents!",
            })
            return {
                "ready": True,
                "message": self.history[-1]["content"],
                "plan_summary": {
                    "title": result.get("title", ""),
                    "customer": result.get("customer", ""),
                    "objective": result.get("objective", ""),
                    "sections": len(result.get("storyline", [])),
                    "provider": provider,
                },
            }
        else:
            msg = result.get("message", "Could you provide more details?")
            self.history.append({"role": "assistant", "content": msg})
            return {"ready": False, "message": msg}

    def generate(self, template_name: str | None = None, formats: str = "both") -> dict:
        if not self.plan:
            return {"error": "No proposal plan ready. Keep chatting to build one."}

        if formats not in ("pptx", "docx", "both"):
            return {"error": "formats must be one of 'pptx', 'docx', 'both'"}

        self.status = "generating"
        output_dir = Path(__file__).resolve().parent.parent.parent / "outputs"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self.plan.get("customer", "proposal").replace(" ", "_")[:30]

        results = {}

        if formats in ("pptx", "both"):
            try:
                pptx_path = output_dir / "ppt" / f"{safe_title}_{timestamp}.pptx"
                generate_proposal_pptx(self.plan, pptx_path, template_name=template_name,
                                       embed_images=self.embed_images if self.embed_images else None,
                                       provider=self.last_provider)
                results["pptx"] = str(pptx_path)
                self.generated_files["pptx"] = str(pptx_path)
            except Exception as e:
                results["pptx_error"] = str(e)

        if formats not in ("docx", "both"):
            self.status = "complete"
            return results

        try:
            docx_path = output_dir / "docx" / f"{safe_title}_{timestamp}.docx"
            generate_proposal_docx(self.plan, docx_path)
            results["docx"] = str(docx_path)
            self.generated_files["docx"] = str(docx_path)
        except Exception as e:
            results["docx_error"] = str(e)

        self.status = "complete"
        return results

    def _find_references(self, query: str) -> dict | None:
        try:
            return search_for_proposal(query, top_k=10)
        except Exception:
            return None
