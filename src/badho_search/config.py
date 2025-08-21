from __future__ import annotations

from pathlib import Path

# Resolve project root assuming this file lives in src/badho_search/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Data
CSV_PATH: Path = PROJECT_ROOT / "product_catalogue.csv"

# Ollama
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
OLLAMA_TIMEOUT_SECONDS: float = 30.0

# Artifacts
ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
INDEX_PATH: Path = ARTIFACTS_DIR / "index.faiss"
LOOKUP_PATH: Path = ARTIFACTS_DIR / "product_lookup.json"
META_PATH: Path = ARTIFACTS_DIR / "meta.json"
VOCAB_PATH: Path = ARTIFACTS_DIR / "phonetic_vocab.json"

# Embedding generation
EMBED_BATCH_SIZE: int = 1  # Ollama embeddings API typically accepts one input per call

# Search defaults
DEFAULT_K: int = 5
DEFAULT_CANDIDATE_POOL: int = 150
DEFAULT_PHONETIC_BOOST: float = 0.2  # brand-level phonetic boost

# Product-level phonetic and fuzzy boosts for reranking (no CLI args; tuned for sub-100ms)
PRODUCT_PHONETIC_BOOST: float = 0.25
FUZZY_JARO_WEIGHT: float = 50.0  # subtract weight * similarity from distance

# Phonetic tolerance (approximate matching on encoded codes)
PHONETIC_CODE_MAX_EDITS: int = 1  # allow Levenshtein distance <= 1 for tolerant match
PHONETIC_APPROX_BOOST: float = 0.12  # smaller boost for approximate phonetic matches 