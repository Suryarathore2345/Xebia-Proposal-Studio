"""Embedding generator using sentence-transformers.

Reads extracted JSON files (from the PPT/DOCX extraction pipeline),
generates vector embeddings per slide or section, and saves them
to the embedding store with content hashes for deduplication.
"""

import json
from pathlib import Path

from retrieval.embedding_store import content_hash, save_embeddings, get_all_hashes


_model = None


def _get_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts (batched for efficiency)."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


def embed_pptx_extraction(extraction_path: str | Path, store_name: str = "embeddings") -> dict:
    """Embed all slides from a PPT extraction JSON file.

    Returns stats: {"file": ..., "total_slides": ..., "embedded": ..., "skipped": ...}
    """
    path = Path(extraction_path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    existing_hashes = get_all_hashes(store_name)
    entries = []
    skipped = 0

    slides_to_embed = []
    slide_infos = []

    for slide in data.get("slides", []):
        text = slide.get("text", "").strip()
        if not text or len(text) < 20:
            skipped += 1
            continue

        c_hash = content_hash(text)
        if c_hash in existing_hashes:
            skipped += 1
            continue

        slides_to_embed.append(text)
        slide_infos.append({
            "slide": slide,
            "c_hash": c_hash,
            "source_file": data["metadata"]["filename"],
        })

    if slides_to_embed:
        embeddings = embed_texts(slides_to_embed)

        for info, embedding in zip(slide_infos, embeddings):
            entries.append({
                "entity_type": "slide",
                "source_file": info["source_file"],
                "entity_id": info["slide"]["slide_number"],
                "text": info["slide"]["text"][:500],
                "content_hash": info["c_hash"],
                "embedding": embedding,
                "metadata": {
                    "slide_type": info["slide"].get("slide_type", ""),
                    "word_count": info["slide"].get("word_count", 0),
                    "industries": data.get("classification", {}).get("industries", []),
                    "technologies": data.get("classification", {}).get("technologies", []),
                    "proposal_type": data.get("classification", {}).get("proposal_type", ""),
                },
            })

    new_count = 0
    if entries:
        new_count = save_embeddings(entries, store_name)

    return {
        "file": data["metadata"]["filename"],
        "total_slides": len(data.get("slides", [])),
        "embedded": new_count,
        "skipped": skipped,
    }


def embed_docx_extraction(extraction_path: str | Path, store_name: str = "embeddings") -> dict:
    """Embed all sections from a DOCX extraction JSON file."""
    path = Path(extraction_path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    existing_hashes = get_all_hashes(store_name)
    entries = []
    skipped = 0

    sections_to_embed = []
    section_infos = []

    for i, section in enumerate(data.get("sections", [])):
        text = section.get("text", "").strip()
        if not text or len(text) < 20:
            skipped += 1
            continue

        c_hash = content_hash(text)
        if c_hash in existing_hashes:
            skipped += 1
            continue

        sections_to_embed.append(text)
        section_infos.append({
            "section": section,
            "index": i,
            "c_hash": c_hash,
            "source_file": data["metadata"]["filename"],
        })

    if sections_to_embed:
        embeddings = embed_texts(sections_to_embed)

        for info, embedding in zip(section_infos, embeddings):
            entries.append({
                "entity_type": "section",
                "source_file": info["source_file"],
                "entity_id": info["index"],
                "text": info["section"]["text"][:500],
                "content_hash": info["c_hash"],
                "embedding": embedding,
                "metadata": {
                    "heading": info["section"].get("heading", ""),
                    "heading_level": info["section"].get("heading_level", 0),
                    "word_count": info["section"].get("word_count", 0),
                    "industries": data.get("classification", {}).get("industries", []),
                    "technologies": data.get("classification", {}).get("technologies", []),
                },
            })

    new_count = 0
    if entries:
        new_count = save_embeddings(entries, store_name)

    return {
        "file": data["metadata"]["filename"],
        "total_sections": len(data.get("sections", [])),
        "embedded": new_count,
        "skipped": skipped,
    }
