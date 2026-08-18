"""Extract structured content and metadata from PPTX files.

Reads a .pptx file and produces a JSON representation with:
- Document-level metadata (title, slide count, authors, dates)
- Per-slide content (text, shapes, images, tables, notes)
- Per-slide classification (slide type, layout type, content density)
- Visual metadata (has_chart, has_table, has_image, has_diagram)
"""

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN


SLIDE_TYPE_KEYWORDS = {
    "cover": ["prepared for", "presented", "engagement", "proposal", "response"],
    "table_of_contents": ["contents", "agenda", "table of contents"],
    "executive_summary": ["executive summary", "overview"],
    "corporate_overview": ["global footprint", "global presence", "our global", "who we are", "about xebia"],
    "solution": ["proposed solution", "our approach", "solution", "approach"],
    "architecture": ["architecture", "technical design", "system design"],
    "timeline": ["timeline", "roadmap", "project plan", "gantt"],
    "team": ["team structure", "our team", "project team", "delivery team"],
    "commercials": ["commercial", "investment", "pricing", "cost", "fee"],
    "case_study": ["case study", "case studies", "success story", "customer story"],
    "methodology": ["methodology", "delivery approach", "agile", "sprint"],
    "closing": ["thank you", "next steps", "q&a", "questions", "let's go", "contact"],
    "customer_portfolio": ["customer portfolio", "our clients", "client logos"],
    "section_divider": [],
    "content": [],
}


def classify_slide(texts: list[str], shape_count: int, image_count: int) -> str:
    """Classify a slide based on its text content and visual elements."""
    combined = " ".join(texts).lower()

    if not combined.strip() and image_count > 0:
        return "section_divider"

    for slide_type, keywords in SLIDE_TYPE_KEYWORDS.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in combined:
                return slide_type

    if len(combined) < 50 and image_count > 0:
        return "section_divider"

    return "content"


def extract_slide(slide, slide_number: int) -> dict:
    """Extract all content and metadata from a single slide."""
    texts = []
    shapes_data = []
    image_count = 0
    table_count = 0
    chart_count = 0
    has_diagram = False

    for shape in slide.shapes:
        try:
            shape_info = {
                "name": shape.name,
                "shape_type": str(shape.shape_type) if shape.shape_type else "unknown",
                "left": shape.left,
                "top": shape.top,
                "width": shape.width,
                "height": shape.height,
            }

            if shape.has_text_frame:
                paragraphs = []
                for para in shape.text_frame.paragraphs:
                    para_text = para.text.strip()
                    if para_text:
                        paragraphs.append({
                            "text": para_text,
                            "level": para.level,
                            "alignment": str(para.alignment) if para.alignment else None,
                            "bold": any(run.font.bold for run in para.runs if run.font.bold),
                            "font_size": next(
                                (run.font.size for run in para.runs if run.font.size),
                                None
                            ),
                        })
                        texts.append(para_text)
                shape_info["paragraphs"] = paragraphs

            if shape.has_table:
                table_count += 1
                table_data = []
                for row in shape.table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                shape_info["table"] = table_data

            is_picture = False
            try:
                if shape.shape_type is not None and int(shape.shape_type) == 13:
                    is_picture = True
            except Exception:
                pass
            if is_picture or "Picture" in shape.name or "Image" in shape.name:
                image_count += 1
                shape_info["has_image"] = True
            elif "Placeholder" in shape.name and not shape.has_text_frame:
                image_count += 1
                shape_info["has_image"] = True

            try:
                if shape.has_chart:
                    chart_count += 1
                    shape_info["has_chart"] = True
            except Exception:
                pass

            if "SmartArt" in shape.name or "Diagram" in shape.name:
                has_diagram = True

            shapes_data.append(shape_info)
        except Exception:
            shapes_data.append({"name": getattr(shape, "name", "unknown"), "error": True})

    notes_text = ""
    if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
        notes_text = slide.notes_slide.notes_text_frame.text.strip()

    slide_type = classify_slide(texts, len(shapes_data), image_count)

    full_text = " ".join(texts)
    word_count = len(full_text.split())

    if word_count > 200:
        content_density = "high"
    elif word_count > 80:
        content_density = "medium"
    else:
        content_density = "low"

    visual_elements = image_count + chart_count + (1 if has_diagram else 0)
    if visual_elements >= 3:
        visual_density = "high"
    elif visual_elements >= 1:
        visual_density = "medium"
    else:
        visual_density = "low"

    return {
        "slide_number": slide_number,
        "slide_type": slide_type,
        "content_density": content_density,
        "visual_density": visual_density,
        "text": full_text,
        "word_count": word_count,
        "texts": texts,
        "shapes": shapes_data,
        "image_count": image_count,
        "table_count": table_count,
        "chart_count": chart_count,
        "has_diagram": has_diagram,
        "notes": notes_text,
    }


def extract_document_metadata(prs: Presentation, file_path: Path) -> dict:
    """Extract document-level metadata."""
    core = prs.core_properties

    with open(file_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()

    return {
        "filename": file_path.name,
        "file_path": str(file_path),
        "file_size_bytes": file_path.stat().st_size,
        "content_hash": content_hash,
        "slide_count": len(prs.slides),
        "slide_width": prs.slide_width,
        "slide_height": prs.slide_height,
        "title": core.title or "",
        "author": core.author or "",
        "last_modified_by": core.last_modified_by or "",
        "created": core.created.isoformat() if core.created else None,
        "modified": core.modified.isoformat() if core.modified else None,
        "extracted_at": datetime.now().isoformat(),
    }


def extract_pptx(file_path: str | Path) -> dict:
    """Extract all content and metadata from a PPTX file.

    Returns a dict with document metadata and per-slide extracted data,
    ready for JSON serialization or database storage.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    prs = Presentation(str(file_path))

    metadata = extract_document_metadata(prs, file_path)
    slides = []
    slide_type_counts = {}

    for i, slide in enumerate(prs.slides, 1):
        slide_data = extract_slide(slide, i)
        slides.append(slide_data)
        st = slide_data["slide_type"]
        slide_type_counts[st] = slide_type_counts.get(st, 0) + 1

    doc_text = " ".join(s["text"] for s in slides)
    industries = _detect_industries(doc_text)
    technologies = _detect_technologies(doc_text)
    proposal_type = _detect_proposal_type(doc_text, metadata["filename"])

    return {
        "metadata": metadata,
        "classification": {
            "document_type": "pptx",
            "proposal_type": proposal_type,
            "industries": industries,
            "technologies": technologies,
            "slide_type_distribution": slide_type_counts,
            "approval_status": "pending_review",
            "confidentiality": "internal",
        },
        "slides": slides,
    }


def _detect_industries(text: str) -> list[str]:
    text_lower = text.lower()
    industry_keywords = {
        "retail": ["retail", "store", "e-commerce", "ecommerce", "shopping"],
        "fmcg": ["fmcg", "cpg", "consumer goods", "consumer packaged"],
        "financial_services": ["mortgage", "banking", "financial", "loan", "payment"],
        "manufacturing": ["manufacturing", "factory", "tyres", "tires", "production"],
        "energy": ["energy", "oil", "gas", "utilities"],
        "technology": ["saas", "platform", "software"],
        "healthcare": ["health", "pharma", "medical"],
    }
    found = []
    for industry, keywords in industry_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(industry)
    return found or ["general"]


def _detect_technologies(text: str) -> list[str]:
    text_lower = text.lower()
    tech_keywords = {
        "microsoft_fabric": ["fabric", "microsoft fabric"],
        "azure": ["azure", "microsoft azure"],
        "databricks": ["databricks"],
        "power_bi": ["power bi", "powerbi"],
        "synapse": ["synapse"],
        "mdm": ["mdm", "master data"],
        "ai_ml": ["machine learning", "artificial intelligence", "ai/ml", "genai", "gen ai"],
        "data_engineering": ["data engineering", "data pipeline", "etl", "elt"],
        "sap": ["sap", "s/4hana"],
        "oracle": ["oracle"],
    }
    found = []
    for tech, keywords in tech_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(tech)
    return found or ["general"]


def _detect_proposal_type(text: str, filename: str) -> str:
    combined = (text + " " + filename).lower()
    if any(kw in combined for kw in ["technical response", "rfp response", "rfp"]):
        return "rfp_response"
    if any(kw in combined for kw in ["case study", "case studies", "success story"]):
        return "case_study"
    if any(kw in combined for kw in ["kickoff", "kick-off", "kick off"]):
        return "engagement_kickoff"
    if any(kw in combined for kw in ["workshop", "training"]):
        return "workshop"
    if any(kw in combined for kw in ["proposal", "engagement"]):
        return "proposal"
    return "presentation"


def save_extraction(extraction: dict, output_dir: str | Path) -> Path:
    """Save extraction result to a JSON file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = extraction["metadata"]["filename"]
    safe_name = re.sub(r'[^\w\-.]', '_', Path(filename).stem)
    output_path = output_dir / f"{safe_name}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extraction, f, indent=2, ensure_ascii=False, default=str)

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pptx_extractor.py <file.pptx> [output_dir]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted/ppt"

    result = extract_pptx(file_path)
    out = save_extraction(result, output_dir)

    meta = result["metadata"]
    cls = result["classification"]
    print(f"Extracted: {meta['filename']}")
    print(f"  Slides: {meta['slide_count']}")
    print(f"  Type: {cls['proposal_type']}")
    print(f"  Industries: {', '.join(cls['industries'])}")
    print(f"  Technologies: {', '.join(cls['technologies'])}")
    print(f"  Slide types: {cls['slide_type_distribution']}")
    print(f"  Saved to: {out}")
