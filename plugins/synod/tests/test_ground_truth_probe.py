"""Tests for tools/ground_truth_probe.py — v3.5 evidence-first critical-path code."""

import importlib.util
from pathlib import Path

# ---------------------------------------------------------------------------
# Module import (module lives in tools/ with no __init__.py package structure)
# ---------------------------------------------------------------------------

_probe_path = Path(__file__).parent.parent / "tools" / "ground_truth_probe.py"
_spec = importlib.util.spec_from_file_location("ground_truth_probe", _probe_path)
_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_probe)

detect_lang = _probe.detect_lang
parse_pyproject = _probe.parse_pyproject
_parse_pyproject_regex = _probe._parse_pyproject_regex
compute_integrity = _probe.compute_integrity
compute_status = _probe.compute_status
run_version_pins = _probe.run_version_pins


# ---------------------------------------------------------------------------
# detect_lang
# ---------------------------------------------------------------------------


class TestDetectLang:
    def test_python_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        assert detect_lang(tmp_path) == "python"

    def test_python_setup_py(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
        assert detect_lang(tmp_path) == "python"

    def test_node_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "myapp", "version": "1.0.0"}')
        assert detect_lang(tmp_path) == "node"

    def test_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/hello\ngo 1.21\n")
        assert detect_lang(tmp_path) == "go"

    def test_rust_cargo_toml(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "hello"\n')
        assert detect_lang(tmp_path) == "rust"

    def test_unknown_empty_dir(self, tmp_path):
        assert detect_lang(tmp_path) == "unknown"

    def test_python_takes_priority_over_node_when_both(self, tmp_path):
        # pyproject.toml checked first in the function
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        (tmp_path / "package.json").write_text('{"name": "foo"}')
        assert detect_lang(tmp_path) == "python"


# ---------------------------------------------------------------------------
# parse_pyproject — regex fallback path
# ---------------------------------------------------------------------------


class TestParseProjectRegexFallback:
    """Tests for the _parse_pyproject_regex helper directly."""

    def test_extracts_name_and_version(self):
        text = '[project]\nname = "mylib"\nversion = "1.2.3"\n'
        result = _parse_pyproject_regex(text)
        assert result["name"] == "mylib"
        assert result["version"] == "1.2.3"

    def test_stops_at_next_section(self):
        text = '[project]\nname = "mylib"\n\n[build-system]\nname = "should-not-appear"\n'
        result = _parse_pyproject_regex(text)
        assert result["name"] == "mylib"
        assert "should-not-appear" not in result.values()

    def test_returns_empty_when_no_project_section(self):
        text = '[build-system]\nrequires = ["setuptools"]\n'
        result = _parse_pyproject_regex(text)
        assert result == {}

    def test_parse_pyproject_returns_empty_when_no_file(self, tmp_path):
        result = parse_pyproject(tmp_path)
        assert result == {}

    def test_parse_pyproject_reads_real_file(self, tmp_path):
        toml_text = '[project]\nname = "probe-test"\nversion = "0.1.0"\n'
        (tmp_path / "pyproject.toml").write_text(toml_text)
        result = parse_pyproject(tmp_path)
        assert result.get("name") == "probe-test"
        assert result.get("version") == "0.1.0"


# ---------------------------------------------------------------------------
# compute_integrity — scoring math
# ---------------------------------------------------------------------------


class TestComputeIntegrity:
    def _make_import_probe(self, can_import=True, attempts=None):
        return {
            "lang": "python",
            "attempts": attempts or [],
            "can_import_top_level": can_import,
        }

    def _make_test_collect(self, collected=5, errors=None):
        return {
            "runner": "pytest",
            "collected": collected,
            "errors": errors or [],
            "items_sample": [],
        }

    def _make_version_pins(self, consistency="ok", pyproject=None, changelog=None):
        return {
            "pyproject_toml": pyproject or "1.0.0",
            "package_json": None,
            "changelog_top": changelog or "1.0.0",
            "consistency": consistency,
        }

    def test_perfect_project_scores_10(self):
        ip = self._make_import_probe(can_import=True)
        tc = self._make_test_collect(collected=10)
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 10
        assert result["issues"] == []

    def test_import_failure_deducts_4(self):
        ip = self._make_import_probe(
            can_import=False,
            attempts=[{"module": "mylib", "result": "fail", "error": "ModuleNotFoundError"}],
        )
        tc = self._make_test_collect(collected=5)
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 6  # 10 - 4
        assert any(i["severity"] == "high" for i in result["issues"])

    def test_no_tests_deducts_2(self):
        ip = self._make_import_probe(can_import=True)
        tc = self._make_test_collect(collected=0)
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 8  # 10 - 2
        assert any(i["severity"] == "medium" for i in result["issues"])

    def test_version_mismatch_deducts_2(self):
        ip = self._make_import_probe(can_import=True)
        tc = self._make_test_collect(collected=5)
        vp = self._make_version_pins(consistency="mismatch", pyproject="1.0.0", changelog="2.0.0")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 8  # 10 - 2
        assert any(i["severity"] == "medium" for i in result["issues"])

    def test_collect_error_deducts_1(self):
        ip = self._make_import_probe(can_import=True)
        tc = self._make_test_collect(collected=5, errors=["ERROR collecting tests/broken.py"])
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 9  # 10 - 1
        assert any(i["severity"] == "low" for i in result["issues"])

    def test_score_floored_at_zero(self):
        ip = self._make_import_probe(
            can_import=False,
            attempts=[{"module": "x", "result": "fail", "error": "ImportError: no module"}],
        )
        tc = self._make_test_collect(collected=0, errors=["E1", "E2", "E3", "E4", "E5"])
        vp = self._make_version_pins(consistency="mismatch", pyproject="1.0.0", changelog="99.0.0")
        result = compute_integrity(ip, tc, vp)
        assert result["score"] == 0

    def test_no_import_attempts_adds_high_issue(self):
        ip = {"lang": "python", "attempts": [], "can_import_top_level": False}
        tc = self._make_test_collect(collected=5)
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        assert any("No importable" in i["msg"] for i in result["issues"])

    def test_combined_import_and_no_tests(self):
        ip = self._make_import_probe(
            can_import=False,
            attempts=[{"module": "x", "result": "fail", "error": "ImportError"}],
        )
        tc = self._make_test_collect(collected=0)
        vp = self._make_version_pins(consistency="ok")
        result = compute_integrity(ip, tc, vp)
        # high(-4) + medium(-2) = 4
        assert result["score"] == 4


# ---------------------------------------------------------------------------
# compute_status — broken / degraded / ok branches
# ---------------------------------------------------------------------------


class TestComputeStatus:
    def _base_integrity(self, issues=None, version_consistency="ok", test_count=5):
        return {
            "issues": issues or [],
            "version_consistency": version_consistency,
            "test_count": test_count,
            "score": 10,
            "can_run": True,
        }

    def test_broken_when_cannot_import(self):
        ip = {"can_import_top_level": False, "attempts": []}
        integrity = self._base_integrity(
            issues=[{"severity": "high", "msg": "Import failed: ModuleNotFoundError"}]
        )
        assert compute_status(ip, integrity) == "broken"

    def test_broken_when_high_severity_issue(self):
        ip = {"can_import_top_level": True, "attempts": []}
        integrity = self._base_integrity(
            issues=[{"severity": "high", "msg": "Some critical issue"}]
        )
        assert compute_status(ip, integrity) == "broken"

    def test_degraded_when_no_tests(self):
        ip = {"can_import_top_level": True, "attempts": []}
        integrity = self._base_integrity(issues=[], test_count=0)
        assert compute_status(ip, integrity) == "degraded"

    def test_degraded_when_version_mismatch(self):
        ip = {"can_import_top_level": True, "attempts": []}
        integrity = self._base_integrity(
            issues=[{"severity": "medium", "msg": "Version mismatch"}],
            version_consistency="mismatch",
            test_count=5,
        )
        assert compute_status(ip, integrity) == "degraded"

    def test_ok_when_all_good(self):
        ip = {"can_import_top_level": True, "attempts": []}
        integrity = self._base_integrity(issues=[], version_consistency="ok", test_count=10)
        assert compute_status(ip, integrity) == "ok"

    def test_ok_when_version_unknown_and_has_tests(self):
        # "unknown" is not "mismatch", so version_ok is True
        ip = {"can_import_top_level": True, "attempts": []}
        integrity = self._base_integrity(issues=[], version_consistency="unknown", test_count=5)
        assert compute_status(ip, integrity) == "ok"


# ---------------------------------------------------------------------------
# run_version_pins — consistency logic
# ---------------------------------------------------------------------------


class TestRunVersionPins:
    def test_ok_when_versions_match_exactly(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\nversion = "1.2.3"\n')
        (tmp_path / "CHANGELOG.md").write_text("# [1.2.3] - 2024-01-01\n\n- initial\n")
        result = run_version_pins(tmp_path, {"version": "1.2.3"})
        assert result["consistency"] == "ok"

    def test_ok_when_changelog_prefixes_match(self, tmp_path):
        # changelog "1.2.3-beta" starts with pyproject "1.2.3"
        (tmp_path / "CHANGELOG.md").write_text("# [1.2.3-beta] - 2024-01-01\n")
        result = run_version_pins(tmp_path, {"version": "1.2.3"})
        assert result["consistency"] == "ok"

    def test_mismatch_when_versions_differ(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("# [2.0.0] - 2024-01-01\n\n- new major\n")
        result = run_version_pins(tmp_path, {"version": "1.0.0"})
        assert result["consistency"] == "mismatch"

    def test_unknown_when_only_pyproject_version(self, tmp_path):
        # No changelog file
        result = run_version_pins(tmp_path, {"version": "1.0.0"})
        assert result["consistency"] == "unknown"

    def test_unknown_when_only_changelog(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("# [1.0.0] - 2024-01-01\n")
        result = run_version_pins(tmp_path, {})
        assert result["consistency"] == "unknown"

    def test_unknown_when_neither(self, tmp_path):
        result = run_version_pins(tmp_path, {})
        assert result["consistency"] == "unknown"

    def test_reads_package_json_version(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "foo", "version": "3.0.0"}')
        result = run_version_pins(tmp_path, {})
        assert result["package_json"] == "3.0.0"

    def test_v_prefix_stripped_for_comparison(self, tmp_path):
        # pyproject version without 'v', changelog with 'v'
        (tmp_path / "CHANGELOG.md").write_text("## v1.0.0 - 2024-01-01\n")
        result = run_version_pins(tmp_path, {"version": "1.0.0"})
        assert result["consistency"] == "ok"
