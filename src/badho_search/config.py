from __future__ import annotations

from pathlib import Path

# Resolve project root assuming this file lives in src/badho_search/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Data
CSV_PATH: Path = PROJECT_ROOT / "product_catalogue.csv"

# Ollama
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_EMBED_MODEL: str = "nomic-embed-text:v1.5"
OLLAMA_TIMEOUT_SECONDS: float = 30.0

# Artifacts
ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
INDEX_PATH: Path = ARTIFACTS_DIR / "index.faiss"
LOOKUP_PATH: Path = ARTIFACTS_DIR / "product_lookup.json"
META_PATH: Path = ARTIFACTS_DIR / "meta.json"

# Embedding generation
EMBED_BATCH_SIZE: int = 1  # Ollama embeddings API typically accepts one input per call

# Search defaults
DEFAULT_K: int = 5
DEFAULT_CANDIDATE_POOL: int = 50
DEFAULT_PHONETIC_BOOST: float = 0.2 