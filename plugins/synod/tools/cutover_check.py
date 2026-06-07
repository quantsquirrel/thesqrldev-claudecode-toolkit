#!/usr/bin/env python3
"""cutover_check.py — offline readiness gate for the bridge→direct cutover.

Run this BEFORE flipping ``SYNOD_PROVIDER_BACKEND=direct`` (or removing the
agy/cliproxy bridges). It verifies, without making any network call, that the
direct backend can serve every tier:

  1. Roster resolution — every entry in config/model_matrix.json maps cleanly
     to the direct backend via provider_backend.resolve_roster (no unmapped
     model/provider).
  2. Model validity   — each resolved direct model is a real key in the target
     CLI's MODEL_MAP AND an accepted ``--model`` argparse choice. The CLIs are
     AST-parsed (not imported) so missing google-genai/openai packages don't
     break the check.
  3. CLI presence     — gemini-3.py and openai-cli.py exist on disk.
  4. API-key preflight — GEMINI_API_KEY (or GOOGLE_API_KEY) and OPENAI_API_KEY
     are set. Reported as a check; only fails the run under --require-keys
     (keys are a runtime concern, the other checks are structural).

Exit codes:
  0 — ready (all structural checks pass; keys per --require-keys)
  1 — not ready (one or more checks failed)
  2 — internal error (cannot read matrix / CLI sources)
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
import provider_backend  # noqa: E402

DEFAULT_MATRIX = SCRIPT_DIR.parent / "config" / "model_matrix.json"

# Direct CLI source files keyed by provider (AST-parsed, never imported).
DIRECT_CLI_SOURCE = {
    "gemini": ("gemini-3.py", "GeminiProvider"),
    "openai": ("openai-cli.py", "OpenAIProvider"),
}

# Env var(s) that satisfy each provider's direct API-key requirement.
PROVIDER_KEY_ENVS = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}


def _fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def _module_ast(filename: str) -> ast.Module:
    path = SCRIPT_DIR / filename
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except OSError as exc:
        _fail(f"cannot read CLI source {path}: {exc}")


def _model_map(tree: ast.Module, class_name: str) -> dict:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "MODEL_MAP":
                            return ast.literal_eval(stmt.value)
    _fail(f"{class_name}.MODEL_MAP not found")


def _model_choices(tree: ast.Module) -> set:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_argument":
            flags = {a.value for a in node.args if isinstance(a, ast.Constant)}
            if "--model" in flags or "-m" in flags:
                for kw in node.keywords:
                    if kw.arg == "choices":
                        return set(ast.literal_eval(kw.value))
    return set()


def load_matrix(matrix_path: Path) -> dict:
    try:
        return json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read matrix {matrix_path}: {exc}")


def run_checks(matrix_path: Path, backend: str, require_keys: bool) -> dict:
    matrix = load_matrix(matrix_path)
    tiers = matrix.get("tiers", matrix)
    checks: list[dict] = []

    # Pre-parse CLI sources once.
    cli_maps: dict[str, dict] = {}
    cli_choices: dict[str, set] = {}
    cli_present: dict[str, bool] = {}
    for provider, (filename, class_name) in DIRECT_CLI_SOURCE.items():
        present = (SCRIPT_DIR / filename).is_file()
        cli_present[provider] = present
        checks.append(
            {
                "check": f"cli_present:{filename}",
                "ok": present,
                "detail": str(SCRIPT_DIR / filename),
            }
        )
        if present:
            tree = _module_ast(filename)
            cli_maps[provider] = _model_map(tree, class_name)
            cli_choices[provider] = _model_choices(tree)

    # Per-tier roster resolution + model validity.
    for tier, roster in tiers.items():
        try:
            resolved = provider_backend.resolve_roster(roster, backend)
        except provider_backend.BackendResolutionError as exc:
            checks.append({"check": f"resolve:{tier}", "ok": False, "detail": str(exc)})
            continue
        checks.append(
            {"check": f"resolve:{tier}", "ok": True, "detail": f"{len(resolved)} entries"}
        )

        if backend != provider_backend.DIRECT:
            continue  # model-map validity only meaningful for the direct target

        for entry in resolved:
            provider = entry.get("provider")
            model = entry.get("model")
            if provider not in cli_maps:
                checks.append(
                    {
                        "check": f"model:{tier}:{provider}:{model}",
                        "ok": False,
                        "detail": f"no CLI source for provider '{provider}'",
                    }
                )
                continue
            in_map = model in cli_maps[provider]
            in_choices = (not cli_choices[provider]) or (model in cli_choices[provider])
            ok = in_map and in_choices
            detail = "valid"
            if not in_map:
                detail = f"'{model}' not in {provider} MODEL_MAP"
            elif not in_choices:
                detail = f"'{model}' not an accepted --model choice"
            checks.append({"check": f"model:{tier}:{provider}:{model}", "ok": ok, "detail": detail})

    # API-key preflight (structural-independent).
    for provider, envs in PROVIDER_KEY_ENVS.items():
        present = any(os.environ.get(e) for e in envs)
        checks.append(
            {
                "check": f"api_key:{provider}",
                "ok": present if require_keys else True,
                "detail": (
                    f"set ({'/'.join(envs)})" if present else f"MISSING ({' or '.join(envs)})"
                ),
                "advisory": (not present) and (not require_keys),
            }
        )

    ready = all(c["ok"] for c in checks)
    return {"backend": backend, "ready": ready, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline readiness gate for the bridge→direct provider cutover."
    )
    parser.add_argument(
        "--backend",
        default=provider_backend.DIRECT,
        help=f"Target backend to validate (default: {provider_backend.DIRECT})",
    )
    parser.add_argument(
        "--matrix",
        default=str(DEFAULT_MATRIX),
        help="Path to model_matrix.json",
    )
    parser.add_argument(
        "--require-keys",
        action="store_true",
        help="Fail the run when an API key is missing (default: keys are advisory)",
    )
    parser.add_argument("--json", action="store_true", help="Emit the report as JSON")
    args = parser.parse_args()

    report = run_checks(Path(args.matrix), args.backend, args.require_keys)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"cutover readiness — backend={report['backend']}")
        for c in report["checks"]:
            mark = "✓" if c["ok"] else ("•" if c.get("advisory") else "✗")
            print(f"  {mark} {c['check']}: {c['detail']}")
        print(f"\n{'READY' if report['ready'] else 'NOT READY'}")

    sys.exit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
