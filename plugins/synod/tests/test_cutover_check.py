"""Tests for tools/cutover_check.py — offline cutover readiness gate."""

import importlib.util
import json
from pathlib import Path

import pytest

_cc_path = Path(__file__).parent.parent / "tools" / "cutover_check.py"
_spec = importlib.util.spec_from_file_location("cutover_check", _cc_path)
cutover_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cutover_check)

REAL_MATRIX = Path(__file__).parent.parent / "config" / "model_matrix.json"


def _checks_by_name(report):
    return {c["check"]: c for c in report["checks"]}


class TestRealMatrixDirect:
    def test_real_matrix_is_structurally_ready_direct(self, monkeypatch):
        """Every tier of the shipped matrix must resolve+validate against the
        direct CLIs. Keys advisory → structural readiness independent of env."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        report = cutover_check.run_checks(REAL_MATRIX, "direct", require_keys=False)
        assert report["ready"] is True, [c for c in report["checks"] if not c["ok"]]

    def test_missing_keys_advisory_without_require(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        report = cutover_check.run_checks(REAL_MATRIX, "direct", require_keys=False)
        ck = _checks_by_name(report)
        assert ck["api_key:openai"]["ok"] is True
        assert ck["api_key:openai"]["advisory"] is True

    def test_missing_keys_fail_under_require(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        report = cutover_check.run_checks(REAL_MATRIX, "direct", require_keys=True)
        assert report["ready"] is False
        ck = _checks_by_name(report)
        assert ck["api_key:openai"]["ok"] is False
        assert ck["api_key:gemini"]["ok"] is False

    def test_keys_present_pass_under_require(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("GEMINI_API_KEY", "g-test")
        report = cutover_check.run_checks(REAL_MATRIX, "direct", require_keys=True)
        ck = _checks_by_name(report)
        assert ck["api_key:openai"]["ok"] is True
        assert ck["api_key:gemini"]["ok"] is True

    def test_google_api_key_satisfies_gemini(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "g-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        report = cutover_check.run_checks(REAL_MATRIX, "direct", require_keys=True)
        ck = _checks_by_name(report)
        assert ck["api_key:gemini"]["ok"] is True


class TestBridgeBackend:
    def test_bridge_skips_model_map_validity(self, monkeypatch):
        """Bridge backend only resolves rosters (identity); no direct-CLI model
        validity checks are emitted."""
        report = cutover_check.run_checks(REAL_MATRIX, "bridge", require_keys=False)
        model_checks = [c for c in report["checks"] if c["check"].startswith("model:")]
        assert model_checks == []
        # resolve checks still present and ok
        resolves = [c for c in report["checks"] if c["check"].startswith("resolve:")]
        assert resolves and all(c["ok"] for c in resolves)


class TestUnmappableMatrix:
    def test_unmapped_model_makes_not_ready(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("GEMINI_API_KEY", "g-test")
        bad = {
            "tiers": {
                "standard": [{"provider": "openai", "cli": "cliproxy-cli", "model": "ghost-model"}]
            }
        }
        p = tmp_path / "bad_matrix.json"
        p.write_text(json.dumps(bad))
        report = cutover_check.run_checks(p, "direct", require_keys=False)
        assert report["ready"] is False
        ck = _checks_by_name(report)
        assert ck["resolve:standard"]["ok"] is False


class TestMainExitCodes:
    def _run(self, argv, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "argv", ["cutover_check.py"] + argv)
        with pytest.raises(SystemExit) as exc:
            cutover_check.main()
        return exc.value.code

    def test_main_ready_exits_0(self, monkeypatch, capsys):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        code = self._run(["--matrix", str(REAL_MATRIX)], monkeypatch)
        assert code == 0

    def test_main_json_output(self, monkeypatch, capsys):
        code = self._run(["--matrix", str(REAL_MATRIX), "--json"], monkeypatch)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["backend"] == "direct"
        assert "checks" in data
        assert code == 0

    def test_main_require_keys_without_keys_exits_1(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        code = self._run(["--matrix", str(REAL_MATRIX), "--require-keys"], monkeypatch)
        assert code == 1
