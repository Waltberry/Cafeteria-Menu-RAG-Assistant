# Cafeteria Menu RAG Assistant

**Repo name:** `cdai-menu-rag`  
Ask questions about cafeteria menus, allergens, and nutrition using Retrieval-Augmented Generation (RAG).  
This project ingests sample menu & nutrition documents, chunks + embeds them, and stores vectors in **Postgres + pgvector**.  
We provide a **FastAPI** backend for retrieval and a **Streamlit** chat UI. Optional LLM generation and **ragas** evaluation are included.

> **Data** in `data/raw` is **synthetic** and for demo only. Drop in your own PDFs/Markdown and re-run ingestion.

---

## Architecture

```
+--------------------+        +-------------------+
|  Raw docs (PDF/MD) | ---->  |  Ingest & Chunk   |  (Python)
+--------------------+        +-------------------+
                                      |
                                      v
                            +--------------------+
                            |  Embeddings        |  (Sentence-Transformers
                            |  (MiniLM or OpenAI)|   or OpenAI embeddings)
                            +--------------------+
                                      |
                                      v
                          +------------------------+
                          | Postgres + pgvector    |
                          |  documents( content,   |
                          |  source, page, chunk,  |
                          |  embedding VECTOR(n) ) |
                          +------------------------+
                                      ^
                                      |
                          +------------------------+
                          |  FastAPI /query        |
                          |  vector search +       |
                          |  (optional LLM gen)    |
                          +------------------------+
                                      |
                                      v
                          +------------------------+
                          | Streamlit Chat UI      |
                          | citations + snippets   |
                          +------------------------+
```

---

## Quickstart (VS Code - Local Python)

**Prereqs**
- Python 3.11
- Postgres with `pgvector` extension (or use Docker below)
- (Optional) OpenAI API key for LLM/embeddings

**1) Clone & env**
```bash
git clone <your-repo-url> cdai-menu-rag
cd cdai-menu-rag
cp .env.example .env   # edit if needed
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2) Start Postgres with pgvector**
- Easiest: `docker compose up -d db`  
- Or use your local Postgres and ensure `CREATE EXTENSION vector;`

**3) Ingest data**
```bash
python scripts/ingest.py
```
This scans `data/raw/**` for `.pdf`, `.md`, `.txt`, chunks & embeds, and inserts into Postgres.

**4) Run API**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Health check at `http://localhost:8000/health`

**5) Run UI**
```bash
streamlit run ui/streamlit_app.py
```
Open the UI at `http://localhost:8501` and ask questions like:
- “What are gluten-free options on Tuesday?”  
- “Calories in the quinoa bowl?”  
- “Which items contain dairy?”

---

## Docker (API + UI + DB)

```bash
cp .env.example .env
docker compose up --build -d db
docker compose run --rm ingest         # one-time to ingest documents
docker compose up --build api ui       # starts API (8000) and UI (8501)
```

- API: `http://localhost:8000`
- UI: `http://localhost:8501`

Re-run `docker compose run --rm ingest` after adding new docs to `data/raw`.

---

## Config

`.env` (see `.env.example`):
- `DATABASE_URL` (default: `postgresql+psycopg://postgres:postgres@db:5432/menu_rag` in Docker)
- `EMBEDDING_MODEL` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `USE_OPENAI=1` and `OPENAI_API_KEY=...` to switch to OpenAI embeddings (`text-embedding-3-small`, dim=1536)
- `TOP_K` retrieval count
- `API_URL` for the Streamlit UI

**Note:** Table dimension is created from the first embedding run. If you change models (dim), clear the table:
```sql
TRUNCATE TABLE documents;
-- or drop and re-run ingestion if dims differ
DROP TABLE documents;
```
then re-run `scripts/ingest.py`.

---

## Evaluation (optional, requires LLM)

We use **ragas** for retrieval/answer quality. Install extras:
```bash
pip install -r requirements-eval.txt
export OPENAI_API_KEY=...
```

Then run:
```bash
python scripts/eval_ragas.py
```

- You can edit `scripts/eval_ragas.py` to define a small QA dataset (few-shot) based on your own menus.
- Metrics (typical): `context_precision`, `context_recall`, `faithfulness`, `answer_relevancy`

---

## Project Structure

```
cdai-menu-rag/
├── api/
│   └── main.py            # FastAPI app (/health, /query)
├── app/
│   ├── core/config.py     # env/config
│   ├── db.py              # Postgres + pgvector helpers
│   └── embeddings.py      # Embedding client (MiniLM or OpenAI)
├── scripts/
│   ├── chunker.py         # simple chunker (sections + overlap)
│   ├── ingest.py          # ingestion pipeline
│   ├── wait_for_db.py     # docker helper
│   └── eval_ragas.py      # OPTIONAL: ragas evaluation
├── ui/
│   └── streamlit_app.py   # chat UI (calls API)
├── data/
│   ├── raw/               # synthetic sample docs (add yours here)
│   └── processed/         # reserved for future use
├── .env.example
├── requirements.txt
├── requirements-eval.txt
├── Dockerfile
├── docker-compose.yml
├── LICENSE
└── README.md
```

---

## Notes & Tips

- The API returns citations (file path, page, chunk) so the UI can show “grounded” sources.
- Retrieval uses cosine distance with `ivfflat` index. For larger corpora, consider HNSW or tuning `lists`.
- To switch to OpenAI for embeddings and generation, set `USE_OPENAI=1` and provide `OPENAI_API_KEY`. The UI demonstrates an extractive fallback if no LLM is available.

---

## Roadmap

- Add LLM answer synthesis with grounding checks (TruLens/RAGAS judge).
- Add ingestion CLI to tag sources (location, date range) and filter at query time.
- Support S3/GCS ingestion and scheduled re-index.
- Add unit tests and basic e2e smoke test.
