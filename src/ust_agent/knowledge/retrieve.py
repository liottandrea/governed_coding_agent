"""Knowledge retrieval from pgvector.

Embeds a query through the gateway and returns the top-k most similar
chunks from ust_chunks, assembled into Citation objects.

Usage:
    from ust_agent.knowledge.retrieve import retrieve
    hits = retrieve("parse CSV file with type coercion", top_k=3)
    for c in hits:
        print(c.format())
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

from ust_agent import gateway

logger = logging.getLogger(__name__)


def _dsn() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST','localhost')} "
        f"port={os.environ.get('POSTGRES_PORT','5432')} "
        f"dbname={os.environ.get('POSTGRES_DB','ust_agent')} "
        f"user={os.environ.get('POSTGRES_USER','ust_agent')} "
        f"password={os.environ.get('POSTGRES_PASSWORD','changeme')}"
    )


@dataclass
class Citation:
    """A retrieved code chunk with its provenance metadata."""
    repo: str
    path: str
    commit: str
    chunk_type: str
    symbol: str | None
    content: str
    deprecated: bool
    score: float           # cosine similarity (higher = more similar)

    def format(self) -> str:
        """Human-readable citation block for use in prompts and output."""
        dep_flag = " ⚠ DEPRECATED" if self.deprecated else ""
        ref = f"{self.repo}/{self.path}"
        if self.symbol and self.symbol != self.path:
            ref += f":{self.symbol}"
        ref += f"@{self.commit}{dep_flag}"
        return f"[{ref}] (score={self.score:.3f})\n```python\n{self.content}\n```"


_SEARCH_SQL = """
SELECT
    repo, path, commit, chunk_type, symbol, content, deprecated,
    1 - (embedding <=> %s::vector) AS score
FROM ust_chunks
ORDER BY embedding <=> %s::vector
LIMIT %s;
"""


def retrieve(
    query: str,
    top_k: int = 5,
    data_class: str = "internal",
    min_score: float = 0.0,
) -> list[Citation]:
    """Embed query and return top_k most similar chunks as Citations.

    Args:
        query: Natural-language description of what to find.
        top_k: Maximum number of results.
        data_class: Controls which embedding model is used (policy-gated).
        min_score: Minimum cosine similarity to include (0 = no filter).

    Returns:
        List of Citation objects sorted by descending similarity score.
        Returns an empty list if the knowledge store has no content yet.
    """
    vecs = gateway.embed([query], data_class=data_class)
    query_vec = vecs[0]

    with psycopg.connect(_dsn()) as conn:
        register_vector(conn)
        rows = conn.execute(_SEARCH_SQL, (query_vec, query_vec, top_k)).fetchall()

    citations = [
        Citation(
            repo=row[0],
            path=row[1],
            commit=row[2],
            chunk_type=row[3],
            symbol=row[4],
            content=row[5],
            deprecated=row[6],
            score=float(row[7]),
        )
        for row in rows
        if float(row[7]) >= min_score
    ]

    logger.debug("retrieve('%s') → %d hit(s)", query[:60], len(citations))
    return citations


def format_for_prompt(citations: list[Citation]) -> str:
    """Format citations into a context block suitable for injection into a prompt."""
    if not citations:
        return "No relevant UST prior work found for this query."
    parts = [f"Found {len(citations)} relevant UST snippet(s):\n"]
    for i, c in enumerate(citations, 1):
        parts.append(f"## Snippet {i}\n{c.format()}\n")
    return "\n".join(parts)
