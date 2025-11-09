from typing import List, Tuple
import psycopg
from psycopg.rows import dict_row
from app.core.config import DATABASE_URL

def get_conn():
    return psycopg.connect(DATABASE_URL, autocommit=True)

def create_extension_and_table(embedding_dim: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'documents'
                );
            """)
            exists = cur.fetchone()[0]
            if not exists:
                cur.execute(f"""
                    CREATE TABLE documents (
                        id BIGSERIAL PRIMARY KEY,
                        source TEXT,
                        page INTEGER,
                        chunk_index INTEGER,
                        content TEXT,
                        embedding VECTOR({embedding_dim})
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS documents_embedding_idx
                    ON documents
                    USING ivfflat (embedding vector_cosine_ops);
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    k TEXT PRIMARY KEY,
                    v TEXT
                );
            """)

def clear_documents():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM documents;")

def insert_document_rows(rows: List[Tuple[str, int, int, str, List[float]]]):
    with get_conn() as conn:
        with conn.cursor() as cur:
            params = [
                (r[0], r[1], r[2], r[3], "[" + ",".join(f"{x:.7f}" for x in r[4]) + "]")
                for r in rows
            ]
            cur.executemany(
                "INSERT INTO documents (source, page, chunk_index, content, embedding) VALUES (%s,%s,%s,%s,%s)",
                params
            )

def search_similar(embedding: List[float], top_k: int = 5):
    with get_conn() as conn:
        conn.execute("SET enable_seqscan = off;")
        with conn.cursor(row_factory=dict_row) as cur:
            qvec = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
            cur.execute(
                """
                SELECT content, source, page, chunk_index, 1 - (embedding <=> %s::vector) AS score
                FROM documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (qvec, qvec, top_k)
            )
            return cur.fetchall()
