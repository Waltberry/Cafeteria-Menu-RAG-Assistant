# scripts/ingest.py
import os
from typing import List, Tuple
from app.embeddings import EmbeddingClient
from app.db import create_extension_and_table, insert_document_rows, clear_documents
from scripts.chunker import smart_chunk
from pypdf import PdfReader

RAW_DIR = os.path.join("data", "raw")

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
                for i, t in enumerate(read_pdf(fp)):
                    out.append((fp, i + 1, t))
            elif fn.lower().endswith((".md", ".txt", ".csv")):
                out.append((fp, -1, read_text(fp)))
    return out

def main():
    emb = EmbeddingClient()
    dim = emb.get_dimension()
    print(f"Using embedding model: {emb.name()} (dim={dim})", flush=True)

    create_extension_and_table(dim)
    clear_documents()

    sources = collect_sources()
    print(f"Found {len(sources)} source items under {RAW_DIR}", flush=True)

    rows = []
    for (src, page, text) in sources:
        rel = os.path.relpath(src, start="data")
        try:
            if not text or not text.strip():
                print(f" !! Skipping empty: {rel}{(f':p{page}' if page != -1 else '')}", flush=True)
                continue
            chunks = smart_chunk(text, max_chars=800, overlap=120)
            if not chunks:
                print(f" !! No chunks: {rel}{(f':p{page}' if page != -1 else '')}", flush=True)
                continue
            embs = emb.embed(chunks)
            for idx, (chunk, vec) in enumerate(zip(chunks, embs)):
                rows.append((src, page, idx, chunk, vec))
            print(f" -> {rel}{(f':p{page}' if page != -1 else '')} | chunks: {len(chunks)}", flush=True)
        except Exception as e:
            # Never let one file crash the whole run
            print(f" !! Error on {rel}{(f':p{page}' if page != -1 else '')}: {type(e).__name__}: {e}", flush=True)

    print(f"Total chunks to insert: {len(rows)}", flush=True)

    if not rows:
        print("Nothing to insert. Exiting.", flush=True)
        return

    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        insert_document_rows(batch)
        print(f"Inserted {min(i+BATCH, len(rows))}/{len(rows)}", flush=True)

    print("Ingestion complete.", flush=True)

if __name__ == "__main__":
    main()
