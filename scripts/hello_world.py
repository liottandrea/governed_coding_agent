"""Phase 0 acceptance check: prove deepagents installs and the gateway resolves.

Run: uv run python scripts/hello_world.py

This does NOT make a live model call — it only verifies that:
  1. deepagents imports correctly
  2. The gateway resolves a role+data_class to a ChatLiteLLM model object
  3. The policy check blocks a forbidden combination
"""
from __future__ import annotations

import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, "src")

print("─── UST Coding Agent — Phase 0 hello-world ───")

# 1. Import check
import deepagents  # noqa: E402
import deepagents as da
print(f"✓ deepagents {da.__version__} imported")

from langchain_litellm import ChatLiteLLM
print(f"✓ langchain_litellm imported")

import langgraph  # noqa: F401
import importlib.metadata as _meta
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

# 4. create_deep_agent smoke-test (no model call, just construction)
# We pass a dummy model string since we're offline in this check.
# The agent graph is compiled without hitting a real API.
try:
    agent = deepagents.create_deep_agent(
        model=model,
        system_prompt="Hello from UST.",
        name="ust-hello-world",
    )
    print(f"✓ create_deep_agent() compiled: {type(agent).__name__}")
except Exception as exc:
    print(f"✗ create_deep_agent() failed: {exc}")
    raise

print("\n✓ Phase 0 acceptance criteria met.")
print(f"  deepagents: {da.__version__}")
print(f"  langgraph:  {_lg_version}")
