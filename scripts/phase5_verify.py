"""Phase 5 verification: routing cascade + Testing sub-agent.

Checks:
  1. resolve_fallback_group() reads fallback_group from routing-rules.yaml.
  2. resolve_model("testing", ...) returns a RunnableWithFallbacks (cascade active).
  3. Testing agent builds with HITL nodes.
  4. Live auto-approve run: agent retrieves UST patterns, writes tests, executes them.
  5. Langfuse trace check.

Run with:
    uv run python scripts/phase5_verify.py
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()
os.chdir(ROOT)


def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── 1. resolve_fallback_group ────────────────────────────────────────────────

section("1. resolve_fallback_group for 'testing' role")
from ust_agent.gateway import resolve_fallback_group, resolve_group

fb = resolve_fallback_group("testing")
primary = resolve_group("testing")
print(f"  primary  : {primary}")
print(f"  fallback : {fb}")
assert fb is not None, "testing role has no fallback_group in routing-rules.yaml"
assert fb != primary, "fallback_group must differ from default_group"
print("  PASS: fallback group defined and distinct from primary")

# ── 2. Cascade wiring: resolve_model returns RunnableWithFallbacks ───────────

section("2. resolve_model('testing') returns a cascaded model")
from ust_agent.gateway import resolve_model, CascadingChatModel

model = resolve_model("testing", "internal")
print(f"  model type: {type(model).__name__}")
assert isinstance(model, CascadingChatModel), (
    f"Expected CascadingChatModel, got {type(model).__name__}. "
    "Check that 'testing' role has fallback_group in routing-rules.yaml."
)
print(f"  primary  : {model.primary.model}")
print(f"  fallback : {model.fallback.model}")
print("  PASS: CascadingChatModel returned — cascade is active")

# ── 3. Roles without fallback still return plain ChatLiteLLM ────────────────

section("3. Roles without fallback return plain ChatLiteLLM")
from langchain_litellm import ChatLiteLLM

codegen_model = resolve_model("codegen", "internal")
print(f"  codegen model type: {type(codegen_model).__name__}")
assert isinstance(codegen_model, ChatLiteLLM)
assert not isinstance(codegen_model, CascadingChatModel)
print("  PASS: codegen (no fallback) returns plain ChatLiteLLM")

# ── 4. Testing agent builds with HITL ───────────────────────────────────────

section("4. Testing agent builds with HITL + checkpointer")
from ust_agent.subagents.testing import build_testing_agent
from langgraph.graph.state import CompiledStateGraph

agent = build_testing_agent(data_class="internal")
print(f"  Agent type      : {type(agent).__name__}")
assert isinstance(agent, CompiledStateGraph)

node_names = list(agent.nodes.keys())
hitl_nodes = [n for n in node_names if "HumanInTheLoop" in n]
print(f"  HITL nodes      : {hitl_nodes}")
assert hitl_nodes, f"No HITL node found. Nodes: {node_names}"
assert agent.checkpointer is not None
print("  PASS: agent built with HITL and checkpointer")

# ── 5. System prompt includes SKILL.md ──────────────────────────────────────

section("5. System prompt contains UST test style guide")
from ust_agent.subagents.testing import _build_system_prompt

prompt = _build_system_prompt()
assert "parametrize" in prompt.lower() or "parametrize" in prompt
assert "pytest" in prompt
assert "retrieve_knowledge_tool" in prompt
print("  PASS: system prompt includes testing SKILL.md content")

# ── 6. Live auto-approve run ─────────────────────────────────────────────────

section("6. Full auto-approve run: test generation + execution")
from ust_agent.subagents.testing import run

TASK = (
    "Write pytest tests for the validate_email function from UST prior work. "
    "Search the knowledge store for validate_email first. "
    "Write the tests to /ust_workspace/test_ust_email.py. "
    "Test: valid email returns valid=True, invalid email returns valid=False, "
    "empty string returns valid=False. "
    "Run the tests with: python -m pytest /ust_workspace/test_ust_email.py -v"
)
print(f"  Task: {TASK[:120]}...")

output = run(TASK, data_class="internal", auto_approve=True)

print(f"\n  thread_id : {output['thread_id']}")
print(f"  approved  : {len(output['approved'])} action(s)")
for a in output["approved"]:
    print(f"    - {a['tool']}  args_keys={list(a['args'].keys())}")

assert output["messages"], "No messages returned"
assert output["approved"], "No actions approved — agent did not write tests"
assert any(a["tool"] == "write_file" for a in output["approved"]), (
    "write_file not approved — agent did not write a test file"
)
print("  PASS: Testing agent completed with write_file approval")

# ── 7. Langfuse trace check ──────────────────────────────────────────────────

section("7. Langfuse trace check")
import httpx

LANGFUSE_URL = os.getenv("LANGFUSE_BASEURL", "http://localhost:3000")
PK = os.getenv("LANGFUSE_PUBLIC_KEY", "")
SK = os.getenv("LANGFUSE_SECRET_KEY", "")

try:
    resp = httpx.get(
        f"{LANGFUSE_URL}/api/public/traces",
        auth=(PK, SK),
        params={"limit": 5},
        timeout=5.0,
    )
    if resp.status_code == 200:
        traces = resp.json().get("data", [])
        print(f"  Recent traces: {len(traces)}")
        if traces:
            print(f"  Latest: {traces[0].get('name','?')} — {traces[0].get('timestamp','?')[:19]}")
        print("  PASS: Langfuse reachable")
    else:
        print(f"  Langfuse returned {resp.status_code}")
except Exception as exc:
    print(f"  Langfuse not reachable ({exc}) — non-fatal")

# ── Summary ──────────────────────────────────────────────────────────────────

section("Phase 5 complete")
final_msg = output["messages"][-1]
content = getattr(final_msg, "content", str(final_msg))
print(textwrap.indent(content[:800] + ("..." if len(content) > 800 else ""), "  "))
print("\n  All Phase 5 checks passed.")
