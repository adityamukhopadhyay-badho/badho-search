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

### Notes
- FAISS build time is zero with `IndexFlatL2`; only embedding time dominates offline build.
- Real-time path includes one embedding call to Ollama; the localhost API latency is often the main contributor. Tune candidate pool size and boost as needed. 
