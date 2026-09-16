"""Governed Coding Agent — JSON-lines server mode for the VS Code extension.

Driven by the extension via stdin/stdout (newline-delimited JSON).

stdin commands (extension → server):
  {"type": "ping"}
  {"type": "start",    "thread_id": "...", "data_class": "internal",
                       "role": "planner", "group_overrides": {...},
                       "system_prompt": "...", "include_knowledge": true,
                       "cwd": "/path/to/project"}
  {"type": "task",     "message": "..."}
  {"type": "decision", "decisions": [{"type": "approve"} | {"type": "reject", "message": "..."}]}
  {"type": "sessions"}

stdout events (server → extension):
  {"type": "pong"}
  {"type": "ready",     "session_id": "..."}
  {"type": "thinking"}
  {"type": "response",  "content": "..."}
  {"type": "interrupt", "action_requests": [...]}
  {"type": "sessions",  "rows": [{"thread_id": "...", "turns": 5}]}
  {"type": "trace_url", "url": "..."}
  {"type": "error",     "message": "..."}
"""
from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_AGENT_HOME = Path(os.getenv("GOVERNED_AGENT_HOME", Path(__file__).parent.parent.parent))
_stdout_lock = threading.Lock()


def _emit(event: dict[str, Any]) -> None:
    """Write one JSON event line to stdout. Thread-safe."""
    with _stdout_lock:
        print(json.dumps(event), flush=True)


# ── Postgres checkpointer singleton ──────────────────────────────────────────

_checkpointer = None
_checkpointer_ctx = None


def _ensure_checkpointer():
    global _checkpointer, _checkpointer_ctx
    if _checkpointer is None:
        from langgraph.checkpoint.postgres import PostgresSaver
        from governed_coding_agent.cli import _dsn
        _checkpointer_ctx = PostgresSaver.from_conn_string(_dsn())
        _checkpointer = _checkpointer_ctx.__enter__()
        _checkpointer.setup()
    return _checkpointer


# ── Active session ────────────────────────────────────────────────────────────

class AgentSession:
    """One active agent session with a HITL state machine."""

    def __init__(self) -> None:
        self.agent = None
        self.thread_id: str | None = None
        self.thread_cfg: dict | None = None
        self._decision_q: queue.Queue = queue.Queue(maxsize=1)
        self._worker: threading.Thread | None = None

    def start(self, cmd: dict) -> None:
        """Initialise (or resume) an agent session from a 'start' command."""
        from governed_coding_agent.harness import build_agent
        from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool
        from governed_coding_agent import observability
        from governed_coding_agent.cli import _SYSTEM_PROMPT_TEMPLATE

        observability.configure()

        thread_id: str = cmd.get("thread_id") or str(uuid.uuid4())
        data_class: str = cmd.get("data_class", "internal")
        role: str = cmd.get("role", "planner")
        group_overrides: dict | None = cmd.get("group_overrides") or None
        include_knowledge: bool = cmd.get("include_knowledge", True)
        cwd = Path(cmd.get("cwd") or os.getcwd())
        system_prompt: str = cmd.get("system_prompt") or _SYSTEM_PROMPT_TEMPLATE.format(cwd=cwd)

        checkpointer = _ensure_checkpointer()
        extra_tools = [retrieve_knowledge_tool] if include_knowledge else []

        self.agent = build_agent(
            role=role,
            data_class=data_class,
            extra_tools=extra_tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            cwd=cwd,
            session_id=thread_id,
            group_overrides=group_overrides,
        )
        self.thread_id = thread_id
        self.thread_cfg = {"configurable": {"thread_id": thread_id}}
        _emit({"type": "ready", "session_id": thread_id})

    def run_task(self, message: str) -> None:
        """Start streaming a task; runs the agent in a background thread."""
        if self.agent is None:
            _emit({"type": "error", "message": "No session — send 'start' first."})
            return
        if self._worker and self._worker.is_alive():
            _emit({"type": "error", "message": "Task already running — wait for it to finish."})
            return

        from langchain_core.messages import HumanMessage
        state: dict = {"messages": [HumanMessage(content=message)]}
        _emit({"type": "thinking"})
        self._worker = threading.Thread(
            target=self._stream_loop, args=(state,), daemon=True
        )
        self._worker.start()

    def send_decision(self, decisions: list[dict]) -> None:
        """Deliver HITL decisions to unblock the waiting stream thread."""
        try:
            self._decision_q.put_nowait(decisions)
        except queue.Full:
            _emit({"type": "error", "message": "No pending interrupt to resolve."})

    # ── stream thread ─────────────────────────────────────────────────────────

    def _stream_loop(self, initial_state: Any) -> None:
        """Background thread: drives agent.stream(), handles interrupts."""
        from langgraph.types import Command

        state = initial_state
        while True:
            interrupted = False
            interrupt_value: Any = None

            try:
                for event in self.agent.stream(
                    state, config=self.thread_cfg, stream_mode="updates"
                ):
                    if "__interrupt__" in event:
                        interrupted = True
                        interrupt_value = event["__interrupt__"]
                        break
            except Exception as exc:
                logger.exception("Agent stream error")
                _emit({"type": "error", "message": str(exc)})
                return

            if not interrupted:
                final = self.agent.get_state(self.thread_cfg)
                msgs = final.values.get("messages", [])
                content = ""
                if msgs:
                    last = msgs[-1]
                    content = getattr(last, "content", str(last))
                _emit({"type": "response", "content": content})
                host = os.getenv("LANGFUSE_HOST", "http://localhost:13000")
                _emit({"type": "trace_url", "url": f"{host}/sessions/{self.thread_id}"})
                return

            # Interrupt — surface to UI and wait for human decision
            action_requests: list = interrupt_value[0].value.get("action_requests", [])
            _emit({"type": "interrupt", "action_requests": action_requests})
            decisions = self._decision_q.get()  # blocks until send_decision() is called
            state = Command(resume={"decisions": decisions})


# ── Session listing ───────────────────────────────────────────────────────────

def _list_sessions() -> None:
    import psycopg
    from governed_coding_agent.cli import _dsn

    sql = """
        SELECT thread_id, max((metadata->>'step')::int) AS turns
        FROM checkpoints
        GROUP BY thread_id
        ORDER BY max(checkpoint_id) DESC
        LIMIT 30
    """
    try:
        with psycopg.connect(_dsn()) as conn:
            rows = conn.execute(sql).fetchall()
        _emit({"type": "sessions", "rows": [
            {"thread_id": r[0], "turns": r[1] or 0} for r in rows
        ]})
    except Exception as exc:
        _emit({"type": "error", "message": f"Could not list sessions: {exc}"})


# ── Main server loop ──────────────────────────────────────────────────────────

def run_server() -> None:
    """Read JSON commands from stdin; write JSON events to stdout."""
    load_dotenv(_AGENT_HOME / ".env")
    session = AgentSession()

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            cmd: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            _emit({"type": "error", "message": f"Invalid JSON: {exc}"})
            continue

        cmd_type = cmd.get("type")
        try:
            if cmd_type == "ping":
                _emit({"type": "pong"})
            elif cmd_type == "start":
                session.start(cmd)
            elif cmd_type == "task":
                session.run_task(cmd.get("message", ""))
            elif cmd_type == "decision":
                session.send_decision(cmd.get("decisions", []))
            elif cmd_type == "sessions":
                _list_sessions()
            else:
                _emit({"type": "error", "message": f"Unknown command: {cmd_type!r}"})
        except Exception as exc:
            logger.exception("Command error")
            _emit({"type": "error", "message": str(exc)})
