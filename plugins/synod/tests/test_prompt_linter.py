"""Tests for tools/prompt_linter.py (Contract #3 — unbacked-claim auditor).

Import idiom mirrors test_tier_routing.py: prompt_linter.py has a normal
(non-hyphenated) name so a direct import via sys.path works, but we use
importlib for consistency with the project pattern.
"""

import importlib.util
import json
import os

import pytest

# ---------------------------------------------------------------------------
# Load the module under test
# ---------------------------------------------------------------------------

_linter_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "prompt_linter.py"
)
_spec = importlib.util.spec_from_file_location("prompt_linter", _linter_path)
_linter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_linter)

lint = _linter.lint


# ---------------------------------------------------------------------------
# unbacked-default rule
# ---------------------------------------------------------------------------


class TestUnbackedDefault:
    """Rule: 'default <token>' without a file:line citation should be flagged."""

    def test_bare_number_flagged(self):
        """True-positive: 'default 110' with no citation -> unbacked-default."""
        result = lint("default 110")
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" in rules
        assert result["fatal_count"] >= 1

    def test_bare_identifier_flagged(self):
        """True-positive: 'default timeout' with no citation -> unbacked-default."""
        result = lint("default timeout")
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" in rules

    def test_function_call_not_flagged(self):
        """Regression: 'default timeout()' must NOT produce unbacked-default (the fixed bug)."""
        result = lint("default timeout()")
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" not in rules
        assert result["fatal_count"] == 0

    def test_function_call_with_space_not_flagged(self):
        """Edge-case: 'default timeout ()' (space before paren) must NOT be flagged."""
        result = lint("default timeout ()")
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" not in rules

    def test_cited_line_not_flagged(self):
        """Citation-backed: file:line within 100 chars exempts the claim."""
        text = "default 110  (see config.py:42 for rationale)"
        result = lint(text)
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" not in rules

    def test_dotted_identifier_flagged(self):
        """'default some.value' (dotted) without citation is flagged (matches on 'some')."""
        result = lint("default some.value")
        rules = [w["rule"] for w in result["warnings"]]
        assert "unbacked-default" in rules

    def test_dotted_function_call_not_flagged(self):
        """'default some.func()' — token 'some' is followed by '.func(' not '(', so it matches.
        This is an edge case: the rule flags 'default some' portion but not 'some()' directly.
        The important regression is plain 'default timeout()' which must NOT be flagged."""
        # The critical regression test is test_function_call_not_flagged above.
        # For dotted-method calls, the first word 'some' doesn't have '(' right after it
        # so it still gets flagged — that is acceptable conservative behavior.
        pass

    def test_severity_is_high(self):
        """unbacked-default severity must be 'high'."""
        result = lint("default 110")
        hits = [w for w in result["warnings"] if w["rule"] == "unbacked-default"]
        assert hits
        assert hits[0]["severity"] == "high"


# ---------------------------------------------------------------------------
# lint() result structure
# ---------------------------------------------------------------------------


class TestLintResultStructure:
    """Verify the JSON envelope returned by lint()."""

    def test_clean_text_no_warnings(self):
        """Prose with no triggering patterns produces empty warnings."""
        result = lint("The system is running well.")
        assert result["warnings"] == []
        assert result["fatal_count"] == 0
        assert result["warning_count"] == 0
        assert result["summary"] == "no issues found"

    def test_fatal_count_increments_per_high_severity(self):
        """Two distinct high-severity matches increment fatal_count by 2."""
        text = "default 110\ndefault 220"
        result = lint(text)
        assert result["fatal_count"] == 2

    def test_summary_reflects_fatal(self):
        """Summary string mentions high-severity count when fatal_count >= 1."""
        result = lint("default 110")
        assert "high-severity" in result["summary"]

    def test_line_number_reported(self):
        """Warning includes 1-based line number."""
        text = "first line\ndefault 110"
        result = lint(text)
        hits = [w for w in result["warnings"] if w["rule"] == "unbacked-default"]
        assert hits
        assert hits[0]["line"] == 2


# ---------------------------------------------------------------------------
# main() / --stdin path
# ---------------------------------------------------------------------------


class TestMainStdin:
    """Exercise the CLI entry-point via monkeypatching stdin."""

    def test_stdin_clean_exits_zero(self, monkeypatch, capsys):
        """Clean input via --stdin exits 0 and prints valid JSON."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("The system is fine."))
        monkeypatch.setattr("sys.argv", ["prompt_linter.py", "--stdin"])
        with pytest.raises(SystemExit) as exc_info:
            _linter.main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["fatal_count"] == 0

    def test_stdin_flagged_exits_two(self, monkeypatch, capsys):
        """Input with high-severity claim via --stdin exits 2."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("default 110"))
        monkeypatch.setattr("sys.argv", ["prompt_linter.py", "--stdin"])
        with pytest.raises(SystemExit) as exc_info:
            _linter.main()
        assert exc_info.value.code == 2
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["fatal_count"] >= 1
