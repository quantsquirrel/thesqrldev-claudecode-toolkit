"""Synod mode configuration loader.

Loads mode definitions from config/synod-modes.yaml.
Provides typed access to mode parameters.
"""

import os
import yaml
from typing import Any, Optional


_CONFIG_CACHE: Optional[dict] = None


def _find_config_path() -> str:
    """Find synod-modes.yaml relative to this file."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(tools_dir)
    return os.path.join(project_root, "config", "synod-modes.yaml")


def _find_templates_path() -> str:
    """Find synod-templates.yaml relative to this file."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(tools_dir)
    return os.path.join(project_root, "config", "synod-templates.yaml")


def load_config(force_reload: bool = False) -> dict:
    """Load and cache the synod modes configuration."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return _CONFIG_CACHE

    config_path = _find_config_path()
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r") as f:
        _CONFIG_CACHE = yaml.safe_load(f)

    return _CONFIG_CACHE


def get_mode_config(mode: str) -> dict:
    """Get configuration for a specific mode."""
    config = load_config()
    modes = config.get("modes", {})
    if mode not in modes:
        return modes.get("general", {})
    return modes[mode]


def get_model_config(mode: str, provider: str) -> dict:
    """Get model configuration for a mode and provider."""
    mode_config = get_mode_config(mode)
    return mode_config.get("models", {}).get(provider, {})


def get_focus(mode: str, provider: str) -> str:
    """Get focus area for a mode and provider."""
    mode_config = get_mode_config(mode)
    return mode_config.get("focus", {}).get(provider, "")


def get_rounds(mode: str) -> dict:
    """Get round configuration for a mode."""
    mode_config = get_mode_config(mode)
    return mode_config.get("rounds", {"base": 3, "dynamic_range": [2, 4]})


def get_complexity_rounds(score: float) -> int:
    """Get number of rounds based on complexity score."""
    config = load_config()
    complexity = config.get("complexity", {})

    if score < complexity.get("simple", {}).get("max_score", 0.5):
        return complexity.get("simple", {}).get("rounds", 2)
    elif score < complexity.get("medium", {}).get("max_score", 2.0):
        return complexity.get("medium", {}).get("rounds", 3)
    else:
        return complexity.get("complex", {}).get("rounds", 4)


def list_modes() -> list[str]:
    """List all available mode names."""
    config = load_config()
    return list(config.get("modes", {}).keys())


def get_timeouts() -> dict:
    """Get timeout configuration."""
    config = load_config()
    return config.get("timeouts", {"model": 110, "outer": 120})


def get_all_keywords() -> dict[str, list[str]]:
    """Get all classifier keyword patterns."""
    config = load_config()
    return config.get("keywords", {})


def get_threshold(name: str, default: float = 0) -> float:
    """Get a named threshold value."""
    config = load_config()
    return config.get("thresholds", {}).get(name, default)


def get_tier(complexity: str) -> str:
    """Map complexity level to model tier.

    Args:
        complexity: Complexity level (simple, medium, complex)

    Returns:
        Tier name (fast, standard, deep). Defaults to 'standard'.
    """
    config = load_config()
    mapping = config.get("tier_mapping", {})
    return mapping.get(complexity, "standard")


def get_tier_config(tier: str) -> dict:
    """Get configuration for a specific tier.

    Args:
        tier: Tier name (fast, standard, deep)

    Returns:
        Tier config dict, or empty dict if tier not found.
    """
    config = load_config()
    tiers = config.get("tiers", {})
    return tiers.get(tier, {})


def get_tiered_model_config(mode: str, provider: str, tier: Optional[str] = None) -> dict:
    """Get model config with tier override applied.

    When tier is None or 'standard', returns the original mode config.
    For other tiers, merges tier config over mode config.

    Args:
        mode: Synod mode (review, design, debug, idea, general)
        provider: Model provider (gemini, openai)
        tier: Optional tier name (fast, standard, deep)

    Returns:
        Model config dict with tier overrides applied.
    """
    base = get_model_config(mode, provider)
    if tier is None or tier == "standard":
        return base

    tier_cfg = get_tier_config(tier)
    provider_override = tier_cfg.get(provider, {})
    if not provider_override:
        return base

    merged = dict(base)
    merged.update(provider_override)
    return merged


def list_tiers() -> list[str]:
    """List all available tier names."""
    config = load_config()
    return list(config.get("tiers", {}).keys())


def get_template(mode: str) -> str:
    """Get output template for a mode from synod-templates.yaml.

    Args:
        mode: Mode name (review, design, debug, idea, general)

    Returns:
        Template string, or empty string if not found
    """
    templates_path = _find_templates_path()
    if not os.path.exists(templates_path):
        return ""

    try:
        with open(templates_path, "r") as f:
            templates_config = yaml.safe_load(f)
        return templates_config.get("templates", {}).get(mode, "")
    except Exception:
        return ""


def main():
    """CLI interface for shell script access to config values."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Query synod configuration")
    parser.add_argument("path", nargs="+",
                        help="Config path segments (e.g. 'timeouts model')")
    args = parser.parse_args()

    try:
        config = load_config()
    except FileNotFoundError:
        print("Error: config not found", file=sys.stderr)
        sys.exit(1)

    result = config
    for key in args.path:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            result = None
            break

    if result is None:
        sys.exit(1)

    if isinstance(result, (dict, list)):
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result)


if __name__ == "__main__":
    main()
