"""Phase 1: gateway routing and observability unit tests (no live calls)."""
from __future__ import annotations

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
ROOT = Path(__file__).parent.parent


def test_litellm_params_resolve_frontier() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import _litellm_params_for_group
    params = _litellm_params_for_group("frontier")
    assert params["model"] == "bedrock/us.anthropic.claude-sonnet-4-6"
    assert params["aws_profile_name"] == "genai-agent-user"


def test_litellm_params_resolve_cheap() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import _litellm_params_for_group
    params = _litellm_params_for_group("cheap")
    assert "haiku" in params["model"].lower()


def test_litellm_params_unknown_group_raises() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import _litellm_params_for_group
    with pytest.raises(ValueError, match="not found"):
        _litellm_params_for_group("does_not_exist")


def test_resolve_model_uses_full_bedrock_id() -> None:
    os.chdir(ROOT)
    from ust_agent.gateway import resolve_model
    model = resolve_model("codegen", "internal")
    assert model.model.startswith("bedrock/us.anthropic.")


_LOCAL_GROUPS = {"private", "local_fast", "local_standard", "local_heavy"}


def test_all_roles_resolve_to_known_group() -> None:
    """Every role in routing-rules.yaml must map to a group in litellm.config.yaml."""
    os.chdir(ROOT)
    import yaml
    from ust_agent.gateway import _litellm_params_for_group

    with open("config/routing-rules.yaml") as f:
        routing = yaml.safe_load(f)

    for role, cfg in routing["roles"].items():
        group = cfg["default_group"]
        if group in _LOCAL_GROUPS:
            continue  # local groups need Ollama running, skip in CI
        params = _litellm_params_for_group(group)
        assert params["model"].startswith("bedrock/"), (
            f"Role '{role}' → group '{group}' → model '{params['model']}' "
            "does not start with 'bedrock/'"
        )


def test_local_groups_exist_in_litellm_config() -> None:
    """local_fast, local_standard, local_heavy must all be in litellm config."""
    os.chdir(ROOT)
    from ust_agent.gateway import _litellm_params_for_group
    for group in ("local_fast", "local_standard", "local_heavy"):
        params = _litellm_params_for_group(group)
        assert params["model"].startswith("ollama/"), (
            f"Expected ollama/ model for {group}, got {params['model']!r}"
        )
        assert params["api_base"] == "http://localhost:11434"


def test_restricted_class_allows_local_groups() -> None:
    """restricted data class must permit all local_* groups."""
    os.chdir(ROOT)
    from ust_agent.policy import check
    for group in ("local_fast", "local_standard", "local_heavy"):
        check("restricted", group)  # must not raise


def test_observability_configure_no_keys_is_safe() -> None:
    """configure() must not crash when keys are absent."""
    os.chdir(ROOT)
    # Reset the module-level flag
    import ust_agent.observability as obs
    obs._configured = False
    with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}, clear=False):
        obs.configure()  # should warn but not raise
    obs._configured = False  # reset for other tests


def test_observability_configure_registers_langfuse_callback() -> None:
    """With keys set, configure() adds 'langfuse' to litellm callbacks."""
    os.chdir(ROOT)
    import ust_agent.observability as obs
    import litellm

    obs._configured = False
    original_success = list(litellm.success_callback)
    original_failure = list(litellm.failure_callback)

    with patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "LANGFUSE_HOST": "http://localhost:13000",
    }):
        obs.configure()

    assert "langfuse" in litellm.success_callback
    assert "langfuse" in litellm.failure_callback

    # cleanup
    obs._configured = False
    litellm.success_callback = original_success
    litellm.failure_callback = original_failure
