"""Test similarity search against embedded reference documents."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from retrieval.search import search, search_for_proposal


TEST_QUERIES = [
    "Microsoft Fabric migration from Synapse",
    "Data governance and master data management",
    "Retail analytics and demand forecasting",
    "Project team structure and delivery approach",
    "Commercial pricing and investment",
]


def main():
    print("=" * 60)
    print("SIMILARITY SEARCH TEST")
    print("=" * 60)

    for query in TEST_QUERIES:
        print(f"\nQuery: \"{query}\"")
        print("-" * 50)

        results = search(query, top_k=5)

        if not results:
            print("  No results found.")
            continue

        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['score']:.3f}] {r['source_file']} "
                  f"({r['entity_type']} #{r['entity_id']}) "
                  f"[{r['metadata'].get('slide_type', r['metadata'].get('heading', ''))}]")
            print(f"     {r['text'][:100]}...")

    # Test proposal search
    print("\n" + "=" * 60)
    print("PROPOSAL REFERENCE SEARCH")
    print("=" * 60)

    requirement = "Build a data platform on Microsoft Fabric for a retail company with demand forecasting and supply chain analytics"
    print(f"\nRequirement: \"{requirement}\"")
    print("-" * 50)

    refs = search_for_proposal(requirement)
    print(f"  Total matches: {refs['total_matches']}")
    print(f"  Slide references: {len(refs['slide_references'])}")
    print(f"  Section references: {len(refs['section_references'])}")
    print(f"  Layout patterns: {len(refs['layout_references'])}")

    print("\n  Top 5 content references:")
    for i, r in enumerate(refs["content_references"][:5], 1):
        print(f"    {i}. [{r['score']:.3f}] {r['source_file']} — {r['text'][:80]}...")


if __name__ == "__main__":
    main()
