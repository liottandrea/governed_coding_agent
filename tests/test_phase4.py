"""Phase 4: Code Authoring sub-agent unit tests."""
from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
ROOT = Path(__file__).parent.parent


def _load_env() -> None:
    os.chdir(ROOT)
    from dotenv import load_dotenv
    load_dotenv()


# ── Build / structure ────────────────────────────────────────────────────────

def test_build_code_authoring_agent_returns_compiled_graph() -> None:
    _load_env()
    from ust_agent.subagents.code_authoring import build_code_authoring_agent
    from langgraph.graph.state import CompiledStateGraph

    agent = build_code_authoring_agent(data_class="internal")
    assert isinstance(agent, CompiledStateGraph)


def test_build_code_authoring_agent_has_hitl_node() -> None:
    _load_env()
    from ust_agent.subagents.code_authoring import build_code_authoring_agent

    agent = build_code_authoring_agent(data_class="internal")
    node_names = list(agent.nodes.keys())
    hitl_nodes = [n for n in node_names if "HumanInTheLoop" in n]
    assert hitl_nodes, f"No HITL node found. Nodes: {node_names}"


def test_build_code_authoring_agent_has_checkpointer() -> None:
    _load_env()
    from ust_agent.subagents.code_authoring import build_code_authoring_agent

    agent = build_code_authoring_agent(data_class="internal")
    assert agent.checkpointer is not None


def test_code_authoring_interrupt_on_covers_write_and_execute() -> None:
    """interrupt_on must include write_file and execute."""
    _load_env()
    # The interrupt set is configured inside build_code_authoring_agent;
    # we verify it via the compiled graph having HITL nodes (structural check)
    # and by inspecting the source directly.
    from ust_agent.subagents import code_authoring

    src = Path(code_authoring.__file__).read_text()
    assert '"write_file"' in src or "'write_file'" in src
    assert '"execute"' in src or "'execute'" in src


# ── System prompt / SKILL.md ────────────────────────────────────────────────

def test_system_prompt_includes_skill_md() -> None:
    _load_env()
    from ust_agent.subagents.code_authoring import _build_system_prompt

    prompt = _build_system_prompt()
    assert "retrieve_knowledge" in prompt
    assert "UST" in prompt


def test_system_prompt_includes_style_guide() -> None:
    _load_env()
    from ust_agent.subagents.code_authoring import _build_system_prompt

    prompt = _build_system_prompt()
    # SKILL.md content must be present
    assert "from __future__ import annotations" in prompt
    assert "Google-style" in prompt or "Google" in prompt


def test_skill_md_exists() -> None:
    skill_path = ROOT / "src" / "ust_agent" / "skills" / "code-authoring" / "SKILL.md"
    assert skill_path.exists(), f"SKILL.md missing at {skill_path}"
    content = skill_path.read_text()
    assert len(content) > 200, "SKILL.md is suspiciously short"


# ── retrieve_knowledge_tool ──────────────────────────────────────────────────

def test_retrieve_knowledge_tool_is_a_tool() -> None:
    _load_env()
    from ust_agent.knowledge.retrieve import retrieve_knowledge_tool
    from langchain_core.tools import BaseTool

    assert isinstance(retrieve_knowledge_tool, BaseTool)


def test_retrieve_knowledge_tool_name() -> None:
    _load_env()
    from ust_agent.knowledge.retrieve import retrieve_knowledge_tool

    assert retrieve_knowledge_tool.name == "retrieve_knowledge_tool"


def test_retrieve_knowledge_tool_invoke_live() -> None:
    """Live call: embed + pgvector search. Requires running postgres + data."""
    _load_env()
    from ust_agent.knowledge.retrieve import retrieve_knowledge_tool

    result = retrieve_knowledge_tool.invoke({"query": "validate email address", "top_k": 2})
    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain snippet header or "No relevant" message
    assert "snippet" in result.lower() or "no relevant" in result.lower()


def test_retrieve_knowledge_tool_importable_from_code_authoring() -> None:
    """The import used in code_authoring.py must resolve without error."""
    _load_env()
    from ust_agent.knowledge.retrieve import retrieve_knowledge_tool  # noqa: F401


# ── run() function (mocked LLM) ──────────────────────────────────────────────

def test_run_returns_expected_keys() -> None:
    """run() must always return the documented dict keys."""
    _load_env()

    from langchain_core.messages import AIMessage
    from ust_agent.subagents.code_authoring import build_code_authoring_agent

    agent = build_code_authoring_agent(data_class="internal")

    # Patch agent.stream to return a completed run with no interrupts
    fake_msg = AIMessage(content="Done.")
    fake_state = MagicMock()
    fake_state.values = {"messages": [fake_msg], "files": {}}

    with patch.object(agent, "stream", return_value=iter([{"agent": {"messages": [fake_msg]}}])):
        with patch.object(agent, "get_state", return_value=fake_state):
            from ust_agent.subagents.code_authoring import run
            result = run("dummy task", data_class="internal", auto_approve=True)

    assert "messages" in result
    assert "files" in result
    assert "thread_id" in result
    assert "approved" in result


# ── Policy enforcement ───────────────────────────────────────────────────────

def test_codegen_role_maps_to_frontier_model() -> None:
    """codegen role must resolve to the frontier model group."""
    _load_env()
    from ust_agent.gateway import resolve_model

    # Just check it returns a ChatLiteLLM instance — the group resolution is
    # tested in gateway tests; here we confirm the role is accepted.
    from langchain_litellm import ChatLiteLLM
    model = resolve_model("codegen", "internal")
    assert isinstance(model, ChatLiteLLM)


def test_restricted_data_class_raises_for_frontier() -> None:
    _load_env()
    from ust_agent.policy import PolicyError, check

    with pytest.raises(PolicyError):
        check("restricted", "frontier")
