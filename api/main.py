# api/main.py
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from app.embeddings import EmbeddingClient
from app.db import search_similar
from app.core.config import TOP_K

log = logging.getLogger("uvicorn")

app = FastAPI(title="Cafeteria Menu RAG Assistant API")
emb = EmbeddingClient()

class QueryIn(BaseModel):
    question: str
    top_k: int | None = None

@app.get("/health")
def health():
    return {
        "status": "ok",
        "embedding_model": emb.name(),
        "dim": emb.get_dimension(),
        "top_k_default": TOP_K,
    }

@app.post("/query")
def query(q: QueryIn):
    top_k = q.top_k or TOP_K
    question = (q.question or "").strip()
    if not question:
        return {"answer": "Please enter a question.", "citations": [], "debug": {"hits": 0}}

    q_vec = emb.embed_one(question)
    hits = search_similar(q_vec, top_k=top_k)
    log.info(f"[query] q='{question[:80]}' top_k={top_k} hits={len(hits)}")

    citations = [
        {
            "source": h["source"],
            "page": h.get("page"),
            "chunk_index": h.get("chunk_index"),
            "score": float(h.get("score", 0.0)),
        }
        for h in hits
    ]

    if not hits:
        return {
            "answer": "I couldn’t find relevant excerpts. Try asking about a day/dish by name.",
            "citations": [],
            "debug": {"hits": 0},
        }

    context = "\n\n".join([h["content"] for h in hits])
    answer = (
        "Here are the most relevant menu/nutrition excerpts I found. "
        "Use these citations to verify details:\n\n" + context[:1800]
    )
    return {"answer": answer, "citations": citations, "debug": {"hits": len(hits)}}
