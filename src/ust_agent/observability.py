"""Langfuse observability wiring.

Call configure() once at process startup (e.g. from harness.py or demo.py).
It registers the Langfuse callback with LiteLLM so every model call is traced.

Environment variables required:
    LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY
    LANGFUSE_HOST   (default: http://localhost:3000)
"""
from __future__ import annotations

import os


def configure() -> None:
    """Wire LiteLLM → Langfuse tracing. Safe to call multiple times."""
    from langfuse.callback import CallbackHandler as LangfuseCallback  # type: ignore[import]
    import litellm

    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

    handler = LangfuseCallback(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )

    # Register as a global LiteLLM success/failure callback so every call is traced.
    if handler not in litellm.success_callback:
        litellm.success_callback.append(handler)
    if handler not in litellm.failure_callback:
        litellm.failure_callback.append(handler)
