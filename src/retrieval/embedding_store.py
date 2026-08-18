"""JSON-based embedding storage.

Stores and retrieves embeddings from local JSON files. Each embedded entity
(slide or section) is stored with its content hash so unchanged content
is never re-embedded. When PostgreSQL + pgvector is available, this can
be swapped for a database-backed store.
"""

import json
import hashlib
from pathlib import Path


STORE_DIR = Path(__file__).resolve().parent.parent.parent / "extracted" / "embeddings"


def _ensure_dir():
    STORE_DIR.mkdir(parents=True, exist_ok=True)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def save_embeddings(entries: list[dict], store_name: str = "embeddings"):
    """Save a list of embedding entries to a JSON file.

    Each entry: {
        "entity_type": "slide" | "section",
        "source_file": "filename.pptx",
        "entity_id": 3,
        "text": "...",
        "content_hash": "abc123",
        "embedding": [0.1, 0.2, ...],
        "metadata": { ... }
    }
    """
    _ensure_dir()
    path = STORE_DIR / f"{store_name}.json"

    existing = load_embeddings(store_name)
    existing_hashes = {e["content_hash"] for e in existing}

    new_count = 0
    for entry in entries:
        if entry["content_hash"] not in existing_hashes:
            existing.append(entry)
            existing_hashes.add(entry["content_hash"])
            new_count += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)

    return new_count


def load_embeddings(store_name: str = "embeddings") -> list[dict]:
    """Load all embeddings from a store file."""
    path = STORE_DIR / f"{store_name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_all_hashes(store_name: str = "embeddings") -> set[str]:
    """Get all content hashes already embedded."""
    entries = load_embeddings(store_name)
    return {e["content_hash"] for e in entries}
