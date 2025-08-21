#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel
from typing import Set

import jellyfish

# Ensure src/ is on sys.path for local execution without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from badho_search.hybrid_search import HybridSearchEngine
from badho_search.config import PHONETIC_CODE_MAX_EDITS, PHONETIC_APPROX_BOOST


def query_phonetic_codes(text: str) -> Set[str]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid search CLI using FAISS + phonetic boost")
    parser.add_argument("--query", type=str, required=True, help="User query string")
    parser.add_argument("--k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--pool", type=int, default=50, help="Candidate pool size for re-ranking")
    parser.add_argument("--boost", type=float, default=0.2, help="Phonetic boost (subtract from distance)")
    parser.add_argument("--profile", action="store_true", help="Print timing breakdown")
    args = parser.parse_args()

    # Show phonetic codes and tolerance info for transparency
    codes = sorted(query_phonetic_codes(args.query))
    rprint(Panel(f"phonetic codes={codes}\nmax_edits={PHONETIC_CODE_MAX_EDITS} | approx_boost={PHONETIC_APPROX_BOOST}", title="phonetics", title_align="left", border_style="dim"))

    engine = HybridSearchEngine()
    results, timing = engine.hybrid_search(
        query=args.query,
        k=args.k,
        phonetic_boost=args.boost,
        candidate_pool=args.pool,
        return_timing=args.profile,
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", justify="right", width=3)
    table.add_column("score", justify="right", width=10)
    table.add_column("brand", justify="left")
    table.add_column("product", justify="left")
    table.add_column("category", justify="left")

    for i, item in enumerate(results, start=1):
        table.add_row(
            str(i),
            f"{item['score']:.4f}",
            str(item.get("brandLabel", "")),
            str(item.get("label", "")),
            str(item.get("category", "")),
        )

    rprint(table)

    if timing:
        rprint(
            Panel(
                f"total={timing.total_ms:.2f}ms | embed={timing.embed_ms:.2f}ms | faiss={timing.faiss_ms:.2f}ms | rerank={timing.rerank_ms:.2f}ms",
                title="timing",
                title_align="left",
                border_style="dim",
            )
        )


if __name__ == "__main__":
    main() 