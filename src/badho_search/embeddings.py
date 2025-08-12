from __future__ import annotations

import time
from typing import Iterable, List, Sequence, Optional

import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL, OLLAMA_TIMEOUT_SECONDS


class OllamaEmbeddingError(RuntimeError):
    pass


def _embeddings_endpoint() -> str:
    return f"{OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"


def _post_embed(payload: dict) -> dict:
    try:
        response = requests.post(
            _embeddings_endpoint(), json=payload, timeout=OLLAMA_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise OllamaEmbeddingError(
            "Failed to reach Ollama embeddings endpoint. Ensure Ollama is running (ollama serve) and the model is pulled."
        ) from exc
    if response.status_code != 200:
        raise OllamaEmbeddingError(
            f"Ollama embeddings error {response.status_code}: {response.text[:200]}"
        )
    return response.json()


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string using Ollama embeddings API.

    Returns a 1D numpy float32 vector.
    """
    if not isinstance(text, str) or not text:
        raise ValueError("text must be a non-empty string")

    # First attempt with 'input'
    data = _post_embed({"model": OLLAMA_EMBED_MODEL, "input": text})
    vector = data.get("embedding")

    # Some Ollama versions expect 'prompt' instead of 'input'
    if not vector:
        data = _post_embed({"model": OLLAMA_EMBED_MODEL, "prompt": text})
        vector = data.get("embedding")

    if vector is None:
        embeddings = data.get("embeddings")
        if embeddings and isinstance(embeddings, list) and len(embeddings) == 1:
            vector = embeddings[0]

    if not vector:
        raise OllamaEmbeddingError(
            f"Unexpected/empty embeddings response. Keys={list(data.keys())}"
        )

    arr = np.asarray(vector, dtype=np.float32)
    if arr.ndim != 1:
        raise OllamaEmbeddingError("Expected 1D embedding vector from Ollama")
    return arr


def embed_texts(texts: Iterable[str]) -> np.ndarray:
    """Embed multiple texts; returns a 2D numpy float32 array shaped (n, d)."""
    vectors: List[np.ndarray] = []
    first_dim: int | None = None
    for text in texts:
        vec = embed_text(text)
        if first_dim is None:
            first_dim = int(vec.shape[0])
        else:
            if vec.shape[0] != first_dim:
                raise OllamaEmbeddingError(
                    f"Inconsistent embedding dimensions: got {vec.shape[0]} expected {first_dim}"
                )
        vectors.append(vec)
        time.sleep(0.0)

    if not vectors:
        return np.zeros((0, 0), dtype=np.float32)

    return np.vstack(vectors).astype(np.float32)


def embed_texts_parallel(
    texts: Sequence[str],
    max_workers: int = 4,
    progress_update: Optional[callable] = None,
) -> np.ndarray:
    """Embed texts concurrently with a bounded thread pool.

    - Preserves original order of `texts` in the returned matrix
    - Calls `progress_update()` after each completed item if provided
    """
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    results: dict[int, np.ndarray] = {}
    first_dim: Optional[int] = None

    def task(idx: int, txt: str) -> tuple[int, np.ndarray]:
        return idx, embed_text(txt)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(task, i, t) for i, t in enumerate(texts)]
        for fut in as_completed(futures):
            idx, vec = fut.result()
            if first_dim is None:
                first_dim = int(vec.shape[0])
            elif int(vec.shape[0]) != first_dim:
                raise OllamaEmbeddingError(
                    f"Inconsistent embedding dimensions: got {vec.shape[0]} expected {first_dim}"
                )
            results[idx] = vec.astype(np.float32)
            if progress_update:
                progress_update()

    # Assemble in order
    ordered = [results[i] for i in range(len(texts))]
    return np.vstack(ordered).astype(np.float32) 