"""Batch extract all PPTX files from a directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from extraction.pptx_extractor import extract_pptx, save_extraction


def extract_all(input_dir: str, output_dir: str = "extracted/ppt"):
    input_path = Path(input_dir)
    pptx_files = sorted(input_path.glob("*.pptx"))

    if not pptx_files:
        print(f"No .pptx files found in {input_path}")
        return

    print(f"Found {len(pptx_files)} PPTX files in {input_path}\n")

    for f in pptx_files:
        try:
            result = extract_pptx(f)
            out = save_extraction(result, output_dir)
            meta = result["metadata"]
            cls = result["classification"]
            print(f"  {meta['filename']}")
            print(f"    Slides: {meta['slide_count']} | Type: {cls['proposal_type']}")
            print(f"    Industries: {', '.join(cls['industries'])}")
            print(f"    Technologies: {', '.join(cls['technologies'])}")
            print(f"    -> {out}\n")
        except Exception as e:
            print(f"  FAILED: {f.name} — {e}\n")

    print("Done.")


if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "Documents"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted/ppt"
    extract_all(input_dir, output_dir)
