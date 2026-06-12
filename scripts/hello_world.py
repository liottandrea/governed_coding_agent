"""Phase 0 acceptance check: prove deepagents installs and the gateway resolves.

Run: uv run python scripts/hello_world.py

Verifies:
  1. deepagents imports correctly
  2. The gateway resolves a role+data_class → ChatLiteLLM backed by Bedrock
  3. The policy check blocks a forbidden combination
  4. create_deep_agent() compiles without error
  5. (optional, live) A trivial Bedrock call succeeds when --live flag is passed
"""
from __future__ import annotations

import sys
import os
import importlib.metadata as _meta

# Allow running from repo root without installing the package
sys.path.insert(0, "src")

LIVE = "--live" in sys.argv

print("─── UST Coding Agent — Phase 0 hello-world ───")
print(f"  AWS_PROFILE = {os.environ.get('AWS_PROFILE', 'genai-agent-user')} (Bedrock)")
print()

# 1. Import check
import deepagents as da
print(f"✓ deepagents {da.__version__} imported")

from langchain_litellm import ChatLiteLLM  # noqa: F401
print("✓ langchain_litellm imported")

_lg_version = _meta.version("langgraph")
print(f"✓ langgraph {_lg_version} imported")

# 2. Gateway resolution
from ust_agent.gateway import resolve_model, resolve_group
from ust_agent.policy import PolicyError

group = resolve_group("codegen")
print(f"✓ role 'codegen' → model group '{group}'")

model = resolve_model("codegen", "internal")
print(f"✓ resolve_model('codegen', 'internal') → {type(model).__name__}(model={model.model!r})")

# 3. Policy refusal
try:
    resolve_model("codegen", "restricted")
    print("✗ Expected PolicyError for restricted+frontier — not raised!")
    sys.exit(1)
except PolicyError as e:
    print(f"✓ PolicyError raised for restricted+frontier: {e}")

# 4. create_deep_agent compilation (no API call)
try:
    agent = da.create_deep_agent(
        model=model,
        system_prompt="Hello from UST Coding Agent.",
        name="ust-hello-world",
    )
    print(f"✓ create_deep_agent() compiled: {type(agent).__name__}")
except Exception as exc:
    print(f"✗ create_deep_agent() failed: {exc}")
    raise

# 5. Live Bedrock call (opt-in)
if LIVE:
    print("\n─── Live Bedrock call (--live) ───")
    from langchain_core.messages import HumanMessage
    try:
        resp = model.invoke([HumanMessage(content="Reply with exactly: UST hello-world OK")])
        print(f"✓ Bedrock response: {resp.content!r}")
    except Exception as exc:
        print(f"✗ Bedrock call failed: {exc}")
        raise
else:
    print("\n  (skip live call — pass --live to test Bedrock connectivity)")

print("\n✓ Phase 0 acceptance criteria met.")
print(f"  deepagents: {da.__version__}")
print(f"  langgraph:  {_lg_version}")
print(f"  backend:    AWS Bedrock / genai-agent-user / us-east-1")
