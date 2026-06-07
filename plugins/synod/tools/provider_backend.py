#!/usr/bin/env python3
"""provider_backend.py — resolve a tier roster to a concrete provider backend.

Synod's model_matrix.json is authored against the **bridge** backend: the
Gemini lane runs through `agy-cli` (Antigravity Gemini 3.5 Flash) and the
OpenAI lane runs through `cliproxy-cli` (CLIProxyAPI). Those bridges are a
personal, time-limited convenience that expires ~2026-06-30.

The **durable** backend is `direct`: the official `gemini-3` and `openai-cli`
wrappers talking to the vendor APIs with the user's own keys. A direct roster
needs two rewrites per entry:

  1. ``cli``   — agy-cli → gemini-3, cliproxy-cli → openai-cli
  2. ``model`` — the bridge model string is translated to the equivalent
                 direct-CLI model key (e.g. ``3.5-flash`` → ``flash-latest``,
                 ``gpt55fast`` → ``gpt55``).

The model translation is intentionally *model-accurate* (not tier-accurate):
bridge ``3.5-flash`` maps to the stable ``flash-latest`` alias rather than a
preview pin, and the cliproxy ``gpt55fast`` fast variant maps to its closest
direct equivalent ``gpt55`` (= gpt-5.5).

Backend selection precedence:
  explicit argument  >  ``SYNOD_PROVIDER_BACKEND`` env  >  default ``bridge``.

An unknown backend value falls back to ``bridge`` with a stderr warning so a
typo never silently switches lanes during the cutover window.

Exit codes (CLI):
  0 — success
  2 — invalid backend or unreadable roster
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy

BRIDGE = "bridge"
DIRECT = "direct"
VALID_BACKENDS = {BRIDGE, DIRECT}

DEFAULT_BACKEND = BRIDGE
BACKEND_ENV = "SYNOD_PROVIDER_BACKEND"

# Per-provider CLI swap applied for the direct backend.
DIRECT_CLI = {
    "gemini": "gemini-3",
    "openai": "openai-cli",
}

# Per-provider model translation: bridge model string → direct-CLI model key.
# Keys must match the model strings authored in config/model_matrix.json.
# Values must be valid keys in the corresponding CLI's MODEL_MAP
# (gemini-3.py / openai-cli.py); cutover_check.py validates this invariant.
DIRECT_MODEL = {
    "gemini": {
        "3.5-flash": "flash-latest",  # stable alias, avoids preview EOL churn
        "flash": "flash-latest",
        "pro": "pro-latest",
    },
    "openai": {
        "gpt54mini": "gpt54mini",
        "gpt55fast": "gpt55",  # cliproxy fast variant → direct gpt-5.5
        "gpt55": "gpt55",
        "gpt54": "gpt54",
        "o3": "o3",
    },
}


class BackendResolutionError(ValueError):
    """Raised when a roster entry cannot be mapped to the requested backend."""


def get_backend(explicit: str | None = None) -> str:
    """Resolve the active backend.

    Precedence: explicit arg > SYNOD_PROVIDER_BACKEND env > DEFAULT_BACKEND.
    Unknown values warn and fall back to ``bridge`` so a typo can never silently
    flip lanes mid-cutover.
    """
    if explicit is not None and explicit != "":
        candidate = explicit
    else:
        candidate = os.environ.get(BACKEND_ENV, DEFAULT_BACKEND)

    candidate = candidate.strip().lower()
    if candidate not in VALID_BACKENDS:
        print(
            f"warning: unknown backend '{candidate}' (valid: {sorted(VALID_BACKENDS)}); "
            f"falling back to '{DEFAULT_BACKEND}'",
            file=sys.stderr,
        )
        return DEFAULT_BACKEND
    return candidate


def resolve_entry(entry: dict, backend: str) -> dict:
    """Return a copy of a single roster entry rewritten for ``backend``.

    ``bridge`` returns an unchanged copy. ``direct`` swaps the ``cli`` and
    translates ``model`` via DIRECT_MODEL. A model with no translation entry
    raises BackendResolutionError so gaps surface at cutover time instead of
    reaching a CLI that cannot parse the string.
    """
    out = deepcopy(entry)
    if backend == BRIDGE:
        return out

    if backend != DIRECT:
        raise BackendResolutionError(f"unsupported backend '{backend}'")

    provider = entry.get("provider")
    if provider not in DIRECT_CLI:
        raise BackendResolutionError(f"no direct CLI mapping for provider '{provider}'")
    out["cli"] = DIRECT_CLI[provider]

    model = entry.get("model")
    model_map = DIRECT_MODEL.get(provider, {})
    if model not in model_map:
        raise BackendResolutionError(
            f"no direct model mapping for {provider} model '{model}' (known: {sorted(model_map)})"
        )
    out["model"] = model_map[model]

    # Record provenance so downstream tooling/logs can see the rewrite.
    out["backend"] = DIRECT
    out["bridge_model"] = model
    return out


def resolve_roster(roster: list, backend: str) -> list:
    """Rewrite every entry of a tier roster for ``backend``."""
    return [resolve_entry(entry, backend) for entry in roster]


def translate_model(provider: str, model: str, backend: str) -> str:
    """Translate a single provider model string for ``backend``.

    Used by the /synod runtime (SKILL.md / phase1) to convert a bridge model
    string (e.g. ``3.5-flash``) to its direct-CLI equivalent (``flash-latest``)
    when SYNOD_PROVIDER_BACKEND=direct. ``bridge`` returns the model unchanged.
    Raises BackendResolutionError for an unmapped direct model.
    """
    if backend == BRIDGE:
        return model
    if backend != DIRECT:
        raise BackendResolutionError(f"unsupported backend '{backend}'")
    model_map = DIRECT_MODEL.get(provider, {})
    if model not in model_map:
        raise BackendResolutionError(
            f"no direct model mapping for {provider} model '{model}' (known: {sorted(model_map)})"
        )
    return model_map[model]


def direct_cli_for(provider: str) -> str:
    """Return the direct CLI name for a provider (gemini→gemini-3, openai→openai-cli)."""
    if provider not in DIRECT_CLI:
        raise BackendResolutionError(f"no direct CLI mapping for provider '{provider}'")
    return DIRECT_CLI[provider]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite a tier roster (JSON list of entries) for a provider backend."
    )
    parser.add_argument(
        "--backend",
        default=None,
        help=f"Provider backend: bridge|direct (default: ${BACKEND_ENV} or '{DEFAULT_BACKEND}')",
    )
    parser.add_argument(
        "--roster-json",
        metavar="PATH",
        help="Path to a JSON file holding a roster list (default: stdin)",
    )
    parser.add_argument(
        "--translate-model",
        metavar="MODEL",
        help="Translate a single model string for the backend and print it (with --provider)",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(DIRECT_CLI),
        help="Provider for --translate-model (gemini|openai)",
    )
    parser.add_argument(
        "--print-cli",
        action="store_true",
        help="With --provider, print the backend CLI name instead of a model",
    )
    args = parser.parse_args()

    backend = get_backend(args.backend)

    # Single-model translation mode (runtime helper for SKILL.md / phase1).
    if args.translate_model is not None or args.print_cli:
        if not args.provider:
            print("error: --provider required for --translate-model/--print-cli", file=sys.stderr)
            sys.exit(2)
        try:
            if args.print_cli:
                print(args.provider if backend == BRIDGE else direct_cli_for(args.provider))
            else:
                print(translate_model(args.provider, args.translate_model, backend))
        except BackendResolutionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(2)
        return

    try:
        if args.roster_json:
            with open(args.roster_json, encoding="utf-8") as f:
                roster = json.load(f)
        else:
            roster = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read roster: {exc}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(roster, list):
        print("error: roster must be a JSON list of entries", file=sys.stderr)
        sys.exit(2)

    try:
        resolved = resolve_roster(roster, backend)
    except BackendResolutionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps({"backend": backend, "models": resolved}, ensure_ascii=False))


if __name__ == "__main__":
    main()
