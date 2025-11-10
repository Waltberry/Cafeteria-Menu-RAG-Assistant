# app/db.py
from typing import List, Tuple
import psycopg
from psycopg.rows import dict_row
from app.core.config import DATABASE_URL


def _normalize_dsn(dsn: str) -> str:
    """
    Accept SQLAlchemy-style DSN (postgresql+psycopg://) and normalize to psycopg's
    expected scheme (postgresql://).
    """
    if dsn.startswith("postgresql+psycopg://"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


def get_conn():
    """Return an autocommit connection."""
    return psycopg.connect(_normalize_dsn(DATABASE_URL), autocommit=True)


def _vec_literal(v: List[float]) -> str:
    """Format a Python list[float] as a pgvector literal, e.g. [0.1,0.2,...]."""
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def create_extension_and_table(embedding_dim: int):
    """
    Ensure pgvector is available and the 'documents' table exists with an IVFFLAT index.
    """
    with get_conn() as conn, conn.cursor() as cur:
        # pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # documents table (if not exists)
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'documents'
            );
            """
        )
        exists = cur.fetchone()[0]
        if not exists:
            cur.execute(
                f"""
                CREATE TABLE documents (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT,
                    page INTEGER,
                    chunk_index INTEGER,
                    content TEXT,
                    embedding VECTOR({embedding_dim})
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS documents_embedding_idx
                ON documents
                USING ivfflat (embedding vector_cosine_ops);
                """
            )

        # simple key/value table (optional)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                k TEXT PRIMARY KEY,
                v TEXT
            );
            """
        )


def clear_documents():
    """Delete all rows from documents."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM documents;")


def insert_document_rows(rows: List[Tuple[str, int, int, str, List[float]]]):
    """
    Bulk insert rows: (source, page, chunk_index, content, embedding_list).
    Embedding is passed as a formatted pgvector literal string.
    """
    if not rows:
        return
    with get_conn() as conn, conn.cursor() as cur:
        params = [
            (r[0], r[1], r[2], r[3], _vec_literal(r[4]))  # type: ignore[index]
            for r in rows
        ]
        cur.executemany(
            "INSERT INTO documents (source, page, chunk_index, content, embedding) "
            "VALUES (%s,%s,%s,%s,%s)",
            params,
        )


def analyze_documents():
    """Run ANALYZE to help the planner/IVFFLAT after ingestion."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("ANALYZE documents;")


def search_similar(embedding: List[float], top_k: int = 5):
    """
    Cosine similarity search. We **do not** disable seqscan—on small tables,
    Postgres will naturally choose the best plan and return results reliably.
    """
    qvec = _vec_literal(embedding)
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT content, source, page, chunk_index,
                   1 - (embedding <=> %s::vector) AS score
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (qvec, qvec, top_k),
        )
        return cur.fetchall()
