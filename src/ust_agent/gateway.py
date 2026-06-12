"""LiteLLM gateway — AWS Bedrock backend.

All model calls go through resolve_model(role, data_class) which:
  1. Looks up the model group for the role in routing-rules.yaml
  2. Enforces the data-class policy via policy.py
  3. Reads the actual Bedrock model ID + AWS params from litellm.config.yaml
  4. Returns a ChatLiteLLM instance with the resolved params

Routing cascade: if a role defines a fallback_group in routing-rules.yaml, the
returned model is wrapped with .with_fallbacks([fallback_model]) so that any
exception on the primary triggers a transparent retry on the fallback.

No provider SDK is imported directly — all calls go through LiteLLM.

Usage:
    chat_model = resolve_model("codegen", "internal")
    response = chat_model.invoke([HumanMessage(content="hello")])
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterator

import yaml
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_litellm import ChatLiteLLM

from ust_agent import policy

logger = logging.getLogger(__name__)


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


class CascadingChatModel(BaseChatModel):
    """BaseChatModel that tries a primary model and silently falls back on error.

    Returned by resolve_model() when a role defines fallback_group. It IS a
    BaseChatModel so deepagents accepts it unchanged via isinstance() check.
    bind_tools() returns primary.with_fallbacks([fallback]) — valid for use
    inside the LangGraph node where deepagents no longer type-checks.
    """

    primary: ChatLiteLLM
    fallback: ChatLiteLLM

    @property
    def _llm_type(self) -> str:
        return "cascading-litellm"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return self.primary._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
        except Exception as exc:
            logger.warning(
                "Primary model failed (%s: %s); cascading to fallback",
                type(exc).__name__,
                exc,
            )
            return self.fallback._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        try:
            yield from self.primary._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
        except Exception as exc:
            logger.warning(
                "Primary model stream failed (%s: %s); cascading to fallback",
                type(exc).__name__,
                exc,
            )
            yield from self.fallback._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )

    def bind_tools(self, tools: list, **kwargs: Any) -> Any:
        """Bind tools to both models and return a fallback-aware runnable."""
        bound_primary = self.primary.bind_tools(tools, **kwargs)
        bound_fallback = self.fallback.bind_tools(tools, **kwargs)
        return bound_primary.with_fallbacks([bound_fallback])


def resolve_group(role: str, routing_path: Path = _ROUTING_CONFIG) -> str:
    """Return the primary model group name for a given role."""
    routing = _load_routing(routing_path)
    roles: dict[str, Any] = routing.get("roles", {})
    if role not in roles:
        raise ValueError(
            f"Unknown role '{role}'. Known roles: {list(roles.keys())}"
        )
    return roles[role]["default_group"]


def resolve_fallback_group(
    role: str,
    routing_path: Path = _ROUTING_CONFIG,
) -> str | None:
    """Return the fallback model group for a role, or None if not defined."""
    routing = _load_routing(routing_path)
    return routing.get("roles", {}).get(role, {}).get("fallback_group")


def _build_chat_litellm(
    group: str,
    litellm_config_path: Path,
    **extra_kwargs: Any,
) -> ChatLiteLLM:
    """Construct a ChatLiteLLM from a resolved group name."""
    params = _litellm_params_for_group(group, litellm_config_path)
    model_id: str = params.pop("model")

    for key, val in list(params.items()):
        if isinstance(val, str) and val.startswith("os.environ/"):
            env_key = val.removeprefix("os.environ/")
            params[key] = os.environ.get(env_key, "")

    params.update(extra_kwargs)
    return ChatLiteLLM(model=model_id, model_kwargs=params)


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

    If the role defines a fallback_group in routing-rules.yaml and that group
    is allowed by policy, the returned model is wrapped with
    .with_fallbacks([fallback]) so exceptions on the primary are transparently
    retried on the fallback.

    Raises policy.PolicyError if the primary combination is forbidden.
    """
    group = resolve_group(role, routing_path)

    if policy_path is not None:
        policy.check(data_class, group, policy_path)
    else:
        policy.check(data_class, group)

    primary = _build_chat_litellm(group, litellm_config_path, **extra_kwargs)

    fallback_group = resolve_fallback_group(role, routing_path)
    if fallback_group and fallback_group != group:
        try:
            if policy_path is not None:
                policy.check(data_class, fallback_group, policy_path)
            else:
                policy.check(data_class, fallback_group)
            fallback = _build_chat_litellm(
                fallback_group, litellm_config_path, **extra_kwargs
            )
            return CascadingChatModel(primary=primary, fallback=fallback)
        except policy.PolicyError:
            # Fallback group is not allowed for this data class — use primary only.
            pass

    return primary


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
