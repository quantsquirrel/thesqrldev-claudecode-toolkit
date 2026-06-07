"""Tests for tools/tier_matrix.py — v3.5 evidence-first critical-path code."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

_matrix_path = Path(__file__).parent.parent / "tools" / "tier_matrix.py"
_spec = importlib.util.spec_from_file_location("tier_matrix", _matrix_path)
_tier_matrix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tier_matrix)

load_matrix = _tier_matrix.load_matrix
resolve_tier = _tier_matrix.resolve_tier
VALID_TIERS = _tier_matrix.VALID_TIERS
DEFAULT_MATRIX = _tier_matrix.DEFAULT_MATRIX

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REAL_MATRIX = DEFAULT_MATRIX  # config/model_matrix.json


def _write_matrix(tmp_path, tiers: dict, async_threshold: int = 300) -> Path:
    """Write a minimal model_matrix.json to tmp_path and return its path."""
    data = {"tiers": tiers, "async_threshold_sec": async_threshold}
    p = tmp_path / "model_matrix.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# load_matrix
# ---------------------------------------------------------------------------


class TestLoadMatrix:
    def test_loads_valid_file(self, tmp_path):
        p = _write_matrix(tmp_path, {"standard": []})
        result = load_matrix(p)
        assert "tiers" in result

    def test_missing_file_exits_2(self, tmp_path):
        missing = tmp_path / "no_such_file.json"
        with pytest.raises(SystemExit) as exc:
            load_matrix(missing)
        assert exc.value.code == 2

    def test_invalid_json_exits_2(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(SystemExit) as exc:
            load_matrix(bad)
        assert exc.value.code == 2

    def test_loads_real_matrix(self):
        result = load_matrix(_REAL_MATRIX)
        assert "tiers" in result
        assert "standard" in result["tiers"]


# ---------------------------------------------------------------------------
# resolve_tier
# ---------------------------------------------------------------------------


class TestResolveTier:
    def test_explicit_tier_passthrough(self):
        """Non-auto tier is returned as-is, classifier_json is irrelevant."""
        assert resolve_tier("standard", None) == "standard"
        assert resolve_tier("deep", None) == "deep"
        assert resolve_tier("ultra", None) == "ultra"
        assert resolve_tier("simple", None) == "simple"

    def test_auto_without_classifier_json_returns_standard(self):
        assert resolve_tier("auto", None) == "standard"

    def test_auto_with_valid_tier_in_json(self, tmp_path):
        classifier_json = tmp_path / "classifier.json"
        classifier_json.write_text(json.dumps({"tier": "deep", "confidence": 0.9}))
        assert resolve_tier("auto", str(classifier_json)) == "deep"

    def test_auto_with_standard_tier_in_json(self, tmp_path):
        classifier_json = tmp_path / "classifier.json"
        classifier_json.write_text(json.dumps({"tier": "standard"}))
        assert resolve_tier("auto", str(classifier_json)) == "standard"

    def test_auto_with_invalid_tier_in_json_downgrades_to_standard(self, tmp_path):
        """An unrecognised tier value in the classifier JSON falls back to 'standard'."""
        classifier_json = tmp_path / "classifier.json"
        classifier_json.write_text(json.dumps({"tier": "bogus_tier_value"}))
        assert resolve_tier("auto", str(classifier_json)) == "standard"

    def test_auto_with_missing_classifier_file_returns_standard(self, tmp_path):
        missing = str(tmp_path / "no_file.json")
        assert resolve_tier("auto", missing) == "standard"

    def test_auto_with_malformed_classifier_json_returns_standard(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json}")
        assert resolve_tier("auto", str(bad)) == "standard"

    # ------------------------------------------------------------------
    # v3.1 alias: classifier emits 'fast', matrix normalises to 'simple'
    # ------------------------------------------------------------------

    def test_auto_with_fast_tier_resolves_to_simple_roster(self, tmp_path):
        """Classifier 'fast' (v3.1 vocabulary) must normalise to 'simple' via
        TIER_ALIASES, not silently downgrade to 'standard'.

        Fixed in v3.6.1: TIER_ALIASES = {'fast': 'simple'} applied in resolve_tier()
        before the VALID_TIERS check.
        """
        classifier_json = tmp_path / "classifier.json"
        classifier_json.write_text(json.dumps({"tier": "fast"}))
        result = resolve_tier("auto", str(classifier_json))
        assert result == "simple", f"expected 'simple', got '{result}'"
        assert result != "standard"

    def test_explicit_fast_arg_resolves_to_simple(self):
        """--tier fast on the CLI must also normalise to 'simple' via TIER_ALIASES."""
        assert resolve_tier("fast", None) == "simple"


# ---------------------------------------------------------------------------
# main() roster lookup against real config/model_matrix.json
# ---------------------------------------------------------------------------


class TestMainRosterLookup:
    """Tests for main() CLI behavior using real model_matrix.json."""

    def _run_main(self, args: list[str], capsys) -> dict:
        """Run tier_matrix.main() with given sys.argv, return parsed JSON stdout."""
        sys.argv = ["tier_matrix.py"] + args
        _tier_matrix.main()
        out = capsys.readouterr().out
        return json.loads(out)

    def test_standard_tier_returns_models_and_wall_time(self, capsys):
        result = self._run_main(["--tier", "standard"], capsys)
        assert result["tier"] == "standard"
        assert isinstance(result["models"], list)
        assert len(result["models"]) > 0
        assert "estimated_wall_time_sec" in result

    def test_deep_tier_returns_models(self, capsys):
        result = self._run_main(["--tier", "deep"], capsys)
        assert result["tier"] == "deep"
        assert isinstance(result["models"], list)
        assert len(result["models"]) > 0

    def test_ultra_tier_returns_models(self, capsys):
        result = self._run_main(["--tier", "ultra"], capsys)
        assert result["tier"] == "ultra"
        assert isinstance(result["models"], list)

    def test_simple_tier_returns_models(self, capsys):
        result = self._run_main(["--tier", "simple"], capsys)
        assert result["tier"] == "simple"
        assert isinstance(result["models"], list)

    def test_estimated_wall_time_is_max_timeout(self, capsys):
        """estimated_wall_time_sec equals the max timeout_sec of models in the tier."""
        result = self._run_main(["--tier", "standard"], capsys)
        matrix = load_matrix(_REAL_MATRIX)
        tier_map = matrix.get("tiers", matrix)
        expected_max = max(m.get("timeout_sec", 0) for m in tier_map["standard"])
        assert result["estimated_wall_time_sec"] == expected_max

    def test_requires_async_false_for_deep(self, capsys):
        """deep tier timeout_sec is 240s (< async_threshold_sec 300), so requires_async
        must be False after the v3.6.1 timeout alignment (was 600s, reduced to 240s to
        match synod-modes.yaml model:240 ceiling — smaller, safer ladder)."""
        result = self._run_main(["--tier", "deep"], capsys)
        assert result["requires_async"] is False

    def test_requires_async_false_for_simple(self, capsys):
        """simple tier has timeout < 300s, so requires_async must be False."""
        result = self._run_main(["--tier", "simple"], capsys)
        assert result["requires_async"] is False

    def test_invalid_tier_exits_2(self, capsys):
        sys.argv = ["tier_matrix.py", "--tier", "standard"]
        load_matrix(_REAL_MATRIX)
        # Use a custom matrix that lacks the 'standard' tier to trigger exit 2
        # by passing a minimal matrix file pointing to a tier not in it
        with pytest.raises(SystemExit) as exc:
            sys.argv = [
                "tier_matrix.py",
                "--tier",
                "standard",
                "--matrix",
                "/nonexistent/path.json",
            ]
            _tier_matrix.main()
        assert exc.value.code == 2

    def test_auto_tier_defaults_to_standard_without_classifier(self, capsys):
        """--tier auto without --classifier-json resolves to standard."""
        result = self._run_main(["--tier", "auto"], capsys)
        assert result["tier"] == "standard"

    def test_auto_tier_with_valid_classifier_json(self, tmp_path, capsys):
        """--tier auto with classifier JSON emitting 'deep' selects deep roster."""
        clf = tmp_path / "clf.json"
        clf.write_text(json.dumps({"tier": "deep"}))
        result = self._run_main(["--tier", "auto", "--classifier-json", str(clf)], capsys)
        assert result["tier"] == "deep"

    def test_auto_tier_with_fast_in_meta_json_selects_simple_roster(self, tmp_path, capsys):
        """--tier auto with meta.json carrying tier='fast' (v3.1 classifier output)
        must resolve to the 'simple' roster, not silently fall to 'standard'.

        This covers the full pipeline: meta.json tier='fast' → TIER_ALIASES → 'simple'
        → multi-provider simple roster from model_matrix.json.
        """
        meta = tmp_path / "meta.json"
        meta.write_text(json.dumps({"tier": "fast", "complexity": "simple"}))
        result = self._run_main(["--tier", "auto", "--classifier-json", str(meta)], capsys)
        assert result["tier"] == "simple", (
            f"expected tier='simple' from meta.json tier='fast', got '{result['tier']}'"
        )
        providers = {m["provider"] for m in result["models"]}
        assert "gemini" in providers, "simple roster must include gemini provider"
        assert "openai" in providers, "simple roster must include openai provider"
        assert result["requires_async"] is False, "simple tier must not require async"
