"""Proposal planner — orchestrates chat, LLM, search, and generation."""

import sys
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.search import search_for_proposal
from llm.anthropic_client import generate_proposal_plan, review_and_improve_plan
from generation.pptx_generator import generate_proposal_pptx
from generation.docx_generator import generate_proposal_docx


class ProposalSession:
    """Manages a single proposal conversation session."""

    def __init__(self):
        self.session_id = uuid.uuid4().hex[:12]
        self.history: list[dict] = []
        self.plan: dict | None = None
        self.status = "chatting"
        self.generated_files: dict = {}
        self.images: list[dict] = []

    @property
    def reference_images(self) -> list[dict]:
        return [img for img in self.images if img.get("type") == "reference"]

    @property
    def embed_images(self) -> list[dict]:
        return [img for img in self.images if img.get("type") == "embed"]

    def chat(self, user_message: str) -> dict:
        self.history.append({"role": "user", "content": user_message})

        references = self._find_references(user_message)

        try:
            result = generate_proposal_plan(
                user_input=user_message,
                references=references.get("content_references", []) if references else [],
                conversation_history=self.history,
                images=self.images if self.images else None,
                layout_references=references.get("layout_references", []) if references else [],
                slide_references=references.get("slide_references", []) if references else [],
            )
        except Exception as e:
            error_msg = f"I encountered an issue processing your request: {str(e)}"
            self.history.append({"role": "assistant", "content": error_msg})
            return {"ready": False, "message": error_msg}

        if result.get("ready"):
            try:
                reviewed = review_and_improve_plan(result)
                if not reviewed.get("image_placements") and result.get("image_placements"):
                    reviewed["image_placements"] = result["image_placements"]
                result = reviewed
            except Exception as e:
                print(f"[ProposalSession] Review pass failed ({e}), using unreviewed plan")

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
                },
            }
        else:
            msg = result.get("message", "Could you provide more details?")
            self.history.append({"role": "assistant", "content": msg})
            return {"ready": False, "message": msg}

    def generate(self, template_name: str | None = None) -> dict:
        if not self.plan:
            return {"error": "No proposal plan ready. Keep chatting to build one."}

        self.status = "generating"
        output_dir = Path(__file__).resolve().parent.parent.parent / "outputs"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self.plan.get("customer", "proposal").replace(" ", "_")[:30]

        results = {}

        try:
            pptx_path = output_dir / "ppt" / f"{safe_title}_{timestamp}.pptx"
            generate_proposal_pptx(self.plan, pptx_path, template_name=template_name,
                                   embed_images=self.embed_images if self.embed_images else None)
            results["pptx"] = str(pptx_path)
            self.generated_files["pptx"] = str(pptx_path)
        except Exception as e:
            results["pptx_error"] = str(e)

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
