"""Create (or migrate) the pgvector schema for the knowledge store.

Run: uv run python scripts/init_db.py

Safe to re-run — all statements use CREATE IF NOT EXISTS / DO NOTHING.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "src")
from dotenv import load_dotenv
load_dotenv()

import psycopg

DSN = (
    f"host={os.environ.get('POSTGRES_HOST','localhost')} "
    f"port={os.environ.get('POSTGRES_PORT','5432')} "
    f"dbname={os.environ.get('POSTGRES_DB','governed_coding_agent')} "
    f"user={os.environ.get('POSTGRES_USER','governed_coding_agent')} "
    f"password={os.environ.get('POSTGRES_PASSWORD','changeme')}"
)

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS code_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo        TEXT        NOT NULL,
    path        TEXT        NOT NULL,
    commit      TEXT        NOT NULL DEFAULT 'seed',
    chunk_type  TEXT        NOT NULL,      -- 'function' | 'class' | 'module'
    symbol      TEXT,                      -- qualified name, e.g. MyClass.method
    content     TEXT        NOT NULL,
    embedding   vector(1024),
    deprecated  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo, path, symbol, commit)
);

CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx
    ON code_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
"""


def main() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(DDL)
    print("✓ pgvector schema ready (code_chunks table + ivfflat index)")


if __name__ == "__main__":
    main()
