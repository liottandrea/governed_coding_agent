"""UST Coding Agent — end-to-end accelerator demo (Phase 6).

Demonstrates the full agent stack on a single delivery feature request:

  1. Code Authoring sub-agent
     - Searches UST knowledge store for prior patterns
     - Generates a UST-styled Python module grounded in those patterns
     - Writes the file to the virtual filesystem (HITL gate → auto-approved)

  2. Testing sub-agent  [routing: cheap → mid cascade]
     - Searches the knowledge store for test patterns
     - Generates a pytest test suite for the generated module
     - Executes the tests in the built-in sandbox
     - Reports pass/fail

Usage:
    uv run python scripts/demo.py
    uv run python scripts/demo.py "Build a phone number validator module"
"""
from __future__ import annotations

import os
import sys
import time
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()
os.chdir(ROOT)


# ── Helpers ───────────────────────────────────────────────────────────────────

_WIDTH = 64


def banner(text: str, char: str = "═") -> None:
    print(f"\n{char * _WIDTH}")
    pad = (_WIDTH - len(text) - 2) // 2
    print(f"{char}{' ' * pad}{text}{' ' * (_WIDTH - len(text) - pad - 2)}{char}")
    print(f"{char * _WIDTH}")


def section(title: str) -> None:
    print(f"\n{'─' * _WIDTH}")
    print(f"  {title}")
    print(f"{'─' * _WIDTH}")


def elapsed(start: float) -> str:
    return f"{time.monotonic() - start:.1f}s"


def last_message(output: dict) -> str:
    msgs = output.get("messages", [])
    if not msgs:
        return "(no output)"
    content = getattr(msgs[-1], "content", str(msgs[-1]))
    return textwrap.indent(content[:1200] + ("…" if len(content) > 1200 else ""), "  ")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    feature_request = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else (
            "Build a Python module ust_phone_validator.py that exposes "
            "a validate_phone(number: str) -> ValidationResult function. "
            "It must follow UST patterns for ValidationResult, use a regex "
            "for E.164 format (+<country_code><number>), and print a demo "
            "when run as __main__ with both a valid and an invalid number."
        )
    )

    banner("UST CODING AGENT — ACCELERATOR DEMO")
    print(f"\n  Feature request:\n")
    print(textwrap.indent(textwrap.fill(feature_request, width=_WIDTH - 4), "  "))

    from ust_agent import observability
    observability.configure()

    # ── Step 1: Code Authoring ────────────────────────────────────────────────

    section("Step 1 / 2  —  Code Authoring sub-agent")
    print("  Model: frontier (Claude Sonnet 4.6 on Bedrock)")
    print("  Tools: retrieve_knowledge_tool, write_file, execute")
    print("  HITL:  auto-approved for demo\n")

    from ust_agent.subagents.code_authoring import run as ca_run

    t0 = time.monotonic()
    ca_output = ca_run(feature_request, data_class="internal", auto_approve=True)
    ca_elapsed = elapsed(t0)

    approved_writes = [a for a in ca_output["approved"] if a["tool"] == "write_file"]
    written_paths = [a["args"].get("file_path", "?") for a in approved_writes]

    print(f"  Duration : {ca_elapsed}")
    print(f"  Actions  : {len(ca_output['approved'])} approved")
    print(f"  Files    : {written_paths or '(none)'}")
    print()
    print(last_message(ca_output))

    if not written_paths:
        print("\n  ⚠  No file was written — cannot proceed to testing step.")
        sys.exit(1)

    generated_path = written_paths[0]

    # ── Step 2: Testing sub-agent ─────────────────────────────────────────────

    section("Step 2 / 2  —  Testing sub-agent  [cascade: Haiku → Sonnet]")
    print("  Model: cheap → mid (routing cascade)")
    print("  Tools: retrieve_knowledge_tool, write_file, execute")
    print("  HITL:  auto-approved for demo\n")

    from ust_agent.subagents.testing import run as test_run

    test_task = (
        f"Write a pytest test suite for the module written to {generated_path}. "
        "Search the knowledge store for UST validation patterns and test examples. "
        f"Write the tests to /ust_workspace/test_{Path(generated_path).name}. "
        f"Run them with: python -m pytest /ust_workspace/test_{Path(generated_path).name} -v"
    )

    t1 = time.monotonic()
    test_output = test_run(test_task, data_class="internal", auto_approve=True)
    test_elapsed = elapsed(t1)

    test_writes = [a for a in test_output["approved"] if a["tool"] == "write_file"]
    all_test_paths = [a["args"].get("file_path", "?") for a in test_writes]
    # Prefer a path that looks like a pytest test file
    test_paths = [p for p in all_test_paths if Path(p).name.startswith("test_")] or all_test_paths

    print(f"  Duration : {test_elapsed}")
    print(f"  Actions  : {len(test_output['approved'])} approved")
    print(f"  Files    : {test_paths or '(none)'}")
    print()
    print(last_message(test_output))

    # ── Delivery summary ───────────────────────────────────────────────────────

    banner("DELIVERY SUMMARY", char="★")
    total = time.monotonic() - t0
    print(f"""
  Feature     {textwrap.shorten(feature_request, width=_WIDTH - 14)}

  Code file   {generated_path}
  Test file   {test_paths[0] if test_paths else '(not written)'}

  Timings
    Code authoring  {ca_elapsed}
    Test generation {test_elapsed}
    Total           {total:.1f}s

  Routing
    codegen  →  frontier  (Claude Sonnet 4.6 / Bedrock)
    testing  →  cheap → mid cascade  (Haiku, Sonnet fallback)

  All model calls routed through LiteLLM gateway.
  All steps traced to Langfuse (http://localhost:3000).
  Data class: internal — policy enforced, never leaves Bedrock.
""")
    banner("DONE", char="═")


if __name__ == "__main__":
    main()
