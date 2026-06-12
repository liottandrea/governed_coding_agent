"""Phase 0: import and policy smoke tests (no live API calls)."""
from __future__ import annotations

import sys
import os
import pytest
from pathlib import Path

# Allow running from repo root without packaging
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

ROOT = Path(__file__).parent.parent


def test_deepagents_importable() -> None:
    import deepagents
    assert deepagents.__version__ == "0.6.8"


def test_langgraph_importable() -> None:
    import importlib.metadata
    import langgraph  # noqa: F401 — confirm importable
    version = importlib.metadata.version("langgraph")
    assert version == "1.2.4"


def test_gateway_resolve_group() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import resolve_group
    group = resolve_group("codegen")
    assert group == "frontier"


def test_gateway_resolve_group_unknown_role() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import resolve_group
    with pytest.raises(ValueError, match="Unknown role"):
        resolve_group("nonexistent_role")


def test_policy_allows_valid_combination() -> None:
    os.chdir(ROOT)
    from ust_agent.policy import check
    # internal + frontier should be allowed
    check("internal", "frontier")


def test_policy_blocks_restricted_to_frontier() -> None:
    os.chdir(ROOT)
    from ust_agent.policy import check, PolicyError
    with pytest.raises(PolicyError):
        check("restricted", "frontier")


def test_policy_blocks_unknown_class() -> None:
    os.chdir(ROOT)
    from ust_agent.policy import check, PolicyError
    with pytest.raises(PolicyError, match="Unknown data class"):
        check("top_secret", "cheap")


def test_resolve_model_returns_chat_litellm() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import resolve_model
    from langchain_litellm import ChatLiteLLM
    model = resolve_model("codegen", "internal")
    assert isinstance(model, ChatLiteLLM)
    # model.model should be the fully-qualified Bedrock ID, not the group alias
    assert model.model.startswith("bedrock/"), (
        f"Expected bedrock/ model ID, got: {model.model!r}"
    )


def test_resolve_model_restricted_raises_policy_error() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import resolve_model
    from ust_agent.policy import PolicyError
    with pytest.raises(PolicyError):
        resolve_model("codegen", "restricted")
