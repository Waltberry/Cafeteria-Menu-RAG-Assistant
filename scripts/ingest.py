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

    # Prepare DB fresh each run
    create_extension_and_table(dim)
    clear_documents()

    sources = collect_sources()
    print(f"Found {len(sources)} source items under {RAW_DIR}", flush=True)

    total_rows = 0
    for (src, page, text) in sources:
        rel = os.path.relpath(src, start="data")
        label = f"{rel}{(f':p{page}' if page != -1 else '')}"
        try:
            if not text or not text.strip():
                print(f" !! Skipping empty: {label}", flush=True)
                continue

            # small-ish chunks for reliability
            chunks = smart_chunk(text, max_chars=600, overlap=80)
            if not chunks:
                print(f" !! No chunks: {label}", flush=True)
                continue

            # embed one-by-one to avoid spikes
            rows = []
            for idx, chunk in enumerate(chunks):
                vec = emb.embed_one(chunk)
                rows.append((src, page, idx, chunk, vec))

            # insert just this file's rows
            insert_document_rows(rows)
            total_rows += len(rows)
            print(f" -> Inserted {len(rows)} rows for {label}", flush=True)

        except Exception as e:
            # Don't let one bad file kill the whole run
            print(f" !! Error on {label}: {type(e).__name__}: {e}", flush=True)

    print(f"Done. Total rows inserted: {total_rows}", flush=True)


if __name__ == "__main__":
    main()
