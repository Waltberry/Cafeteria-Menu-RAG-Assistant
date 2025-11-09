import re
from typing import List

def split_into_sections(text: str) -> List[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]

def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= n:
            break
    return chunks

def smart_chunk(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    sections = split_into_sections(text)
    out = []
    for sec in sections:
        if len(sec) <= max_chars:
            out.append(sec)
        else:
            out.extend(chunk_text(sec, max_chars=max_chars, overlap=overlap))
    return out
