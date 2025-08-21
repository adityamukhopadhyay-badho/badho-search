from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import faiss  # type: ignore
import numpy as np
import pandas as pd
import jellyfish
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn

from .config import (
    ARTIFACTS_DIR,
    CSV_PATH,
    INDEX_PATH,
    LOOKUP_PATH,
    META_PATH,
    VOCAB_PATH,
)
from .embeddings import embed_texts_parallel


@dataclass
class BuildStats:
    num_items: int
    embedding_dim: int


def _prepare_dataframe(csv_path: Path, max_rows: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows)
    # Expected columns: product_name, brand_name, category_name
    required = {"product_name", "brand_name", "category_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    def safe_lower(x: str) -> str:
        return str(x).strip().lower()

    df["product_name"] = df["product_name"].astype(str).map(safe_lower)
    df["brand_name"] = df["brand_name"].astype(str).map(safe_lower)
    df["category_name"] = df["category_name"].astype(str).map(safe_lower)

    df["search_text"] = (
        df["brand_name"].fillna("")
        + " "
        + df["product_name"].fillna("")
        + " "
        + df["category_name"].fillna("")
    ).str.strip()

    has_double = hasattr(jellyfish, "double_metaphone")

    def dmeta_or_meta_both(text: str) -> tuple[str, str]:
        if has_double:
            p, a = jellyfish.double_metaphone(text)
            return ((p or "").upper(), (a or "").upper())
        code = (jellyfish.metaphone(text) or "").upper()
        return (code, "")

    # Brand and product phonetics (store primary and alternate)
    brand_codes = df["brand_name"].map(dmeta_or_meta_both)
    product_codes = df["product_name"].map(dmeta_or_meta_both)

    df["brand_phonetic_primary"], df["brand_phonetic_alt"] = zip(*brand_codes)
    df["product_phonetic_primary"], df["product_phonetic_alt"] = zip(*product_codes)

    # Back-compat single-code fields (primary)
    df["brand_phonetic"] = df["brand_phonetic_primary"]
    df["product_phonetic"] = df["product_phonetic_primary"]

    return df


def _build_lookup(df: pd.DataFrame) -> List[dict]:
    records: List[dict] = []
    for row in df[[
        "product_name",
        "brand_name",
        "category_name",
        "brand_phonetic",
        "product_phonetic",
        "brand_phonetic_alt",
        "product_phonetic_alt",
    ]].itertuples(index=False):
        product_name, brand_name, category_name, brand_phonetic, product_phonetic, brand_phonetic_alt, product_phonetic_alt = row
        records.append(
            {
                "label": str(product_name).strip(),
                "brandLabel": str(brand_name).strip(),
                "category": str(category_name).strip(),
                "brand_phonetic": str(brand_phonetic).strip(),
                "product_phonetic": str(product_phonetic).strip(),
                "brand_phonetic_alt": str(brand_phonetic_alt).strip(),
                "product_phonetic_alt": str(product_phonetic_alt).strip(),
            }
        )
    return records


def build_index(csv_path: Path | None = None, max_rows: int | None = None, workers: int = 4) -> BuildStats:
    csv_path = csv_path or CSV_PATH

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    df = _prepare_dataframe(csv_path, max_rows=max_rows)

    texts: List[str] = df["search_text"].tolist()

    progress = Progress(
        TextColumn("[bold blue]Embeddings"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )

    with progress:
        task = progress.add_task("embed", total=len(texts))
        def tick():
            progress.advance(task, 1)
        embeddings: np.ndarray = embed_texts_parallel(texts, max_workers=workers, progress_update=tick)

    if embeddings.ndim != 2 or embeddings.shape[0] != len(texts):
        raise RuntimeError("Embedding matrix shape mismatch")

    num_items, embedding_dim = embeddings.shape

    index = faiss.IndexFlatL2(embedding_dim)
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, str(INDEX_PATH))

    product_lookup: List[dict] = _build_lookup(df)
    with open(LOOKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(product_lookup, f, ensure_ascii=False)

    # Persist a tiny phonetic vocabulary from all codes (primary and alternate)
    vocab = sorted({
        *(rec.get("brand_phonetic", "") for rec in product_lookup),
        *(rec.get("product_phonetic", "") for rec in product_lookup),
        *(rec.get("brand_phonetic_alt", "") for rec in product_lookup),
        *(rec.get("product_phonetic_alt", "") for rec in product_lookup),
    })
    with open(VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump([v for v in vocab if v], f)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "num_items": num_items,
                "embedding_dim": embedding_dim,
                "model": "nomic-embed-text",
                "index_type": "IndexFlatL2",
            },
            f,
        )

    return BuildStats(num_items=num_items, embedding_dim=embedding_dim)


if __name__ == "__main__":
    stats = build_index()
    print(f"Built index with {stats.num_items} items, dim={stats.embedding_dim}") 