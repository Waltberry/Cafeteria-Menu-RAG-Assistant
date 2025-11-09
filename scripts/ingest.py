import os
from typing import List, Tuple
from app.embeddings import EmbeddingClient
from app.db import create_extension_and_table, insert_document_rows, clear_documents
from scripts.chunker import smart_chunk
from pypdf import PdfReader

RAW_DIR = os.path.join("data","raw")

def read_pdf(path: str) -> List[str]:
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return pages

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def collect_sources() -> List[Tuple[str, int, str]]:
    out = []
    for root, _, files in os.walk(RAW_DIR):
        for fn in files:
            fp = os.path.join(root, fn)
            if fn.lower().endswith(".pdf"):
                pages = read_pdf(fp)
                for i, t in enumerate(pages):
                    out.append((fp, i+1, t))
            elif fn.lower().endswith((".md",".txt",".csv")):
                t = read_text(fp)
                out.append((fp, -1, t))
    return out

def main():
    emb = EmbeddingClient()
    dim = emb.get_dimension()
    print(f"Using embedding model: {emb.name()} (dim={dim})")

    create_extension_and_table(dim)
    clear_documents()

    sources = collect_sources()
    rows = []
    for (src, page, text) in sources:
        if not text.strip():
            continue
        chunks = smart_chunk(text, max_chars=800, overlap=120)
        embs = emb.embed(chunks)
        for idx, (chunk, vec) in enumerate(zip(chunks, embs)):
            rows.append((src, page, idx, chunk, vec))

    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        insert_document_rows(batch)
        print(f"Inserted {min(i+BATCH, len(rows))}/{len(rows)}")

    print("Ingestion complete.")

if __name__ == "__main__":
    main()
