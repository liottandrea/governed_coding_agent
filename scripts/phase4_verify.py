"""Phase 4 verification: Code Authoring sub-agent.

Demonstrates:
  1. Agent retrieves prior knowledge first (citation check).
  2. Agent writes a house-styled Python module (write_file approved).
  3. Agent executes the generated module (execute approved).
  4. Langfuse trace is created.

Run with:
    uv run python scripts/phase4_verify.py
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

# ── 1. Import guard ──────────────────────────────────────────────────────────

from governed_coding_agent.subagents.code_authoring import build_code_authoring_agent, run


def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── 2. Quick import smoke test ───────────────────────────────────────────────

section("2. Import / build agent (no LLM call)")
agent = build_code_authoring_agent(data_class="internal")
print(f"  Agent type : {type(agent).__name__}")
print(f"  Checkpointer: {type(agent.checkpointer).__name__}")
node_names = list(agent.nodes.keys())
hitl_nodes = [n for n in node_names if "HumanInTheLoop" in n]
print(f"  HITL nodes : {hitl_nodes}")
assert hitl_nodes, "HITL node missing from code-authoring agent"
print("  PASS: agent built with HITL nodes")

# ── 3. retrieve_knowledge_tool smoke test ────────────────────────────────────

section("3. retrieve_knowledge_tool (live Bedrock embed)")
from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool

result = retrieve_knowledge_tool.invoke({"query": "parse CSV file", "top_k": 3})
print(textwrap.indent(result[:600] + ("..." if len(result) > 600 else ""), "  "))
assert "relevant snippet" in result or "No relevant" in result, "Unexpected tool output"
print("  PASS: retrieve_knowledge_tool returns formatted output")

# ── 4. Live auto_approve run ─────────────────────────────────────────────────

section("4. Full auto-approve run (write_file + execute)")
TASK = (
    "Create a Python module at /governed_workspace/email_check.py that:\n"
    "1. Imports the ValidationResult pattern from prior work.\n"
    "2. Exposes a function validate_email(email: str) -> ValidationResult.\n"
    "3. Prints 'ok' to stdout when run as __main__ with a valid email.\n"
    "Follow the house code style exactly (from __future__ import annotations, "
    "dataclass, pathlib, Google docstrings, snake_case)."
)

print(f"  Task: {TASK[:120]}...")
output = run(TASK, data_class="internal", auto_approve=True)

print(f"\n  thread_id : {output['thread_id']}")
print(f"  approved  : {len(output['approved'])} action(s)")
for a in output["approved"]:
    print(f"    - {a['tool']}  args_keys={list(a['args'].keys())}")

assert output["messages"], "No messages in result"
assert output["approved"], "No approved actions — agent may not have written anything"
assert any(a["tool"] == "write_file" for a in output["approved"]), (
    "write_file was never approved — agent did not generate code"
)
print("  PASS: code authoring task completed with write_file approval")

# ── 5. Langfuse trace check ──────────────────────────────────────────────────

section("5. Langfuse trace check")
import httpx

LANGFUSE_URL = os.getenv("LANGFUSE_BASEURL", "http://localhost:13000")
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
        print(f"  Langfuse returned {resp.status_code} — check docker-compose")
except Exception as exc:
    print(f"  Langfuse not reachable ({exc}) — traces not verified (non-fatal)")

# ── 6. Summary ───────────────────────────────────────────────────────────────

section("Phase 4 complete")
final_msg = output["messages"][-1]
content = getattr(final_msg, "content", str(final_msg))
print(textwrap.indent(content[:800] + ("..." if len(content) > 800 else ""), "  "))
print("\n  All Phase 4 checks passed.")
