"""Extract structured content and metadata from DOCX files.

Reads a .docx file and produces a JSON representation with:
- Document-level metadata (title, author, page estimate, word count)
- Section hierarchy (headings and their content)
- Tables
- Images
- Classification
"""

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH


def extract_docx(file_path: str | Path) -> dict:
    """Extract all content and metadata from a DOCX file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = Document(str(file_path))

    metadata = _extract_metadata(doc, file_path)
    sections = _extract_sections(doc)
    tables = _extract_tables(doc)
    image_count = _count_images(doc)

    full_text = " ".join(s["text"] for s in sections)
    word_count = len(full_text.split())

    industries = _detect_industries(full_text)
    technologies = _detect_technologies(full_text)
    doc_type = _detect_document_type(full_text, metadata["filename"])

    return {
        "metadata": {
            **metadata,
            "word_count": word_count,
            "section_count": len(sections),
            "table_count": len(tables),
            "image_count": image_count,
        },
        "classification": {
            "document_type": "docx",
            "proposal_type": doc_type,
            "industries": industries,
            "technologies": technologies,
            "approval_status": "pending_review",
            "confidentiality": "internal",
        },
        "sections": sections,
        "tables": tables,
    }


def _extract_metadata(doc: Document, file_path: Path) -> dict:
    core = doc.core_properties

    with open(file_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()

    return {
        "filename": file_path.name,
        "file_path": str(file_path),
        "file_size_bytes": file_path.stat().st_size,
        "content_hash": content_hash,
        "title": core.title or "",
        "author": core.author or "",
        "last_modified_by": core.last_modified_by or "",
        "created": core.created.isoformat() if core.created else None,
        "modified": core.modified.isoformat() if core.modified else None,
        "extracted_at": datetime.now().isoformat(),
    }


def _extract_sections(doc: Document) -> list[dict]:
    """Extract document content organized by heading hierarchy."""
    sections = []
    current_section = None

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()

        if not text:
            continue

        if style_name.startswith("Heading"):
            try:
                level = int(style_name.replace("Heading", "").strip())
            except ValueError:
                level = 1

            if current_section:
                current_section["text"] = " ".join(current_section["paragraphs"])
                current_section["word_count"] = len(current_section["text"].split())
                sections.append(current_section)

            current_section = {
                "heading": text,
                "level": level,
                "paragraphs": [],
                "text": "",
                "word_count": 0,
            }
        elif current_section:
            current_section["paragraphs"].append(text)
        else:
            current_section = {
                "heading": "(Untitled)",
                "level": 0,
                "paragraphs": [text],
                "text": "",
                "word_count": 0,
            }

    if current_section:
        current_section["text"] = " ".join(current_section["paragraphs"])
        current_section["word_count"] = len(current_section["text"].split())
        sections.append(current_section)

    return sections


def _extract_tables(doc: Document) -> list[dict]:
    """Extract all tables from the document."""
    tables = []
    for i, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            rows.append(row_data)

        header = rows[0] if rows else []
        tables.append({
            "table_index": i,
            "header": header,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(header),
        })
    return tables


def _count_images(doc: Document) -> int:
    """Count inline images in the document."""
    count = 0
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            count += 1
    return count


def _detect_industries(text: str) -> list[str]:
    text_lower = text.lower()
    industry_keywords = {
        "retail": ["retail", "store", "e-commerce"],
        "fmcg": ["fmcg", "cpg", "consumer goods"],
        "financial_services": ["mortgage", "banking", "financial", "loan"],
        "manufacturing": ["manufacturing", "factory"],
        "energy": ["energy", "oil", "gas"],
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
        "azure": ["azure"],
        "databricks": ["databricks"],
        "power_bi": ["power bi"],
        "ai_ml": ["machine learning", "artificial intelligence", "ai/ml"],
        "data_engineering": ["data engineering", "data pipeline"],
    }
    found = []
    for tech, keywords in tech_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(tech)
    return found or ["general"]


def _detect_document_type(text: str, filename: str) -> str:
    combined = (text + " " + filename).lower()
    if any(kw in combined for kw in ["sow", "statement of work"]):
        return "sow"
    if any(kw in combined for kw in ["rfp", "request for proposal"]):
        return "rfp_response"
    if any(kw in combined for kw in ["technical", "architecture"]):
        return "technical_proposal"
    if any(kw in combined for kw in ["proposal"]):
        return "proposal"
    return "document"


def save_extraction(extraction: dict, output_dir: str | Path) -> Path:
    """Save extraction result to JSON."""
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
        print("Usage: python docx_extractor.py <file.docx> [output_dir]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted/docx"

    result = extract_docx(file_path)
    out = save_extraction(result, output_dir)

    meta = result["metadata"]
    cls = result["classification"]
    print(f"Extracted: {meta['filename']}")
    print(f"  Words: {meta['word_count']}")
    print(f"  Sections: {meta['section_count']}")
    print(f"  Tables: {meta['table_count']}")
    print(f"  Images: {meta['image_count']}")
    print(f"  Type: {cls['proposal_type']}")
    print(f"  Saved to: {out}")
