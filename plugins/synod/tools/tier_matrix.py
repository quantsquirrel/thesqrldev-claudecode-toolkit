#!/usr/bin/env python3
"""tier_matrix.py — maps a reasoning tier to a concrete model roster.

Exit codes:
  0 — success
  2 — invalid tier or unreadable matrix file
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VALID_TIERS = {"simple", "standard", "deep", "ultra"}
SCRIPT_DIR = Path(__file__).parent
# Plugin layout: plugins/synod/tools/tier_matrix.py  +  plugins/synod/config/model_matrix.json
DEFAULT_MATRIX = SCRIPT_DIR.parent / "config" / "model_matrix.json"


def load_matrix(matrix_path: Path) -> dict:
    try:
        with open(matrix_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read matrix file {matrix_path}: {exc}", file=sys.stderr)
        sys.exit(2)


def resolve_tier(tier_arg: str, classifier_json: Optional[str]) -> str:
    if tier_arg != "auto":
        return tier_arg

    if classifier_json is None:
        return "standard"

    try:
        with open(classifier_json, encoding="utf-8") as f:
            data = json.load(f)
        candidate = data.get("tier", "standard")
        return candidate if candidate in VALID_TIERS else "standard"
    except (OSError, json.JSONDecodeError):
        return "standard"


def main() -> None:
    parser = argparse.ArgumentParser(description="Map a reasoning tier to model roster.")
    parser.add_argument(
        "--tier",
        default="standard",
        choices=["auto", "simple", "standard", "deep", "ultra"],
        help="Reasoning tier (default: standard)",
    )
    parser.add_argument(
        "--classifier-json",
        metavar="PATH",
        help="Path to classifier output JSON (used when --tier auto)",
    )
    parser.add_argument(
        "--matrix",
        metavar="PATH",
        default=str(DEFAULT_MATRIX),
        help="Path to model_matrix.json (default: <plugin>/config/model_matrix.json)",
    )
    args = parser.parse_args()

    matrix = load_matrix(Path(args.matrix))

    # Support both flat schema (tier → list) and wrapped schema (tiers → {tier → list})
    tier_map: dict = matrix.get("tiers", matrix)
    async_threshold: int = matrix.get("async_threshold_sec", 300)

    tier = resolve_tier(args.tier, args.classifier_json)

    if tier not in tier_map:
        print(
            f"error: invalid tier '{tier}'. Valid tiers: {sorted(tier_map.keys())}", file=sys.stderr
        )
        sys.exit(2)

    models: list = tier_map[tier]
    max_timeout: int = max((m.get("timeout_sec", 0) for m in models), default=0)
    requires_async: bool = max_timeout >= async_threshold

    result = {
        "tier": tier,
        "models": models,
        "estimated_wall_time_sec": max_timeout,
        "requires_async": requires_async,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
