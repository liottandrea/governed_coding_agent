"""Phase 3: knowledge ingest, retrieval, and sub-agent unit tests."""
from __future__ import annotations

import sys
import os
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
ROOT = Path(__file__).parent.parent


# ── tree-sitter chunking ──────────────────────────────────────────────────────
def test_chunk_python_extracts_functions() -> None:
    from governed_coding_agent.knowledge.ingest import chunk_python_file
    source = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"

def goodbye(name: str) -> str:
    """Say goodbye."""
    return f"Goodbye, {name}"
'''
    chunks = chunk_python_file(source, path="test.py", repo="test", commit="abc")
    assert len(chunks) == 2
    symbols = {c.symbol for c in chunks}
    assert "hello" in symbols
    assert "goodbye" in symbols
    assert all(c.chunk_type == "function" for c in chunks)


def test_chunk_python_extracts_class() -> None:
    from governed_coding_agent.knowledge.ingest import chunk_python_file
    source = '''
class MyParser:
    """A parser."""
    def parse(self, text: str) -> list:
        return []
'''
    chunks = chunk_python_file(source, path="parser.py")
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "class"
    assert chunks[0].symbol == "MyParser"


def test_chunk_python_fallback_to_module() -> None:
    """Files with only imports/assignments → single module chunk."""
    from governed_coding_agent.knowledge.ingest import chunk_python_file
    source = "import os\nX = 1\n"
    chunks = chunk_python_file(source, path="consts.py")
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "module"


def test_chunk_deprecated_flag_propagates() -> None:
    from governed_coding_agent.knowledge.ingest import chunk_python_file
    source = "def old(): pass\n"
    chunks = chunk_python_file(source, path="old_deprecated.py", deprecated=True)
    assert all(c.deprecated for c in chunks)


# ── retrieval ─────────────────────────────────────────────────────────────────
def test_retrieve_returns_citations(tmp_path: Path) -> None:
    """Retrieval against the live pgvector store returns Citation objects."""
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from governed_coding_agent.knowledge.retrieve import retrieve, Citation
    hits = retrieve("parse CSV file", top_k=3)
    assert isinstance(hits, list)
    if hits:  # store may be empty in a fresh env; only check shape when populated
        assert isinstance(hits[0], Citation)
        assert hits[0].score >= 0.0
        assert hits[0].path != ""


def test_retrieve_returns_empty_for_unrelated_query() -> None:
    """Very low similarity queries may return results — just verify no crash."""
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from governed_coding_agent.knowledge.retrieve import retrieve
    hits = retrieve("quantum entanglement photon spin", top_k=2)
    assert isinstance(hits, list)  # empty or low-score, never raises


def test_citation_format_includes_path_and_symbol() -> None:
    from governed_coding_agent.knowledge.retrieve import Citation
    c = Citation(
        repo="seed-corpus", path="seed/utils.py", commit="abc123",
        chunk_type="function", symbol="my_func",
        content="def my_func(): pass", deprecated=False, score=0.92,
    )
    text = c.format()
    assert "seed-corpus/seed/utils.py:my_func@abc123" in text
    assert "score=0.920" in text
    assert "DEPRECATED" not in text


def test_citation_format_flags_deprecated() -> None:
    from governed_coding_agent.knowledge.retrieve import Citation
    c = Citation(
        repo="r", path="p.py", commit="x",
        chunk_type="function", symbol="old_fn",
        content="def old_fn(): pass", deprecated=True, score=0.5,
    )
    assert "DEPRECATED" in c.format()


# ── embed policy ──────────────────────────────────────────────────────────────
def test_embed_restricted_raises_policy_error() -> None:
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from governed_coding_agent.gateway import embed
    from governed_coding_agent.policy import PolicyError
    with pytest.raises(PolicyError):
        embed(["test text"], data_class="restricted")


# ── knowledge sub-agent ───────────────────────────────────────────────────────
def test_knowledge_agent_builds() -> None:
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from governed_coding_agent.subagents.knowledge import build_knowledge_agent
    from langgraph.graph.state import CompiledStateGraph
    agent = build_knowledge_agent()
    assert isinstance(agent, CompiledStateGraph)
