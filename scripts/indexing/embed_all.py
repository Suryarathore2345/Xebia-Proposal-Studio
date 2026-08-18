"""Batch embed all extracted reference documents."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from retrieval.embedder import embed_pptx_extraction, embed_docx_extraction


def embed_all(extracted_dir: str = "extracted"):
    base = Path(extracted_dir)

    # Embed PPT extractions
    ppt_dir = base / "ppt"
    ppt_files = sorted(ppt_dir.glob("*.json")) if ppt_dir.exists() else []

    if ppt_files:
        print(f"Embedding {len(ppt_files)} PPT extractions...\n")
        for f in ppt_files:
            stats = embed_pptx_extraction(f)
            print(f"  {stats['file']}")
            print(f"    Slides: {stats['total_slides']} | New embeddings: {stats['embedded']} | Skipped: {stats['skipped']}")
        print()

    # Embed DOCX extractions
    docx_dir = base / "docx"
    docx_files = sorted(docx_dir.glob("*.json")) if docx_dir.exists() else []

    if docx_files:
        print(f"Embedding {len(docx_files)} DOCX extractions...\n")
        for f in docx_files:
            stats = embed_docx_extraction(f)
            print(f"  {stats['file']}")
            print(f"    Sections: {stats['total_sections']} | New embeddings: {stats['embedded']} | Skipped: {stats['skipped']}")
        print()

    if not ppt_files and not docx_files:
        print("No extracted files found. Run the extraction pipeline first.")
        return

    # Summary
    from retrieval.embedding_store import load_embeddings
    all_emb = load_embeddings()
    print(f"Total embeddings in store: {len(all_emb)}")


if __name__ == "__main__":
    embed_all()
