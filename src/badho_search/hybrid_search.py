from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

import faiss  # type: ignore
import jellyfish
import numpy as np

from .config import (
    DEFAULT_CANDIDATE_POOL,
    DEFAULT_K,
    DEFAULT_PHONETIC_BOOST,
    INDEX_PATH,
    LOOKUP_PATH,
    PRODUCT_PHONETIC_BOOST,
    FUZZY_JARO_WEIGHT,
    PHONETIC_CODE_MAX_EDITS,
    PHONETIC_APPROX_BOOST,
)
from .embeddings import embed_text


@dataclass
class SearchTiming:
    total_ms: float
    embed_ms: float
    faiss_ms: float
    rerank_ms: float


class HybridSearchEngine:
    def __init__(self, index_path: Path | str = INDEX_PATH, lookup_path: Path | str = LOOKUP_PATH):
        self.index: faiss.Index = faiss.read_index(str(index_path))
        with open(lookup_path, "r", encoding="utf-8") as f:
            self.product_lookup: List[dict] = json.load(f)

    @staticmethod
    def _query_phonetic_codes(query: str) -> set[str]:
        codes: set[str] = set()
        has_double = hasattr(jellyfish, "double_metaphone")
        for token in query.strip().split():
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

    def hybrid_search(
        self,
        query: str,
        k: int = DEFAULT_K,
        phonetic_boost: float = DEFAULT_PHONETIC_BOOST,
        candidate_pool: int = DEFAULT_CANDIDATE_POOL,
        return_timing: bool = False,
    ) -> tuple[List[dict], SearchTiming | None]:
        start_t = time.perf_counter()
        query_codes = self._query_phonetic_codes(query)

        t0 = time.perf_counter()
        qvec: np.ndarray = embed_text(query).astype(np.float32)
        t1 = time.perf_counter()

        nprobe = max(candidate_pool, k)
        distances, indices = self.index.search(qvec.reshape(1, -1), nprobe)
        t2 = time.perf_counter()

        # Fuzzy similarity of product label to query using Jaro-Winkler (fast, vector-free)
        # Compute once to reuse
        def fuzzy_score(s: str) -> float:
            # Higher is closer (0..1)
            try:
                return float(jellyfish.jaro_winkler_similarity(query.lower(), s.lower()))
            except Exception:
                return 0.0

        def approx_code_match(record_code: str, qcodes: set[str]) -> bool:
            if not record_code:
                return False
            code_up = record_code.upper()
            # exact
            if code_up in qcodes:
                return True
            # tolerant edit distance
            try:
                for qc in qcodes:
                    if jellyfish.levenshtein_distance(code_up, qc) <= int(PHONETIC_CODE_MAX_EDITS):
                        return True
            except Exception:
                return False
            return False

        ranked_results: List[tuple[float, dict]] = []
        for dist, idx in zip(distances[0].tolist(), indices[0].tolist()):
            if idx < 0:
                continue
            metadata = self.product_lookup[idx]

            # Start with semantic distance
            final_score = float(dist)

            # Brand phonetic boost (consider primary and alternate)
            brand_codes = {
                str(metadata.get("brand_phonetic", "")).upper(),
                str(metadata.get("brand_phonetic_alt", "")).upper(),
            } - {""}
            # exact strong boost
            if brand_codes & query_codes:
                final_score -= float(phonetic_boost)
            else:
                # approximate small boost
                if any(approx_code_match(c, query_codes) for c in brand_codes):
                    final_score -= float(PHONETIC_APPROX_BOOST)

            # Product phonetic boost (consider primary and alternate)
            product_codes = {
                str(metadata.get("product_phonetic", "")).upper(),
                str(metadata.get("product_phonetic_alt", "")).upper(),
            } - {""}
            if product_codes & query_codes:
                final_score -= float(PRODUCT_PHONETIC_BOOST)
            else:
                if any(approx_code_match(c, query_codes) for c in product_codes):
                    final_score -= float(PHONETIC_APPROX_BOOST)

            # Fuzzy string similarity of product label to the query
            label = str(metadata.get("label", ""))
            jw = fuzzy_score(label)
            if jw > 0:
                final_score -= float(FUZZY_JARO_WEIGHT) * jw

            ranked_results.append((final_score, metadata))

        ranked_results.sort(key=lambda x: x[0])
        results: List[dict] = []
        for score, meta in ranked_results[:k]:
            item = dict(meta)
            item["score"] = float(score)
            results.append(item)
        t3 = time.perf_counter()

        embed_ms = (t1 - t0) * 1000.0
        faiss_ms = (t2 - t1) * 1000.0
        rerank_ms = (t3 - t2) * 1000.0
        total_ms = (t3 - start_t) * 1000.0

        timing = SearchTiming(total_ms=total_ms, embed_ms=embed_ms, faiss_ms=faiss_ms, rerank_ms=rerank_ms)
        return (results, timing if return_timing else None) 