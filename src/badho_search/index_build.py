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

    def brand_phonetic(brand: str) -> str:
        if has_double:
            code_primary, code_alt = jellyfish.double_metaphone(brand)
            return (code_primary or code_alt or "").upper()
        return (jellyfish.metaphone(brand) or "").upper()

    df["brand_phonetic"] = df["brand_name"].map(brand_phonetic)

    return df


def _build_lookup(df: pd.DataFrame) -> List[dict]:
    records: List[dict] = []
    for row in df[["product_name", "brand_name", "category_name", "brand_phonetic"]].itertuples(
        index=False
    ):
        product_name, brand_name, category_name, brand_phonetic = row
        records.append(
            {
                "label": str(product_name).strip(),
                "brandLabel": str(brand_name).strip(),
                "category": str(category_name).strip(),
                "brand_phonetic": str(brand_phonetic).strip(),
            }
        )
    return records


def build_index(csv_path: Path | None = None, max_rows: int | None = None, workers: int = 4) -> BuildStats:
    csv_path = csv_path or CSV_PATH

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    df = _prepare_dataframe(csv_path, max_rows=max_rows)

    texts: List[str] = df["search_text"].tolist()

    # Progress bar for embeddings
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