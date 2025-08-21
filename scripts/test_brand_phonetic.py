#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Set

import jellyfish

# Ensure src/ is on sys.path for local execution without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from badho_search.config import LOOKUP_PATH, PHONETIC_CODE_MAX_EDITS  # noqa: E402


def query_phonetic_codes(text: str) -> Set[str]:
    """Replicates HybridSearchEngine._query_phonetic_codes logic.

    - Tokenize by whitespace
    - Use jellyfish.double_metaphone if available, otherwise jellyfish.metaphone
    - Collect primary and alternate codes (uppercased)
    """
    codes: Set[str] = set()
    has_double = hasattr(jellyfish, "double_metaphone")
    for token in text.strip().split():
        if not token:
            continue
        if has_double:
            p, a = jellyfish.double_metaphone(token)
            if p:
                codes.add(p.upper())
            if a:
                codes.add(a.upper())
        else:
            code = jellyfish.metaphone(token)
            if code:
                codes.add(code.upper())
    return codes


def is_tolerant_match(record_code: str, codes: Set[str]) -> bool:
    if not record_code:
        return False
    up = record_code.upper()
    if up in codes:
        return True
    try:
        for qc in codes:
            if jellyfish.levenshtein_distance(up, qc) <= int(PHONETIC_CODE_MAX_EDITS):
                return True
    except Exception:
        return False
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Test brand phonetic matching against product_lookup.json")
    parser.add_argument("--brand", type=str, default="colgate", help="Brand name to test (default: colgate)")
    args = parser.parse_args()

    brand = args.brand.strip()
    if not brand:
        print("Please provide a non-empty brand string")
        sys.exit(2)

    codes = query_phonetic_codes(brand)
    print(f"brand='{brand}' -> phonetic codes: {sorted(codes)}")

    lookup_path = Path(LOOKUP_PATH)
    if not lookup_path.exists():
        print(f"Missing lookup file: {lookup_path}. Build the index first (e.g., run scripts/build_index.py).")
        sys.exit(1)

    with open(lookup_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    def record_brand_codes(rec: dict) -> Set[str]:
        return {
            str(rec.get("brand_phonetic", "")).upper(),
            str(rec.get("brand_phonetic_alt", "")).upper(),
        } - {""}

    matches = [r for r in records if any(is_tolerant_match(code, codes) for code in record_brand_codes(r))]

    unique_brands = sorted({str(r.get("brandLabel", "")) for r in matches})
    print(f"matched_records={len(matches)} | unique_matched_brands={len(unique_brands)}")

    preview = unique_brands[:20]
    if preview:
        print("examples:")
        for b in preview:
            print(f"  - {b}")
    else:
        print("No matches found. This could mean your dataset lacks this brand or the phonetic code differs.")


if __name__ == "__main__":
    main() 