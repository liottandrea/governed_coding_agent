"""Phase 5: routing cascade and Testing sub-agent unit tests."""
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


# ── Routing cascade: resolve_fallback_group ───────────────────────────────────

def test_resolve_fallback_group_testing_role() -> None:
    _load_env()
    from governed_coding_agent.gateway import resolve_fallback_group

    fb = resolve_fallback_group("testing")
    assert fb is not None
    assert isinstance(fb, str)


def test_resolve_fallback_group_differs_from_primary() -> None:
    _load_env()
    from governed_coding_agent.gateway import resolve_fallback_group, resolve_group

    primary = resolve_group("testing")
    fb = resolve_fallback_group("testing")
    assert fb != primary


def test_resolve_fallback_group_returns_none_for_no_fallback() -> None:
    _load_env()
    from governed_coding_agent.gateway import resolve_fallback_group

    # codegen has no fallback_group in routing-rules.yaml
    assert resolve_fallback_group("codegen") is None


def test_resolve_model_testing_returns_cascading_model() -> None:
    _load_env()
    from governed_coding_agent.gateway import resolve_model, CascadingChatModel

    model = resolve_model("testing", "internal")
    assert isinstance(model, CascadingChatModel)


def test_resolve_model_codegen_returns_plain_chat_litellm() -> None:
    """Roles without a fallback_group must not be wrapped."""
    _load_env()
    from governed_coding_agent.gateway import resolve_model, CascadingChatModel
    from langchain_litellm import ChatLiteLLM

    model = resolve_model("codegen", "internal")
    assert isinstance(model, ChatLiteLLM)
    assert not isinstance(model, CascadingChatModel)


def test_restricted_data_class_skips_fallback_if_forbidden() -> None:
    """If the fallback group is not allowed for data_class, fall back to primary only."""
    _load_env()
    from governed_coding_agent.gateway import resolve_model
    from langchain_litellm import ChatLiteLLM
    from langchain_core.runnables import RunnableWithFallbacks

    # 'restricted' only allows local groups; 'mid' (testing fallback) is Bedrock.
    # So resolve_model should return a plain ChatLiteLLM (primary=local) or raise.
    # The testing role's primary is 'cheap' which is also Bedrock — both primary
    # and fallback are forbidden for restricted → PolicyError.
    from governed_coding_agent.policy import PolicyError
    with pytest.raises(PolicyError):
        resolve_model("testing", "restricted")


def test_all_roles_still_resolve_after_cascade_change() -> None:
    """Cascade addition must not break roles that have no fallback."""
    _load_env()
    from governed_coding_agent.gateway import resolve_model, CascadingChatModel
    from langchain_litellm import ChatLiteLLM

    for role in ("planner", "codegen", "knowledge_retrieval", "embedding", "summary"):
        model = resolve_model(role, "internal")
        assert isinstance(model, (ChatLiteLLM, CascadingChatModel)), (
            f"resolve_model({role!r}) returned unexpected type {type(model)}"
        )


# ── Testing sub-agent structure ───────────────────────────────────────────────

def test_build_testing_agent_returns_compiled_graph() -> None:
    _load_env()
    from governed_coding_agent.subagents.testing import build_testing_agent
    from langgraph.graph.state import CompiledStateGraph

    agent = build_testing_agent(data_class="internal")
    assert isinstance(agent, CompiledStateGraph)


def test_build_testing_agent_has_hitl_node() -> None:
    _load_env()
    from governed_coding_agent.subagents.testing import build_testing_agent

    agent = build_testing_agent(data_class="internal")
    node_names = list(agent.nodes.keys())
    hitl_nodes = [n for n in node_names if "HumanInTheLoop" in n]
    assert hitl_nodes, f"No HITL node found. Nodes: {node_names}"


def test_build_testing_agent_has_checkpointer() -> None:
    _load_env()
    from governed_coding_agent.subagents.testing import build_testing_agent

    agent = build_testing_agent(data_class="internal")
    assert agent.checkpointer is not None


def test_testing_skill_md_exists() -> None:
    skill_path = ROOT / "src" / "governed_coding_agent" / "skills" / "testing" / "SKILL.md"
    assert skill_path.exists()
    content = skill_path.read_text()
    assert "parametrize" in content
    assert "pytest" in content


def test_testing_system_prompt_contains_skill_content() -> None:
    _load_env()
    from governed_coding_agent.subagents.testing import _build_system_prompt

    prompt = _build_system_prompt()
    assert "retrieve_knowledge_tool" in prompt
    assert "pytest" in prompt.lower()


def test_testing_system_prompt_references_execute_step() -> None:
    """Prompt must instruct the agent to actually run the tests."""
    _load_env()
    from governed_coding_agent.subagents.testing import _build_system_prompt

    prompt = _build_system_prompt()
    assert "execute" in prompt.lower()
    assert "pytest" in prompt.lower()


# ── run() output contract ─────────────────────────────────────────────────────

def test_run_returns_expected_keys() -> None:
    _load_env()
    from langchain_core.messages import AIMessage
    from governed_coding_agent.subagents.testing import build_testing_agent

    agent = build_testing_agent(data_class="internal")
    fake_msg = AIMessage(content="Tests passed.")
    fake_state = MagicMock()
    fake_state.values = {"messages": [fake_msg], "files": {}}

    with patch.object(agent, "stream", return_value=iter([{"agent": {"messages": [fake_msg]}}])):
        with patch.object(agent, "get_state", return_value=fake_state):
            from governed_coding_agent.subagents.testing import run
            result = run("dummy task", data_class="internal", auto_approve=True)

    assert "messages" in result
    assert "files" in result
    assert "thread_id" in result
    assert "approved" in result
