"""Code Authoring sub-agent.

Generates house-styled Python code grounded in prior work retrieved from the
knowledge store. Steps for every task:

  1. Call retrieve_knowledge to find relevant prior patterns and citations.
  2. Write code to the DeepAgents virtual filesystem (write_file tool).
  3. Execute the code in the built-in sandbox (execute tool).

The HITL gate in harness.run() intercepts write_file and execute actions
before they touch the real filesystem.
"""
from __future__ import annotations

import logging
from pathlib import Path

import deepagents
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from governed_coding_agent.gateway import resolve_model
from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool
from governed_coding_agent import observability

logger = logging.getLogger(__name__)

_SKILL_PATH = Path(__file__).parent.parent / "skills" / "code-authoring" / "SKILL.md"

_BASE_SYSTEM_PROMPT = """\
You are the Governed Coding Agent's Code Authoring sub-agent. You produce high-quality Python code
for engineering projects.

For EVERY coding task you must:
1. Call retrieve_knowledge FIRST to find relevant prior work.
2. Use the retrieved patterns as the starting point for your implementation.
   Cite the source(s) in a comment at the top of each generated file.
3. Write the code to a file using write_file.
4. Execute the written file using the execute tool to confirm it runs without error.
   Use: execute with command "python <filepath>"
5. Report the file path, the citation used, and the execution result.

NEVER generate code without first consulting the knowledge store.
"""


def _build_system_prompt() -> str:
    """Combine the base prompt with the style guide from SKILL.md."""
    try:
        skill_content = _SKILL_PATH.read_text(encoding="utf-8")
        return f"{_BASE_SYSTEM_PROMPT}\n\n---\n\n{skill_content}"
    except FileNotFoundError:
        logger.warning("SKILL.md not found at %s — using base prompt only", _SKILL_PATH)
        return _BASE_SYSTEM_PROMPT


def build_code_authoring_agent(
    data_class: str = "internal",
    checkpointer: MemorySaver | None = None,
) -> deepagents.CompiledSubAgent:
    """Build and return the Code Authoring sub-agent.

    Tools available to the agent:
    - retrieve_knowledge: search the knowledge store for prior patterns
    - write_file: write code to the DeepAgents virtual filesystem
    - execute: run a command in the built-in sandbox
    (write_file and execute are built into deepagents by default)
    """
    from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool as _retrieve_tool

    model = resolve_model("codegen", data_class)
    _checkpointer = checkpointer or MemorySaver()

    agent = deepagents.create_deep_agent(
        model=model,
        tools=[_retrieve_tool],
        system_prompt=_build_system_prompt(),
        interrupt_on={"write_file": True, "execute": True},
        checkpointer=_checkpointer,
        name="code-authoring",
    )
    return agent


def run(
    task: str,
    *,
    data_class: str = "internal",
    auto_approve: bool = False,
) -> dict:
    """Run a code authoring task end-to-end with HITL approval.

    Returns:
        dict with keys: messages, files, thread_id, approved, citations
    """
    import uuid
    from langchain_core.messages import HumanMessage

    observability.configure()
    agent = build_code_authoring_agent(data_class=data_class)
    thread_id = str(uuid.uuid4())
    thread_cfg = {"configurable": {"thread_id": thread_id}}

    state: dict = {"messages": [HumanMessage(content=task)]}
    approved_actions: list[dict] = []

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
            messages = final.values.get("messages", [])
            files = final.values.get("files", {})
            return {
                "messages": messages,
                "files": files,
                "thread_id": thread_id,
                "approved": approved_actions,
            }

        action_requests = interrupt_value[0].value.get("action_requests", [])
        decisions: list[dict] = []

        for req in action_requests:
            tool_name = req.get("name", "unknown")
            tool_args = req.get("args", {})

            if auto_approve:
                decision: dict = {"type": "approve"}
                logger.info("Auto-approving %s(%s)", tool_name, tool_args)
            else:
                print(f"\n⚠  Approval required: {tool_name}")
                print(f"   Args: {tool_args}")
                answer = input("   Approve? [y/n] ").strip().lower()
                decision = {"type": "approve"} if answer in ("y", "yes", "") else {
                    "type": "reject",
                    "message": input("   Reason: ").strip() or None,
                }

            decisions.append(decision)
            if decision["type"] == "approve":
                approved_actions.append({"tool": tool_name, "args": tool_args})

        state = Command(resume={"decisions": decisions})  # type: ignore[assignment]
