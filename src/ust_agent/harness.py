"""UST Coding Agent orchestrator.

Assembles the top-level DeepAgents agent using the high-level API.
The model is always resolved through gateway.py — never a direct provider SDK.

Phase 0: hello-world single-agent.
Phase 2+: orchestrator with Knowledge and Code Authoring sub-agents.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

import deepagents

from ust_agent.gateway import resolve_model
from ust_agent import observability


def build_agent(
    role: str = "planner",
    data_class: str | None = None,
    **deepagents_kwargs,
) -> deepagents.CompiledSubAgent:
    """Build and return the top-level UST orchestrator agent."""
    load_dotenv()
    observability.configure()

    effective_data_class = data_class or os.getenv("DEFAULT_DATA_CLASS", "internal")
    model = resolve_model(role, effective_data_class)

    agent = deepagents.create_deep_agent(
        model=model,
        system_prompt=(
            "You are the UST Coding Agent. "
            "You help delivery teams write high-quality, UST-styled code "
            "grounded in prior UST work. Be concise and precise."
        ),
        **deepagents_kwargs,
    )
    return agent
