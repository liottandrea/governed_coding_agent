"""Langfuse observability wiring.

Call configure() once at process startup (harness.py, demo.py, or test scripts).
It wires LiteLLM → Langfuse so every model call is traced with token cost.

LiteLLM's built-in Langfuse integration is used (litellm.success_callback =
["langfuse"]) rather than the lower-level CallbackHandler, which keeps the
surface minimal and lets LiteLLM own the span lifecycle.

Required env vars:
    LANGFUSE_PUBLIC_KEY   — Langfuse project public key
    LANGFUSE_SECRET_KEY   — Langfuse project secret key
    LANGFUSE_HOST         — e.g. http://localhost:3000 (default)
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

_configured = False


def configure() -> None:
    """Wire LiteLLM → Langfuse. Safe to call multiple times (idempotent)."""
    global _configured
    if _configured:
        return

    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        logger.warning(
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set — "
            "traces will not be sent to Langfuse."
        )
        return

    # Set the env vars LiteLLM's Langfuse integration reads.
    os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    os.environ["LANGFUSE_HOST"] = host

    import litellm

    if "langfuse" not in litellm.success_callback:
        litellm.success_callback.append("langfuse")
    if "langfuse" not in litellm.failure_callback:
        litellm.failure_callback.append("langfuse")

    _configured = True
    logger.info("Langfuse tracing enabled → %s", host)


def trace_url(trace_id: str) -> str:
    """Return the Langfuse UI URL for a trace ID."""
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    return f"{host}/trace/{trace_id}"
