## Badho Search (Prototype: Sub-100ms)

This project implements an offline-built FAISS index with real-time hybrid search (semantic + phonetic boost) using a local Ollama embeddings model.

### Tech Stack
- Ollama (`nomic-embed-text`) for embeddings (local API)
- FAISS `IndexFlatL2` for vector search
- Jellyfish `double_metaphone` for phonetic boosting
- NumPy for numerics; Pandas only in offline build

### 1) Environment Setup
1. Install Ollama and start the server (macOS):
   - Install: see `https://ollama.com/download`
   - Start server: `ollama serve` (runs on `http://localhost:11434`)
   - Pull model: `ollama pull nomic-embed-text`
2. Create a Python virtualenv and install deps:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`

### 2) Offline Indexing (run when CSV updates)
Your product CSV must have columns: `product_name,brand_name,category_name`.

Run:

```bash
python scripts/build_index.py
```

Artifacts written to `artifacts/`:
- `index.faiss` – FAISS IndexFlatL2 over embeddings
- `product_lookup.json` – metadata aligned to vector row order
- `meta.json` – index metadata

### 3) Real-time Hybrid Search
Run a query:

```bash
python scripts/search_cli.py --query "amul butter" --k 5 --pool 50 --boost 0.2 --profile
```

The `--profile` flag prints step timings (embedding, FAISS search, rerank) to help tune latency.

### 4) Docker Deployment 🐳
For production deployment, use Docker and Docker Compose:

```bash
# Quick start
./deploy.sh dev      # Development environment
./deploy.sh prod     # Production environment

# Manual deployment
docker-compose up --build -d
```

**Note**: In Docker, the search app connects to Ollama at `http://ollama:11434` (internal Docker network), while Ollama is accessible externally at `http://localhost:11434`.

See [DOCKER_README.md](DOCKER_README.md) for detailed Docker deployment instructions.
See [NETWORKING.md](NETWORKING.md) for Docker networking architecture explanation.

### Notes
- FAISS build time is zero with `IndexFlatL2`; only embedding time dominates offline build.
- Real-time path includes one embedding call to Ollama; the localhost API latency is often the main contributor. Tune candidate pool size and boost as needed.
- **Local Development**: Ollama at `http://localhost:11434`
- **Docker Deployment**: Search app connects to `http://ollama:11434` (internal), Ollama accessible at `http://localhost:11434` (external)