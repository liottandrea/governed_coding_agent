"""Data-class policy enforcement.

Loads data-classes.yaml and provides a single guard that raises PolicyError
when a (data_class, model_group) combination is not permitted.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class PolicyError(Exception):
    """Raised when a routing decision violates the data-class policy."""


_AGENT_HOME = Path(os.getenv("GOVERNED_AGENT_HOME", Path(__file__).parent.parent.parent))
_CONFIG_PATH = _AGENT_HOME / "config" / "data-classes.yaml"


def _load_policy(path: Path = _CONFIG_PATH) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def check(data_class: str, model_group: str, config_path: Path = _CONFIG_PATH) -> None:
    """Raise PolicyError if data_class is not allowed to use model_group."""
    policy = _load_policy(config_path)
    classes: dict[str, Any] = policy.get("classes", {})

    if data_class not in classes:
        raise PolicyError(
            f"Unknown data class '{data_class}'. "
            f"Valid classes: {list(classes.keys())}"
        )

    allowed: list[str] = classes[data_class].get("allowed_groups", [])
    if model_group not in allowed:
        raise PolicyError(
            f"Data class '{data_class}' is not permitted to use model group "
            f"'{model_group}'. Allowed groups: {allowed}"
        )
