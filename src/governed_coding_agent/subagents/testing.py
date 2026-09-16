"""Testing sub-agent.

Generates pytest tests for code produced by the Code Authoring sub-agent.
The agent consults the knowledge store for existing test patterns before
writing new tests, then executes them in the built-in sandbox to confirm they pass.

Routing: testing role → cheap (Haiku) with fallback → mid (Sonnet) so the
cascade kicks in automatically when the primary model is throttled or unavailable.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

import deepagents
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from governed_coding_agent import observability
from governed_coding_agent.gateway import resolve_model
from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool

logger = logging.getLogger(__name__)

_SKILL_PATH = Path(__file__).parent.parent / "skills" / "testing" / "SKILL.md"

_BASE_SYSTEM_PROMPT = """\
You are the Governed Coding Agent's Test Authoring sub-agent. You write high-quality pytest tests for
engineering project code.

For EVERY testing task you must:
1. Call retrieve_knowledge_tool FIRST to find existing test patterns and
   the code being tested.
2. Write a complete pytest test file using write_file.
   - Name it test_<module_name>.py in the same directory or tests/.
   - Cite the source module and any knowledge snippets used in a comment header.
3. Execute the test file using the execute tool:
   execute with command "python -m pytest <filepath> -v"
4. Report: test file path, pass/fail count, and which patterns were reused.

If tests fail, investigate and fix before reporting done.
NEVER report success without running the tests.
"""


def _build_system_prompt() -> str:
    try:
        skill = _SKILL_PATH.read_text(encoding="utf-8")
        return f"{_BASE_SYSTEM_PROMPT}\n\n---\n\n{skill}"
    except FileNotFoundError:
        logger.warning("testing SKILL.md not found at %s", _SKILL_PATH)
        return _BASE_SYSTEM_PROMPT


def build_testing_agent(
    data_class: str = "internal",
    checkpointer: MemorySaver | None = None,
) -> deepagents.CompiledSubAgent:
    """Build and return the Testing sub-agent.

    Uses the 'testing' role which cascades cheap → mid on failure.
    Tools: retrieve_knowledge_tool + deepagents defaults (write_file, execute).
    HITL gate is active on write_file and execute.
    """
    model = resolve_model("testing", data_class)
    _checkpointer = checkpointer or MemorySaver()

    agent = deepagents.create_deep_agent(
        model=model,
        tools=[retrieve_knowledge_tool],
        system_prompt=_build_system_prompt(),
        interrupt_on={"write_file": True, "execute": True},
        checkpointer=_checkpointer,
        name="testing",
    )
    return agent


def run(
    task: str,
    *,
    data_class: str = "internal",
    auto_approve: bool = False,
) -> dict:
    """Run a test-authoring task end-to-end with HITL approval.

    Returns:
        dict with keys: messages, files, thread_id, approved
    """
    observability.configure()
    agent = build_testing_agent(data_class=data_class)
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
            return {
                "messages": final.values.get("messages", []),
                "files": final.values.get("files", {}),
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
