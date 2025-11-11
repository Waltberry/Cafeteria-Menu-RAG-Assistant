# Cafeteria Menu RAG Assistant

Ask questions about cafeteria menus, allergens, and nutrition using Retrieval-Augmented Generation (RAG).
Ingest sample docs → chunk → embed (Sentence-Transformers **or** OpenAI) → store in **Postgres + pgvector** → query via **FastAPI** → chat in **Streamlit** with citations.
Data in `data/raw` is **synthetic** for demo—replace with your own PDFs/Markdown and re-ingest.

## Architecture

```
Raw docs (PDF/MD/TXT)
        │
        ▼
Ingest & Chunk  ──► Embeddings (MiniLM or OpenAI)
        │                          │
        └──────────────► Postgres + pgvector (VECTOR(n), ivfflat)
                                   ▲
                                   │
                         FastAPI (/health, /query)
                                   │
                                   ▼
                           Streamlit UI (citations)
```

## TL;DR (Docker)

```bash
cp .env.example .env                  # set USE_OPENAI=0 or 1; add OPENAI_API_KEY if 1
docker compose up -d db               # start Postgres with pgvector
docker compose run --rm ingest        # one-time: index the docs in data/raw/**
docker compose up -d api ui           # API on :8000, UI on :8501
```

* API health: `http://localhost:8000/health`
* UI: `http://localhost:8501`

**Test the API quickly (PowerShell):**

```powershell
$body = @{ question = "What vegetarian options are there on Tuesday?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

## Local Dev (VS Code / Python)

**Prereqs:** Python 3.11, Postgres with `CREATE EXTENSION vector;` (or just use Docker DB)

```bash
git clone <your-repo-url> cdai-menu-rag
cd cdai-menu-rag
cp .env.example .env    # configure as needed
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Start DB (easiest with Docker)
docker compose up -d db

# Ingest
python scripts/ingest.py

# Run API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Run UI
streamlit run ui/streamlit_app.py
```

## Switch Embeddings (Local vs OpenAI)

In `.env`:

```
# Local (default)
USE_OPENAI=0
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2   # 384 dims

# OpenAI
USE_OPENAI=1
OPENAI_API_KEY=sk-...    # rotate if you ever exposed it
EMBEDDING_MODEL=text-embedding-3-small                   # 1536 dims (or -3-large for 3072)
```

**Important:** The table dimension is created from the first run. If you change models (384 → 1536/3072), drop/recreate the table and re-ingest:

```sql
DROP INDEX IF EXISTS documents_embedding_idx;
DROP TABLE IF EXISTS documents;
DELETE FROM metadata;
```

Then:

```bash
docker compose run --rm ingest
docker compose exec db psql -U postgres -d menu_rag -c "ANALYZE documents;"
```

## What’s in here

```
api/main.py              # FastAPI: /health, /query (returns answer + citations)
app/embeddings.py        # Chooses MiniLM or OpenAI based on USE_OPENAI
app/db.py                # pgvector helpers (create table, insert, similarity search)
scripts/ingest.py        # scan data/raw/**, chunk, embed, insert (batch-safe)
scripts/chunker.py       # simple text chunker with overlap
scripts/wait_for_db.py   # container helper
ui/streamlit_app.py      # simple chat UI with citations + settings
data/raw/                # synthetic demo docs
Dockerfile
docker-compose.yml
```

## Troubleshooting

* **UI shows no answer / empty citations**
  Ensure you ingested:
  `docker compose exec db psql -U postgres -d menu_rag -c "SELECT count(*) FROM documents;"`
  If `0`, re-run ingestion. After first load or model switch, run:
  `docker compose exec db psql -U postgres -d menu_rag -c "ANALYZE documents;"`

* **“Method Not Allowed” on `/query`**
  `/query` is **POST**. Send JSON body with `question` and optional `top_k`.

* **Switched to OpenAI and got weird results**
  You likely didn’t drop the old 384-dim table. Drop + re-ingest (see above).

* **Windows PowerShell curl confusion**
  Prefer `Invoke-RestMethod` (example in TL;DR) or run `curl.exe` with `-H` and `-d` from Git Bash/Wsl.

## Evaluation (optional)

We include a `ragas` script stub (`scripts/eval_ragas.py`) to compute retrieval/answer quality.
Install extras (`requirements-eval.txt`), set `OPENAI_API_KEY`, then run the script and tailor the small QA set.

## License

MIT

---
