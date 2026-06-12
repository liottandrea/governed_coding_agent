"""Knowledge ingest pipeline.

Chunks Python source files on function/class boundaries using tree-sitter,
embeds each chunk through the gateway, and loads it into pgvector.

Usage:
    from ust_agent.knowledge.ingest import ingest_seed
    ingest_seed()          # loads everything under seed/
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import tree_sitter_python as tspython
from pgvector.psycopg import register_vector
from tree_sitter import Language, Parser

from ust_agent import gateway

logger = logging.getLogger(__name__)

# ── tree-sitter setup ─────────────────────────────────────────────────────────
_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_CHUNK_TYPES = {"function_definition", "class_definition", "decorated_definition"}

# ── database DSN ─────────────────────────────────────────────────────────────
def _dsn() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST','localhost')} "
        f"port={os.environ.get('POSTGRES_PORT','5432')} "
        f"dbname={os.environ.get('POSTGRES_DB','ust_agent')} "
        f"user={os.environ.get('POSTGRES_USER','ust_agent')} "
        f"password={os.environ.get('POSTGRES_PASSWORD','changeme')}"
    )


# ── data types ────────────────────────────────────────────────────────────────
@dataclass
class Chunk:
    repo: str
    path: str
    commit: str
    chunk_type: str        # 'function' | 'class' | 'module'
    symbol: str | None     # qualified name (e.g. "MyClass.method")
    content: str
    deprecated: bool = False


# ── tree-sitter chunking ──────────────────────────────────────────────────────
def _extract_symbol(node: Any, source: bytes) -> str | None:
    """Return the name of a function or class definition node."""
    for child in node.children:
        if child.type == "identifier":
            return source[child.start_byte:child.end_byte].decode("utf-8")
    return None


def _unwrap_decorated(node: Any) -> Any:
    """Return the inner function_definition or class_definition from a decorated node."""
    for child in node.children:
        if child.type in ("function_definition", "class_definition"):
            return child
    return node


def chunk_python_file(
    source: str,
    path: str,
    repo: str = "seed",
    commit: str = "seed",
    deprecated: bool = False,
) -> list[Chunk]:
    """Parse Python source and return one Chunk per top-level function/class.

    Falls back to a single module-level chunk if no definitions are found.
    """
    source_bytes = source.encode("utf-8")
    tree = _PARSER.parse(source_bytes)
    root = tree.root_node

    chunks: list[Chunk] = []

    for node in root.children:
        if node.type not in _CHUNK_TYPES:
            continue

        inner = _unwrap_decorated(node) if node.type == "decorated_definition" else node
        chunk_type = "function" if inner.type == "function_definition" else "class"
        symbol = _extract_symbol(inner, source_bytes)
        content = source_bytes[node.start_byte:node.end_byte].decode("utf-8")

        chunks.append(Chunk(
            repo=repo,
            path=path,
            commit=commit,
            chunk_type=chunk_type,
            symbol=symbol,
            content=content,
            deprecated=deprecated,
        ))

    if not chunks:
        # Whole file as a single module chunk
        chunks.append(Chunk(
            repo=repo,
            path=path,
            commit=commit,
            chunk_type="module",
            symbol=None,
            content=source,
            deprecated=deprecated,
        ))

    logger.debug("Chunked %s → %d chunk(s)", path, len(chunks))
    return chunks


# ── embedding + DB load ───────────────────────────────────────────────────────
_INSERT_SQL = """
INSERT INTO ust_chunks (repo, path, commit, chunk_type, symbol, content, embedding, deprecated)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (repo, path, symbol, commit) DO UPDATE
    SET content    = EXCLUDED.content,
        embedding  = EXCLUDED.embedding,
        deprecated = EXCLUDED.deprecated;
"""

# Titan Embed Text v2 batch limit is 1 text per call when using LiteLLM,
# so we batch in groups to avoid oversized requests.
_EMBED_BATCH = 25


def load_chunks(
    chunks: list[Chunk],
    data_class: str = "internal",
) -> int:
    """Embed chunks and upsert them into pgvector. Returns the count loaded."""
    if not chunks:
        return 0

    # Embed in batches
    embeddings: list[list[float]] = []
    for i in range(0, len(chunks), _EMBED_BATCH):
        batch = chunks[i : i + _EMBED_BATCH]
        texts = [c.content for c in batch]
        vecs = gateway.embed(texts, data_class=data_class)
        embeddings.extend(vecs)

    with psycopg.connect(_dsn()) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for chunk, vec in zip(chunks, embeddings):
                cur.execute(_INSERT_SQL, (
                    chunk.repo,
                    chunk.path,
                    chunk.commit,
                    chunk.chunk_type,
                    chunk.symbol or chunk.path,   # fallback for module chunks
                    chunk.content,
                    vec,
                    chunk.deprecated,
                ))
        conn.commit()

    return len(chunks)


# ── seed ingest entry point ───────────────────────────────────────────────────
def ingest_seed(
    seed_dir: Path | None = None,
    repo: str = "ust-seed",
    commit: str = "seed",
    data_class: str = "internal",
) -> int:
    """Ingest all .py files under seed_dir into pgvector.

    Files named with a ``_deprecated`` suffix in their stem are marked
    deprecated. Returns total chunks loaded.
    """
    root = seed_dir or (Path(__file__).parent.parent.parent.parent / "seed")
    total = 0

    for py_file in sorted(root.glob("*.py")):
        deprecated = "_deprecated" in py_file.stem
        source = py_file.read_text(encoding="utf-8")
        chunks = chunk_python_file(
            source,
            path=str(py_file.relative_to(root.parent)),
            repo=repo,
            commit=commit,
            deprecated=deprecated,
        )
        loaded = load_chunks(chunks, data_class=data_class)
        total += loaded
        logger.info("Ingested %s → %d chunk(s)", py_file.name, loaded)

    return total
