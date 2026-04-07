"""
Hierarchical config loader.

Resolution order (later entries win):
  1. base config.yml  (repo root)
  2. pipeline/config.yml  (pipeline-specific overrides)

Only keys that exist in the pipeline config override the base.
Keys not mentioned in the pipeline config are inherited from base.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


# Repo root = parent of this file's directory
_ROOT = Path(__file__).parent
_BASE_CONFIG = _ROOT / "config.yml"
_PIPELINE_CONFIG = _ROOT / "pipeline" / "config.yml"


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base.
    - Dicts are merged recursively (override wins on scalar conflicts).
    - Non-dict values in override replace base values entirely.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _expand_paths(obj: Any) -> Any:
    """Recursively expand ~ in any string values."""
    if isinstance(obj, dict):
        return {k: _expand_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_paths(i) for i in obj]
    if isinstance(obj, str) and obj.startswith("~"):
        return os.path.expanduser(obj)
    return obj


def load_config(
    base_path: Path = _BASE_CONFIG,
    pipeline_path: Path = _PIPELINE_CONFIG,
) -> dict:
    """
    Load and merge base + pipeline configs.

    Returns a plain dict with all ~ paths expanded.
    Raises FileNotFoundError if base config is missing.
    """
    if not base_path.exists():
        raise FileNotFoundError(f"Base config not found: {base_path}")

    with open(base_path) as f:
        base = yaml.safe_load(f) or {}

    pipeline = {}
    if pipeline_path.exists():
        with open(pipeline_path) as f:
            pipeline = yaml.safe_load(f) or {}

    merged = _deep_merge(base, pipeline)
    return _expand_paths(merged)


def get(key_path: str, default: Any = None) -> Any:
    """
    Convenience accessor using dot-notation.

    Example:
        get("transcribe.model")       -> "medium.en"
        get("paths.vault_output")     -> "/home/user/..."
        get("chroma.chunk_size")      -> 750
    """
    cfg = load_config()
    keys = key_path.split(".")
    node = cfg
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


if __name__ == "__main__":
    # Quick sanity check: python -m pipeline.config
    import json
    print(json.dumps(load_config(), indent=2, default=str))
