"""LiteLLM gateway.

All model calls in the agent go through resolve_model(role, data_class) which:
  1. Looks up the model group for the role in routing-rules.yaml
  2. Enforces the data-class policy via policy.py
  3. Returns a ChatLiteLLM instance configured with the resolved group name

Usage:
    chat_model = resolve_model("codegen", "internal")
    response = chat_model.invoke([HumanMessage(content="hello")])
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from langchain_litellm import ChatLiteLLM

from ust_agent import policy


_ROUTING_CONFIG = Path(os.getenv("ROUTING_CONFIG_PATH", "config/routing-rules.yaml"))


def _load_routing(path: Path = _ROUTING_CONFIG) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_group(role: str, routing_path: Path = _ROUTING_CONFIG) -> str:
    """Return the model group name for a given role."""
    routing = _load_routing(routing_path)
    roles: dict[str, Any] = routing.get("roles", {})
    if role not in roles:
        raise ValueError(
            f"Unknown role '{role}'. Known roles: {list(roles.keys())}"
        )
    return roles[role]["default_group"]


def resolve_model(
    role: str,
    data_class: str,
    *,
    routing_path: Path = _ROUTING_CONFIG,
    policy_path: Path | None = None,
    **litellm_kwargs: Any,
) -> ChatLiteLLM:
    """Resolve role + data_class → policy-checked ChatLiteLLM instance.

    Raises policy.PolicyError if the combination is forbidden.
    """
    group = resolve_group(role, routing_path)

    if policy_path is not None:
        policy.check(data_class, group, policy_path)
    else:
        policy.check(data_class, group)

    return ChatLiteLLM(model=group, **litellm_kwargs)
