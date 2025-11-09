from fastapi import FastAPI
from pydantic import BaseModel
from app.embeddings import EmbeddingClient
from app.db import search_similar
from app.core.config import TOP_K

app = FastAPI(title="Cafeteria Menu RAG Assistant API")

emb = EmbeddingClient()

class QueryIn(BaseModel):
    question: str
    top_k: int | None = None

@app.get("/health")
def health():
    return {"status": "ok", "embedding_model": emb.name(), "dim": emb.get_dimension()}

@app.post("/query")
def query(q: QueryIn):
    top_k = q.top_k or TOP_K
    q_vec = emb.embed_one(q.question)
    hits = search_similar(q_vec, top_k=top_k)
    context = "\n\n".join([h["content"] for h in hits])
    citations = [
        {"source": h["source"], "page": h.get("page"), "chunk_index": h.get("chunk_index"), "score": float(h.get("score", 0.0))}
        for h in hits
    ]
    answer = (
        "Here are the most relevant menu/nutrition excerpts I found. "
        "Use these citations to verify details:\n\n" + context[:1800]
    )
    return {"answer": answer, "citations": citations}
