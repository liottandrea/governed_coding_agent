"""LiteLLM gateway — AWS Bedrock backend.

All model calls go through resolve_model(role, data_class) which:
  1. Looks up the model group for the role in routing-rules.yaml
  2. Enforces the data-class policy via policy.py
  3. Reads the actual Bedrock model ID + AWS params from litellm.config.yaml
  4. Returns a ChatLiteLLM instance with the resolved params

No provider SDK is imported directly — all calls go through LiteLLM.

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
_LITELLM_CONFIG = Path(os.getenv("LITELLM_CONFIG_PATH", "config/litellm.config.yaml"))

# Ensure the AWS profile is set for all litellm calls in this process.
os.environ.setdefault("AWS_PROFILE", os.getenv("AWS_PROFILE", "genai-agent-user"))


def _load_routing(path: Path = _ROUTING_CONFIG) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def _load_litellm_config(path: Path = _LITELLM_CONFIG) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def _litellm_params_for_group(
    group: str,
    litellm_config_path: Path = _LITELLM_CONFIG,
) -> dict[str, Any]:
    """Return the litellm_params dict for the named model group."""
    cfg = _load_litellm_config(litellm_config_path)
    for entry in cfg.get("model_list", []):
        if entry.get("model_name") == group:
            return dict(entry.get("litellm_params", {}))
    raise ValueError(
        f"Model group '{group}' not found in {litellm_config_path}. "
        f"Available groups: {[e['model_name'] for e in cfg.get('model_list', [])]}"
    )


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
    litellm_config_path: Path = _LITELLM_CONFIG,
    policy_path: Path | None = None,
    **extra_kwargs: Any,
) -> ChatLiteLLM:
    """Resolve role + data_class → policy-checked ChatLiteLLM instance.

    Reads the actual model ID and AWS params from litellm.config.yaml so
    LiteLLM receives a fully-qualified model string (e.g. bedrock/...).

    Raises policy.PolicyError if the combination is forbidden.
    """
    group = resolve_group(role, routing_path)

    if policy_path is not None:
        policy.check(data_class, group, policy_path)
    else:
        policy.check(data_class, group)

    params = _litellm_params_for_group(group, litellm_config_path)
    model_id: str = params.pop("model")

    # Strip env-reference syntax for api_base (used by private group)
    for key, val in list(params.items()):
        if isinstance(val, str) and val.startswith("os.environ/"):
            env_key = val.removeprefix("os.environ/")
            params[key] = os.environ.get(env_key, "")

    params.update(extra_kwargs)
    return ChatLiteLLM(model=model_id, model_kwargs=params)


# ── Embedding ────────────────────────────────────────────────────────────────

_EMBED_MODEL = "bedrock/amazon.titan-embed-text-v2:0"
_EMBED_AWS_PARAMS = {
    "aws_profile_name": "genai-agent-user",
    "aws_region_name": "us-east-1",
}
_EMBED_DIM = 1024


def embed(texts: list[str], data_class: str = "internal") -> list[list[float]]:
    """Embed a batch of texts via LiteLLM → Bedrock Titan Embed v2.

    Returns a list of 1024-dimensional float vectors, one per input text.
    Policy check: internal/public → Bedrock; restricted must use a local model
    (raises PolicyError if no local embedding model is configured yet).
    """
    import litellm

    if data_class == "restricted":
        raise policy.PolicyError(
            "Embedding for data_class='restricted' requires a local embedding "
            "model. Configure one in gateway.py before ingesting restricted data."
        )

    resp = litellm.embedding(
        model=_EMBED_MODEL,
        input=texts,
        **_EMBED_AWS_PARAMS,
    )
    return [item["embedding"] for item in resp.data]
