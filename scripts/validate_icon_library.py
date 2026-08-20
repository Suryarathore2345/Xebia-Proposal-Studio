"""Validate the technology icon library and generate completeness report.

Checks for:
  - Missing icons (registered but no file)
  - Broken files (too small / corrupt)
  - Duplicate IDs and aliases
  - Orphan files (on disk but not in registry)
  - Low-resolution PNGs
  - Registry/asset mismatches

Usage:
    py scripts/validate_icon_library.py              # full report
    py scripts/validate_icon_library.py --missing     # list missing icons
    py scripts/validate_icon_library.py --orphans     # list orphan files
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets" / "icons"
REGISTRY_PATH = ASSETS_DIR / "registry.json"

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def load_registry() -> list[dict]:
    if not REGISTRY_PATH.exists():
        print("ERROR: registry.json not found. Run build_icon_library.py first.")
        sys.exit(1)
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data.get("icons", [])


def check_file(entry: dict) -> tuple[bool, str | None]:
    for key in ("png_path", "svg_path", "file_path"):
        rel = entry.get(key, "")
        if not rel:
            continue
        full = ASSETS_DIR / rel
        if full.exists():
            sz = full.stat().st_size
            if sz < 100:
                return False, f"broken ({sz} bytes)"
            if full.suffix.lower() == ".png" and HAS_PILLOW:
                try:
                    img = Image.open(full)
                    w, h = img.size
                    if w < 32 or h < 32:
                        return True, f"low-res ({w}x{h})"
                except Exception:
                    return False, "corrupt PNG"
            return True, None
    return False, "missing"


def find_orphans(icons: list[dict]) -> list[str]:
    registered = set()
    for entry in icons:
        for key in ("png_path", "svg_path", "file_path"):
            p = entry.get(key, "")
            if p:
                registered.add(p.replace("\\", "/"))

    orphans = []
    for f in ASSETS_DIR.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".png", ".svg", ".jpg", ".jpeg"):
            if f.name == "registry.json":
                continue
            rel = f.relative_to(ASSETS_DIR).as_posix()
            if rel not in registered:
                orphans.append(rel)
    return sorted(orphans)


def find_duplicates(icons: list[dict]) -> tuple[list[str], list[str]]:
    id_counts: dict[str, int] = {}
    alias_owners: dict[str, list[str]] = {}

    for entry in icons:
        eid = entry.get("id", "")
        id_counts[eid] = id_counts.get(eid, 0) + 1

        for alias in entry.get("aliases", []):
            norm = alias.lower()
            alias_owners.setdefault(norm, []).append(eid)

    dup_ids = [f"{eid} (x{c})" for eid, c in id_counts.items() if c > 1]
    dup_aliases = [
        f"'{alias}' → {owners}"
        for alias, owners in alias_owners.items()
        if len(set(owners)) > 1
    ]
    return dup_ids, dup_aliases


def completeness_by_category(icons: list[dict]) -> dict[str, dict]:
    cats: dict[str, dict] = {}
    for entry in icons:
        cat = entry.get("category", "uncategorized")
        subcat = entry.get("subcategory", "")

        if cat not in cats:
            cats[cat] = {"total": 0, "available": 0, "subcats": {}}
        cats[cat]["total"] += 1

        present, _ = check_file(entry)
        if present:
            cats[cat]["available"] += 1

        if subcat:
            if subcat not in cats[cat]["subcats"]:
                cats[cat]["subcats"][subcat] = {"total": 0, "available": 0}
            cats[cat]["subcats"][subcat]["total"] += 1
            if present:
                cats[cat]["subcats"][subcat]["available"] += 1

    return cats


def print_completeness_report(icons: list[dict]):
    cats = completeness_by_category(icons)
    total = sum(c["total"] for c in cats.values())
    avail = sum(c["available"] for c in cats.values())
    pct = round(avail / total * 100, 1) if total else 0

    print()
    print("=" * 70)
    print("TECHNOLOGY ICON LIBRARY — COMPLETENESS REPORT")
    print("=" * 70)
    print(f"\n  Overall: {avail}/{total} icons ({pct}%)\n")

    for cat in sorted(cats.keys()):
        c = cats[cat]
        p = round(c["available"] / c["total"] * 100) if c["total"] else 0
        bar = "█" * (p // 5) + "░" * (20 - p // 5)
        print(f"  {cat:35s}  {bar}  {p:3d}%  ({c['available']}/{c['total']})")

        for sub in sorted(c["subcats"].keys()):
            s = c["subcats"][sub]
            sp = round(s["available"] / s["total"] * 100) if s["total"] else 0
            print(f"    ├── {sub:31s}  {sp:3d}%  ({s['available']}/{s['total']})")


def print_validation_report(icons: list[dict]):
    print()
    print("=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)

    present = missing_list = broken = low_res = 0
    missing_entries: list[str] = []
    issues: list[str] = []

    for entry in icons:
        eid = entry.get("id", "")
        found, issue = check_file(entry)
        if found:
            present += 1
            if issue:
                low_res += 1
                issues.append(f"LOW-RES: {eid} — {issue}")
        else:
            if issue == "missing":
                missing_list += 1
                missing_entries.append(eid)
            else:
                broken += 1
                issues.append(f"BROKEN: {eid} — {issue}")

    dup_ids, dup_aliases = find_duplicates(icons)
    orphans = find_orphans(icons)

    print(f"\n  Total registered:      {len(icons)}")
    print(f"  Files present:         {present}")
    print(f"  Files missing:         {missing_list}")
    print(f"  Broken files:          {broken}")
    print(f"  Low-resolution:        {low_res}")
    print(f"  Duplicate IDs:         {len(dup_ids)}")
    print(f"  Duplicate aliases:     {len(dup_aliases)}")
    print(f"  Orphan files:          {len(orphans)}")

    coverage = round(present / len(icons) * 100, 1) if icons else 0
    print(f"\n  COVERAGE: {coverage}%")

    if issues:
        print(f"\n  Issues ({len(issues)}):")
        for i in issues[:30]:
            print(f"    • {i}")

    if dup_ids:
        print(f"\n  Duplicate IDs:")
        for d in dup_ids:
            print(f"    • {d}")

    if dup_aliases[:10]:
        print(f"\n  Duplicate aliases (cross-ID):")
        for d in dup_aliases[:10]:
            print(f"    • {d}")

    if orphans[:20]:
        print(f"\n  Orphan files (not in registry):")
        for o in orphans[:20]:
            print(f"    • {o}")
        if len(orphans) > 20:
            print(f"    ... and {len(orphans) - 20} more")

    return missing_entries


def main():
    parser = argparse.ArgumentParser(description="Validate the icon library")
    parser.add_argument("--missing", action="store_true", help="List all missing icons")
    parser.add_argument("--orphans", action="store_true", help="List orphan files")
    args = parser.parse_args()

    icons = load_registry()

    if args.missing:
        print("\nMissing icons:")
        for entry in icons:
            found, _ = check_file(entry)
            if not found:
                eid = entry.get("id", "")
                display = entry.get("display_name", "")
                cat = entry.get("category", "")
                print(f"  {eid:40s}  {display:30s}  [{cat}]")
        return

    if args.orphans:
        orphans = find_orphans(icons)
        print(f"\nOrphan files ({len(orphans)}):")
        for o in orphans:
            print(f"  {o}")
        return

    missing = print_validation_report(icons)
    print_completeness_report(icons)

    print("\n" + "=" * 70)
    print(f"Library location: {ASSETS_DIR}")
    print(f"Registry: {REGISTRY_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
