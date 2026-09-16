"""Governed Coding Agent orchestrator.

Assembles the top-level DeepAgents agent using the high-level API.
The model is always resolved through gateway.py — never a direct provider SDK.

Human-in-the-loop: the agent pauses before any write_file or execute action and
waits for an explicit approval. The caller drives the approval loop via run().

Langfuse tracing: observability.configure() registers LiteLLM→Langfuse callbacks
so every model call is traced with token cost. The full agent run is grouped
under a single Langfuse trace via a per-run trace context.
"""
from __future__ import annotations

import os
import uuid
import logging
from typing import Any

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import deepagents
from deepagents import CompiledSubAgent
from deepagents.backends import LocalShellBackend

from governed_coding_agent.gateway import resolve_model
from governed_coding_agent import observability

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are the Governed Coding Agent. "
    "You help engineering teams write high-quality, house-styled code "
    "grounded in prior project work. "
    "Use the write_file tool to write code to files. "
    "Always be concise and precise."
)

# Tools that require human approval before execution.
# deepagents' built-in execute tool is named "execute" (not "shell").
_INTERRUPT_TOOLS = {"write_file": True, "execute": True}


def _inject_session_id(model: Any, session_id: str) -> None:
    """Stamp session_id into the model's metadata so Langfuse groups traces.

    ChatLiteLLM passes model_kwargs as extra kwargs to litellm.completion().
    litellm.completion(metadata={"session_id": ...}) flows through to
    litellm_params["metadata"] which the Langfuse integration reads.
    For CascadingChatModel we stamp both primary and fallback.
    """
    from governed_coding_agent.gateway import CascadingChatModel
    from langchain_litellm import ChatLiteLLM

    def _stamp(m: ChatLiteLLM) -> None:
        existing = dict(m.model_kwargs or {})
        meta = dict(existing.get("metadata") or {})
        meta["session_id"] = session_id
        existing["metadata"] = meta
        m.model_kwargs = existing

    if isinstance(model, CascadingChatModel):
        _stamp(model.primary)
        _stamp(model.fallback)
    elif isinstance(model, ChatLiteLLM):
        _stamp(model)


def build_agent(
    role: str = "planner",
    data_class: str | None = None,
    checkpointer: MemorySaver | None = None,
    extra_tools: list | None = None,
    subagents: list | None = None,
    system_prompt: str | None = None,
    cwd: os.PathLike | str | None = None,
    session_id: str | None = None,
    group_overrides: dict[str, str] | None = None,
    **deepagents_kwargs: Any,
) -> CompiledSubAgent:
    """Build and return the top-level Governed Coding Agent orchestrator.

    The agent is wired with:
    - A Bedrock model resolved via gateway (role + data_class → policy → model)
    - Human-in-the-loop interrupt on write_file and shell actions
    - A MemorySaver checkpointer so state is preserved across interrupt/resume
    - Langfuse tracing via LiteLLM callbacks

    Args:
        system_prompt: Override the default system prompt (used by the CLI).
        session_id: LangGraph thread_id; stamped into model_kwargs so every
            litellm.completion() call carries metadata["session_id"] and
            Langfuse groups all traces under one Session.
    """
    load_dotenv()
    observability.configure()

    effective_data_class = data_class or os.getenv("DEFAULT_DATA_CLASS", "internal")
    model = resolve_model(role, effective_data_class, group_overrides=group_overrides)

    if session_id:
        _inject_session_id(model, session_id)

    _checkpointer = checkpointer or MemorySaver()

    backend = LocalShellBackend(
        root_dir=cwd or os.getcwd(),
        inherit_env=True,  # inherit RTK-patched PATH and all env vars
        virtual_mode=False,
    )

    agent = deepagents.create_deep_agent(
        model=model,
        system_prompt=system_prompt or _SYSTEM_PROMPT,
        tools=extra_tools or [],
        subagents=subagents or [],
        interrupt_on=_INTERRUPT_TOOLS,
        checkpointer=_checkpointer,
        backend=backend,
        **deepagents_kwargs,
    )
    return agent


def run(
    task: str,
    *,
    role: str = "planner",
    data_class: str | None = None,
    agent: CompiledSubAgent | None = None,
    thread_id: str | None = None,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Run a task end-to-end with human-in-the-loop approval on writes.

    Returns a dict with keys:
        messages  — full message history
        files     — virtual filesystem state (path → content)
        thread_id — thread ID for resuming later
        approved  — list of tool calls the human approved

    If auto_approve=True, all write/shell actions are approved automatically
    (used in tests and the Phase 6 demo when running non-interactively).
    """
    _agent = agent or build_agent(role=role, data_class=data_class)
    _thread_id = thread_id or str(uuid.uuid4())
    thread_cfg: dict[str, Any] = {"configurable": {"thread_id": _thread_id}}

    from langchain_core.messages import HumanMessage

    state: dict[str, Any] = {"messages": [HumanMessage(content=task)]}
    approved_actions: list[dict] = []

    logger.info("Starting task on thread %s", _thread_id)

    while True:
        # Stream so we can detect interrupts event-by-event
        interrupted = False
        interrupt_value: Any = None

        for event in _agent.stream(state, config=thread_cfg, stream_mode="updates"):
            if "__interrupt__" in event:
                interrupted = True
                interrupt_value = event["__interrupt__"]
                break

        if not interrupted:
            # Run completed — pull final state
            final = _agent.get_state(thread_cfg)
            return {
                "messages": final.values.get("messages", []),
                "files": final.values.get("files", {}),
                "thread_id": _thread_id,
                "approved": approved_actions,
            }

        # Handle interrupt — one or more tool calls need approval
        action_requests: list[dict] = interrupt_value[0].value.get("action_requests", [])
        decisions: list[dict] = []

        for req in action_requests:
            tool_name = req.get("name", "unknown")
            tool_args = req.get("args", {})
            description = req.get("description", "")

            if auto_approve:
                decision: dict = {"type": "approve"}
                logger.info("Auto-approving %s(%s)", tool_name, tool_args)
            else:
                print(f"\n⚠  Approval required for: {tool_name}")
                print(f"   Args: {tool_args}")
                answer = input("   Approve? [y/n/edit] ").strip().lower()
                if answer in ("y", "yes", ""):
                    decision = {"type": "approve"}
                elif answer in ("n", "no"):
                    reason = input("   Rejection reason (optional): ").strip()
                    decision = {"type": "reject", "message": reason or None}
                else:
                    # edit path — for MVP just approve; full edit UX is later
                    decision = {"type": "approve"}

            decisions.append(decision)
            if decision["type"] == "approve":
                approved_actions.append({"tool": tool_name, "args": tool_args})

        # Resume the graph with the human decisions
        state = Command(resume={"decisions": decisions})  # type: ignore[assignment]
