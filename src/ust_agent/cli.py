"""UST Coding Agent — interactive CLI.

Drop-in terminal coding assistant. Run it in any project directory.

Usage:
    # Interactive REPL (like running `claude`)
    ust-agent

    # Single-shot task
    ust-agent "Refactor the auth module to use our retry decorator pattern"

    # Resume a previous session
    ust-agent --session <thread-id>

    # Restricted data (local models only, never Bedrock)
    ust-agent --data-class restricted

Flags:
    --data-class   public | internal | restricted  (default: internal)
    --auto-approve  skip HITL prompts (use in CI / scripts)
    --session       thread ID to resume (printed at session start)
    --role          agent role: planner | codegen  (default: planner)
    --no-knowledge  skip UST knowledge store queries
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.types import Command

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

_BANNER = """\
╔══════════════════════════════════════════════════════╗
║          UST Coding Agent  —  interactive            ║
║  Type your task. 'exit' or Ctrl+C to quit.          ║
╚══════════════════════════════════════════════════════╝"""

_SYSTEM_PROMPT = """\
You are the UST Coding Agent — an expert coding assistant for UST delivery \
projects. You work directly inside the developer's project directory.

Your capabilities:
- read_file / write_file / edit_file / ls / glob / grep  — full filesystem access
- execute — run any shell command in the project
- retrieve_knowledge_tool — search UST's prior code patterns and examples

For every coding task:
1. Search the knowledge store first with retrieve_knowledge_tool to find \
relevant UST patterns, then ground your implementation in them.
2. Prefer editing existing files over rewriting them from scratch.
3. When writing new code, follow UST style (from __future__ import annotations, \
Google docstrings, dataclasses, pathlib, snake_case, specific exceptions).
4. Always verify your work: run tests or execute the changed code.
5. Cite the UST pattern you used in a brief comment at the top of new files.

Be direct. Work in the actual project directory. Do not ask clarifying questions \
unless the task is genuinely ambiguous — make a sensible assumption and proceed.
"""


def _build_agent(
    data_class: str,
    role: str,
    include_knowledge: bool,
) -> object:
    from ust_agent.harness import build_agent
    from ust_agent.knowledge.retrieve import retrieve_knowledge_tool

    extra_tools = [retrieve_knowledge_tool] if include_knowledge else []
    return build_agent(
        role=role,
        data_class=data_class,
        extra_tools=extra_tools,
        system_prompt=_SYSTEM_PROMPT,
    )


def _run_turn(
    agent: object,
    message: str,
    thread_cfg: dict,
    auto_approve: bool,
    approved_actions: list,
) -> str:
    """Run one REPL turn and return the agent's final text response."""
    state: object = {"messages": [HumanMessage(content=message)]}

    while True:
        interrupted = False
        interrupt_value = None

        for event in agent.stream(state, config=thread_cfg, stream_mode="updates"):
            if "__interrupt__" in event:
                interrupted = True
                interrupt_value = event["__interrupt__"]
                break

        if not interrupted:
            final = agent.get_state(thread_cfg)
            msgs = final.values.get("messages", [])
            if not msgs:
                return "(no response)"
            last = msgs[-1]
            return getattr(last, "content", str(last))

        action_requests: list = interrupt_value[0].value.get("action_requests", [])
        decisions: list = []

        for req in action_requests:
            tool_name = req.get("name", "unknown")
            tool_args = req.get("args", {})

            if auto_approve:
                decision: dict = {"type": "approve"}
                logger.info("Auto-approving %s", tool_name)
            else:
                print(f"\n  ⚠  {tool_name}")
                # Show a compact preview of the action
                if tool_name == "write_file":
                    path = tool_args.get("file_path", "?")
                    lines = tool_args.get("content", "").splitlines()
                    print(f"     write → {path}  ({len(lines)} lines)")
                elif tool_name == "execute":
                    cmd = tool_args.get("command", "?")
                    print(f"     exec  → {cmd}")
                else:
                    print(f"     args  → {list(tool_args.keys())}")

                answer = input("  Approve? [Y/n] ").strip().lower()
                if answer in ("n", "no"):
                    reason = input("  Reason (optional): ").strip()
                    decision = {"type": "reject", "message": reason or None}
                else:
                    decision = {"type": "approve"}

            decisions.append(decision)
            if decision["type"] == "approve":
                approved_actions.append({"tool": tool_name, "args": tool_args})

        state = Command(resume={"decisions": decisions})  # type: ignore[assignment]


def _repl(
    agent: object,
    thread_id: str,
    auto_approve: bool,
    data_class: str,
    cwd: Path,
) -> None:
    thread_cfg = {"configurable": {"thread_id": thread_id}}
    approved_actions: list = []

    print(_BANNER)
    print(f"  session  : {thread_id}")
    print(f"  data class: {data_class}")
    print(f"  directory : {cwd}")
    print(f"  resume   : ust-agent --session {thread_id}\n")

    while True:
        try:
            task = input("▶ ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nBye.")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q", ":q"):
            print("Bye.")
            break

        try:
            response = _run_turn(
                agent, task, thread_cfg, auto_approve, approved_actions
            )
            print(f"\n{response}\n")
        except Exception as exc:
            print(f"\n  [error] {exc}\n")
            logger.exception("Turn failed")


def main(argv: list[str] | None = None) -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="ust-agent",
        description="UST Coding Agent — interactive coding assistant",
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Single-shot task. Omit for interactive REPL.",
    )
    parser.add_argument(
        "--data-class",
        default=os.getenv("DEFAULT_DATA_CLASS", "internal"),
        choices=["public", "internal", "restricted"],
        help="Data-class policy (default: internal)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Skip HITL approval prompts",
    )
    parser.add_argument(
        "--session",
        default=None,
        metavar="THREAD_ID",
        help="Resume a previous session by thread ID",
    )
    parser.add_argument(
        "--role",
        default="planner",
        choices=["planner", "codegen"],
        help="Agent role (default: planner)",
    )
    parser.add_argument(
        "--no-knowledge",
        action="store_true",
        default=False,
        help="Disable UST knowledge store queries",
    )

    args = parser.parse_args(argv)

    cwd = Path.cwd()
    thread_id = args.session or str(uuid.uuid4())

    from ust_agent import observability
    observability.configure()

    agent = _build_agent(
        data_class=args.data_class,
        role=args.role,
        include_knowledge=not args.no_knowledge,
    )

    if args.task:
        # Single-shot mode
        thread_cfg = {"configurable": {"thread_id": thread_id}}
        approved: list = []
        response = _run_turn(
            agent, args.task, thread_cfg, args.auto_approve, approved
        )
        print(response)
    else:
        # Interactive REPL
        _repl(agent, thread_id, args.auto_approve, args.data_class, cwd)


if __name__ == "__main__":
    main()
