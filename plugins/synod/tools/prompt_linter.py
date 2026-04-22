#!/usr/bin/env python3
"""
prompt_linter.py — Contract #3 of synod-plus.

Audits a user-supplied PROBLEM string for unbacked claims before it reaches
solvers. Outputs a single JSON line to stdout.

Exit 0  → fatal_count == 0
Exit 2  → fatal_count >= 1
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# Citation pattern: \S+.(py|ts|js|go|rs|md|json|toml):\d+  within 100 chars
# ---------------------------------------------------------------------------
CITE_RE = re.compile(
    r'\S+\.(?:py|ts|js|go|rs|md|json|toml):\d+',
    re.IGNORECASE
)

CITATION_WINDOW = 100  # chars to look ahead after match end


def _is_cited(text: str, match_end: int) -> bool:
    """Return True if a file:line citation appears within CITATION_WINDOW chars after match_end."""
    window = text[match_end:match_end + CITATION_WINDOW]
    return bool(CITE_RE.search(window))


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def _rule_unbacked_default(line_text: str, line_no: int, full_text: str, line_start: int):
    """
    unbacked-default (high)
    Pattern: 'default' followed by a non-paren token (avoids function calls).
    """
    pattern = re.compile(
        r'default\s+\S+(?!\s*\()',
        re.IGNORECASE
    )
    warnings = []
    for m in pattern.finditer(line_text):
        abs_end = line_start + m.end()
        if not _is_cited(full_text, abs_end):
            span = m.group()[:80]
            warnings.append({
                "rule": "unbacked-default",
                "span": span,
                "line": line_no,
                "severity": "high",
                "suggestion": "cite file:line (e.g., __main__.py:138)",
            })
    return warnings


def _rule_uncited_numeric(line_text: str, line_no: int, full_text: str, line_start: int):
    """
    uncited-numeric (medium)
    Pattern: ~?<number> followed by unit words (lines, LoC, tests, sessions, 줄, …).
    """
    pattern = re.compile(
        r'~?\d[\d,]*\s*(?:줄|lines?|LoC|tests?|tests?개|sessions?)',
        re.IGNORECASE
    )
    warnings = []
    for m in pattern.finditer(line_text):
        abs_end = line_start + m.end()
        if not _is_cited(full_text, abs_end):
            span = m.group()[:80]
            warnings.append({
                "rule": "uncited-numeric",
                "span": span,
                "line": line_no,
                "severity": "medium",
                "suggestion": "cite source of line/test count",
            })
    return warnings


def _rule_existence_claim(line_text: str, line_no: int, full_text: str, line_start: int):
    """
    existence-claim (high)
    Pattern: path segment like providers/ modules/ lib/ src/ without ls or citation.
    """
    pattern = re.compile(
        r'(?:providers|modules|lib|src)/\S*',
        re.IGNORECASE
    )
    ls_nearby_re = re.compile(r'\bls\b', re.IGNORECASE)
    warnings = []
    for m in pattern.finditer(line_text):
        abs_end = line_start + m.end()
        # check for 'ls' within 50 chars before the match (in the line)
        pre_window = line_text[max(0, m.start() - 50):m.start()]
        has_ls = bool(ls_nearby_re.search(pre_window))
        if not has_ls and not _is_cited(full_text, abs_end):
            span = m.group()[:80]
            warnings.append({
                "rule": "existence-claim",
                "span": span,
                "line": line_no,
                "severity": "high",
                "suggestion": "verify path exists; cite (e.g., ls providers/ or ground_truth_probe.py output)",
            })
    return warnings


def _rule_version_unverified(line_text: str, line_no: int, full_text: str, line_start: int):
    """
    version-unverified (low)
    Pattern: bare v<digits>.<digits>... without a nearby source file citation.
    """
    pattern = re.compile(
        r'\bv\d[\d.]+\b'
    )
    warnings = []
    for m in pattern.finditer(line_text):
        abs_end = line_start + m.end()
        if not _is_cited(full_text, abs_end):
            span = m.group()[:80]
            warnings.append({
                "rule": "version-unverified",
                "span": span,
                "line": line_no,
                "severity": "low",
                "suggestion": "cite the source file for this version string",
            })
    return warnings


def _rule_test_count_claim(line_text: str, line_no: int, full_text: str, line_start: int):
    """
    test-count-claim (medium)
    Pattern: N/N regression|tests|green without a pytest reference nearby.
    """
    pattern = re.compile(
        r'\d+/\d+\s*(?:regression|tests?|green)',
        re.IGNORECASE
    )
    pytest_re = re.compile(r'\bpytest\b', re.IGNORECASE)
    warnings = []
    for m in pattern.finditer(line_text):
        abs_end = line_start + m.end()
        # look for 'pytest' within 100 chars in either direction (in full_text)
        window_start = max(0, line_start + m.start() - 100)
        window_end = min(len(full_text), abs_end + 100)
        nearby = full_text[window_start:window_end]
        has_pytest = bool(pytest_re.search(nearby))
        if not has_pytest and not _is_cited(full_text, abs_end):
            span = m.group()[:80]
            warnings.append({
                "rule": "test-count-claim",
                "span": span,
                "line": line_no,
                "severity": "medium",
                "suggestion": "cite pytest output (e.g., test_session.txt:1) or run pytest first",
            })
    return warnings


RULES = [
    _rule_unbacked_default,
    _rule_uncited_numeric,
    _rule_existence_claim,
    _rule_version_unverified,
    _rule_test_count_claim,
]

# ---------------------------------------------------------------------------
# Main linting logic
# ---------------------------------------------------------------------------

def lint(text: str):
    lines = text.splitlines()
    all_warnings = []

    # Build cumulative line start offsets for absolute position lookups
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1  # +1 for the newline

    for line_idx, line_text in enumerate(lines):
        line_no = line_idx + 1
        line_start = offsets[line_idx]
        for rule_fn in RULES:
            all_warnings.extend(rule_fn(line_text, line_no, text, line_start))

    fatal_count = sum(1 for w in all_warnings if w["severity"] == "high")
    warning_count = sum(1 for w in all_warnings if w["severity"] in ("medium", "low"))

    if fatal_count >= 1:
        summary = f"{fatal_count} high-severity unbacked claim(s) found; prompt likely stale"
    elif warning_count >= 1:
        summary = f"{warning_count} warning(s) found; review before submitting"
    else:
        summary = "no issues found"

    return {
        "warnings": all_warnings,
        "fatal_count": fatal_count,
        "warning_count": warning_count,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit a prompt string for unbacked claims."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stdin", action="store_true", help="Read input from stdin")
    group.add_argument("--file", metavar="PATH", help="Read input from file")
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            sys.stderr.write(f"prompt_linter: cannot open file: {exc}\n")
            sys.exit(2)
    else:
        # default: read from stdin (covers both --stdin and bare invocation)
        text = sys.stdin.read()

    result = lint(text)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(2 if result["fatal_count"] >= 1 else 0)


if __name__ == "__main__":
    main()
