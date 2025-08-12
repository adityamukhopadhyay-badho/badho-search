#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is on sys.path for local execution without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from badho_search.index_build import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS index and lookup artifacts from CSV")
    parser.add_argument("--csv", type=str, default="", help="Path to product_catalogue.csv (default: project root)")
    parser.add_argument("--max-rows", type=int, default=0, help="Limit number of rows for quick builds (0 = all)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent embedding workers")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else None
    max_rows = args.max_rows if args.max_rows > 0 else None
    stats = build_index(csv_path, max_rows=max_rows, workers=max(1, args.workers))
    print(f"Built index with {stats.num_items} items, embedding_dim={stats.embedding_dim}")


if __name__ == "__main__":
    main() 