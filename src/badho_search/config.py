from __future__ import annotations

import os
from pathlib import Path

# Resolve project root assuming this file lives in src/badho_search/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Data
CSV_PATH: Path = PROJECT_ROOT / "product_catalogue.csv"

# Ollama - Use environment variables with fallbacks
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30.0"))

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