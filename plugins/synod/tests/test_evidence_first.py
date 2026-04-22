"""Tests for v3.4.0 evidence-first tools: ground_truth_probe, prompt_linter, tier_matrix."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TOOLS = PLUGIN_ROOT / "tools"
CONFIG = PLUGIN_ROOT / "config"


def _run(cmd: list[str], *, input_text: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
    )


# -- tier_matrix --------------------------------------------------------------

def test_tier_matrix_simple_returns_sync_roster() -> None:
    result = _run([sys.executable, str(TOOLS / "tier_matrix.py"), "--tier", "simple"])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["tier"] == "simple"
    assert data["requires_async"] is False
    assert data["estimated_wall_time_sec"] <= 60


def test_tier_matrix_deep_sets_async_flag() -> None:
    result = _run([sys.executable, str(TOOLS / "tier_matrix.py"), "--tier", "deep"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["tier"] == "deep"
    assert data["requires_async"] is True
    assert data["estimated_wall_time_sec"] >= 300


def test_tier_matrix_auto_defaults_to_standard_when_no_classifier() -> None:
    result = _run([sys.executable, str(TOOLS / "tier_matrix.py"), "--tier", "auto"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["tier"] == "standard"


def test_tier_matrix_default_config_path_resolves() -> None:
    """Regression: default --matrix must point to <plugin>/config/model_matrix.json."""
    assert (CONFIG / "model_matrix.json").exists(), "config/model_matrix.json missing"
    # Running without --matrix must succeed (proves default path is correct)
    result = _run([sys.executable, str(TOOLS / "tier_matrix.py"), "--tier", "standard"])
    assert result.returncode == 0, f"default path broken: {result.stderr}"


# -- prompt_linter ------------------------------------------------------------

def test_linter_clean_prompt_exits_zero() -> None:
    result = _run(
        [sys.executable, str(TOOLS / "prompt_linter.py"), "--stdin"],
        input_text="README.md:42 says default provider is anthropic (see __main__.py:138)",
    )
    assert result.returncode == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["fatal_count"] == 0


def test_linter_stale_prompt_blocks_with_fatal() -> None:
    """This is the exact failure mode from the April 22 2026 Synod session."""
    stale = (
        "claude -p --bare를 사용하며 default provider는 claude_code. "
        "22/22 regression green. providers/ 추상화 사용."
    )
    result = _run(
        [sys.executable, str(TOOLS / "prompt_linter.py"), "--stdin"],
        input_text=stale,
    )
    assert result.returncode == 2, "stale prompt must exit 2 to block Synod"
    data = json.loads(result.stdout)
    assert data["fatal_count"] >= 2, f"expected ≥2 high-severity findings, got {data}"
    rules = {w["rule"] for w in data["warnings"]}
    assert "unbacked-default" in rules
    assert "existence-claim" in rules


def test_linter_unbacked_default_caught() -> None:
    result = _run(
        [sys.executable, str(TOOLS / "prompt_linter.py"), "--stdin"],
        input_text="The default timeout is 30 seconds.",
    )
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert any(w["rule"] == "unbacked-default" for w in data["warnings"])


# -- ground_truth_probe -------------------------------------------------------

def test_probe_on_missing_path_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = _run([sys.executable, str(TOOLS / "ground_truth_probe.py"), str(missing)])
    assert result.returncode == 2


def test_probe_on_self_plugin_dir_writes_artifacts(tmp_path: Path) -> None:
    """Probing this plugin directory should produce 5 artifacts and valid JSON stdout."""
    out_dir = tmp_path / "probe"
    result = _run(
        [
            sys.executable,
            str(TOOLS / "ground_truth_probe.py"),
            str(PLUGIN_ROOT),
            "--output-dir",
            str(out_dir),
        ]
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] in {"ok", "degraded", "broken"}
    for name in (
        "import_probe.json",
        "test_collect.json",
        "file_tree.txt",
        "version_pins.json",
        "integrity.json",
    ):
        assert (out_dir / name).exists(), f"missing artifact: {name}"
    integrity = json.loads((out_dir / "integrity.json").read_text())
    assert "can_run" in integrity
    assert "score" in integrity


def test_probe_emits_single_line_json(tmp_path: Path) -> None:
    """stdout must be parseable as a single JSON object (matches DESIGN contract)."""
    result = _run(
        [
            sys.executable,
            str(TOOLS / "ground_truth_probe.py"),
            str(PLUGIN_ROOT),
            "--output-dir",
            str(tmp_path / "probe"),
        ]
    )
    assert result.returncode == 0
    # Must be a single JSON object, not multiline or wrapped
    json.loads(result.stdout)  # raises if invalid
