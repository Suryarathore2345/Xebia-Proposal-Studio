"""Similarity search over the embedding store.

Given a query string, finds the most relevant slides/sections
from the reference library using cosine similarity.
"""

import numpy as np
from retrieval.embedding_store import load_embeddings
from retrieval.embedder import embed_text


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def search(query: str, top_k: int = 10, store_name: str = "embeddings",
           entity_type: str = None, min_score: float = 0.3,
           industry: str = None, technology: str = None) -> list[dict]:
    """Search the embedding store for the most relevant content.

    Args:
        query: Free-text search query
        top_k: Number of results to return
        store_name: Name of the embedding store file
        entity_type: Filter to "slide" or "section" only
        min_score: Minimum similarity score threshold
        industry: Filter to specific industry
        technology: Filter to specific technology

    Returns:
        List of results sorted by relevance, each with:
        {score, entity_type, source_file, entity_id, text, metadata}
    """
    query_embedding = embed_text(query)
    entries = load_embeddings(store_name)

    if not entries:
        return []

    results = []
    for entry in entries:
        if entity_type and entry.get("entity_type") != entity_type:
            continue

        meta = entry.get("metadata", {})

        if industry:
            industries = meta.get("industries", [])
            if industry.lower() not in [i.lower() for i in industries]:
                continue

        if technology:
            technologies = meta.get("technologies", [])
            if technology.lower() not in [t.lower() for t in technologies]:
                continue

        score = cosine_similarity(query_embedding, entry["embedding"])

        if score >= min_score:
            results.append({
                "score": round(score, 4),
                "entity_type": entry["entity_type"],
                "source_file": entry["source_file"],
                "entity_id": entry["entity_id"],
                "text": entry["text"],
                "metadata": meta,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def search_for_proposal(requirement: str, top_k: int = 15,
                        store_name: str = "embeddings") -> dict:
    """Search for reference content relevant to a proposal requirement.

    Returns separate content and layout references as recommended
    by the blueprint.
    """
    content_results = search(
        query=requirement,
        top_k=top_k,
        store_name=store_name,
        min_score=0.25,
    )

    slide_results = [r for r in content_results if r["entity_type"] == "slide"]
    section_results = [r for r in content_results if r["entity_type"] == "section"]

    slide_types = {}
    for r in slide_results:
        st = r["metadata"].get("slide_type", "content")
        if st not in slide_types:
            slide_types[st] = r

    return {
        "content_references": content_results[:top_k],
        "slide_references": slide_results[:10],
        "section_references": section_results[:10],
        "layout_references": list(slide_types.values()),
        "query": requirement,
        "total_matches": len(content_results),
    }
