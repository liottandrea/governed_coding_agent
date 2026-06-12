"""Phase 2: harness and HITL unit tests."""
from __future__ import annotations

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
ROOT = Path(__file__).parent.parent


def test_build_agent_returns_compiled_graph() -> None:
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from ust_agent.harness import build_agent
    from langgraph.graph.state import CompiledStateGraph
    agent = build_agent(role="planner", data_class="internal")
    assert isinstance(agent, CompiledStateGraph)


def test_build_agent_has_hitl_node() -> None:
    """HumanInTheLoopMiddleware node must be present when interrupt_on is set."""
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from ust_agent.harness import build_agent
    agent = build_agent(role="planner", data_class="internal")
    node_names = list(agent.nodes.keys())
    hitl_nodes = [n for n in node_names if "HumanInTheLoop" in n]
    assert hitl_nodes, f"No HITL node found. Nodes: {node_names}"


def test_build_agent_has_checkpointer() -> None:
    """Agent must have a checkpointer so state survives across interrupt/resume."""
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from ust_agent.harness import build_agent
    agent = build_agent(role="planner", data_class="internal")
    assert agent.checkpointer is not None


def test_interrupt_tools_include_write_and_execute() -> None:
    """The interrupt set must cover write_file and execute."""
    os.chdir(ROOT)
    from ust_agent.harness import _INTERRUPT_TOOLS
    assert "write_file" in _INTERRUPT_TOOLS
    assert "execute" in _INTERRUPT_TOOLS


def test_run_auto_approve_completes(tmp_path: Path) -> None:
    """auto_approve=True should run end-to-end without blocking."""
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv()
    from ust_agent.harness import run as agent_run

    result = agent_run(
        "Write the text 'hello phase2' to /ust_workspace/test_p2.txt",
        role="planner",
        data_class="internal",
        auto_approve=True,
    )
    assert "messages" in result
    assert "files" in result
    assert "thread_id" in result
    # At least one write should have been approved
    assert len(result["approved"]) >= 1
    assert any(a["tool"] == "write_file" for a in result["approved"])
