#!/usr/bin/env python3
"""Ground-truth probe for synod-plus: mechanically inspect a target codebase
before any LLM is involved. Implements Contract #1 from DESIGN.md."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
    _TOMLLIB_AVAILABLE = True
except ImportError:
    _TOMLLIB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_lang(target: Path) -> str:
    if (target / "pyproject.toml").exists() or (target / "setup.py").exists():
        return "python"
    if (target / "package.json").exists():
        return "node"
    if (target / "go.mod").exists():
        return "go"
    if (target / "Cargo.toml").exists():
        return "rust"
    return "unknown"


# ---------------------------------------------------------------------------
# pyproject.toml parsing (tomllib on 3.11+, regex fallback on 3.10)
# ---------------------------------------------------------------------------

def _parse_pyproject_regex(text: str) -> dict:
    """Minimal regex-based pyproject.toml parser for [project] section."""
    result = {}
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if stripped.startswith("[") and stripped != "[project]":
            in_project = False
        if in_project:
            m = re.match(r'^(\w+)\s*=\s*"([^"]*)"', stripped)
            if m:
                result[m.group(1)] = m.group(2)
    return result


def parse_pyproject(target: Path) -> dict:
    path = target / "pyproject.toml"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if _TOMLLIB_AVAILABLE:
        try:
            data = tomllib.loads(text)
            return data.get("project", {})
        except Exception:
            pass
    return _parse_pyproject_regex(text)


# ---------------------------------------------------------------------------
# Artifact: import_probe.json
# ---------------------------------------------------------------------------

def run_import_probe(target: Path, lang: str, project_info: dict) -> dict:
    attempts = []
    can_import = False

    if lang == "python":
        pkg_name = project_info.get("name", "")
        if not pkg_name:
            # fallback: look for a directory that looks like a package
            candidates = [d.name for d in target.iterdir()
                          if d.is_dir() and (d / "__init__.py").exists()]
            pkg_name = candidates[0] if candidates else ""

        if pkg_name:
            pkg_python = pkg_name.replace("-", "_")
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import {pkg_python}"],
                    capture_output=True, text=True, timeout=15,
                    cwd=str(target)
                )
                success = result.returncode == 0
                error_msg = (result.stderr.strip().splitlines()[-1]
                             if result.stderr.strip() else "")
                attempts.append({
                    "module": pkg_python,
                    "result": "ok" if success else "fail",
                    "error": "" if success else error_msg,
                })
                can_import = success
            except subprocess.TimeoutExpired:
                attempts.append({
                    "module": pkg_python,
                    "result": "fail",
                    "error": "TimeoutExpired",
                })
        else:
            attempts.append({
                "module": "(unknown)",
                "result": "fail",
                "error": "Could not determine top-level package name",
            })

    return {
        "lang": lang,
        "attempts": attempts,
        "can_import_top_level": can_import,
    }


# ---------------------------------------------------------------------------
# Artifact: test_collect.json
# ---------------------------------------------------------------------------

def run_test_collect(target: Path) -> dict:
    runner = "pytest"
    collected = 0
    errors = []
    items_sample = []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
            capture_output=True, text=True, timeout=20,
            cwd=str(target)
        )
        output = result.stdout + result.stderr
        # Parse summary line like "3 tests collected" or "no tests ran"
        m = re.search(r"(\d+)\s+(?:test[s]?\s+)?collected", output)
        if m:
            collected = int(m.group(1))
        # Collect error lines
        for line in output.splitlines():
            if "ERROR" in line or "error" in line.lower():
                errors.append(line.strip())
        errors = errors[:10]
        # Sample test item names
        for line in output.splitlines():
            if "::" in line and not line.startswith("=") and not line.startswith("E "):
                items_sample.append(line.strip())
        items_sample = items_sample[:20]
    except FileNotFoundError:
        errors.append("pytest not found in environment")
    except subprocess.TimeoutExpired:
        errors.append("pytest --collect-only timed out after 20s")

    return {
        "runner": runner,
        "collected": collected,
        "errors": errors,
        "items_sample": items_sample,
    }


# ---------------------------------------------------------------------------
# Artifact: file_tree.txt
# ---------------------------------------------------------------------------

def build_file_tree(target: Path, max_entries: int) -> str:
    lines = []
    try:
        for root, dirs, files in os.walk(str(target)):
            # Skip hidden dirs and common noise
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in {
                "__pycache__", "node_modules", ".git", "dist", "build", ".tox", "venv", ".venv"
            })
            rel_root = Path(root).relative_to(target)
            for fname in sorted(files):
                rel_path = str(rel_root / fname) if str(rel_root) != "." else fname
                lines.append(rel_path)
                if len(lines) >= max_entries:
                    lines.append(f"... (truncated at {max_entries} entries)")
                    return "\n".join(lines)
    except PermissionError as e:
        lines.append(f"[PermissionError: {e}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Artifact: version_pins.json
# ---------------------------------------------------------------------------

def get_changelog_top(target: Path) -> str | None:
    for name in ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "CHANGES"):
        path = target / name
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    m = re.match(r"^#+\s*(v?\d[\d.]+[^\s]*)", line)
                    if m:
                        return m.group(1)
            except Exception:
                pass
    return None


def run_version_pins(target: Path, project_info: dict) -> dict:
    pyproject_version = project_info.get("version", None)
    package_json_version = None

    pkg_json = target / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            package_json_version = data.get("version")
        except Exception:
            pass

    changelog_top = get_changelog_top(target)

    # Determine consistency
    # Compare pyproject version with changelog top if both exist
    consistency = "unknown"
    if pyproject_version and changelog_top:
        # Normalise: strip leading 'v'
        pv = pyproject_version.lstrip("v").strip()
        cv = changelog_top.lstrip("v").strip()
        # changelog might have extra suffix like "v4.0-phase0"
        # Do prefix match: changelog top starts with pyproject version
        if pv == cv or cv.startswith(pv) or pv.startswith(cv):
            consistency = "ok"
        else:
            consistency = "mismatch"
    elif pyproject_version or changelog_top:
        consistency = "unknown"

    return {
        "pyproject_toml": pyproject_version,
        "package_json": package_json_version,
        "changelog_top": changelog_top,
        "consistency": consistency,
    }


# ---------------------------------------------------------------------------
# Artifact: integrity.json
# ---------------------------------------------------------------------------

def compute_integrity(import_probe: dict, test_collect: dict,
                      version_pins: dict) -> dict:
    issues = []
    can_run = import_probe.get("can_import_top_level", False)
    test_count = test_collect.get("collected", 0)
    version_consistency = version_pins.get("consistency", "unknown")

    if not can_run:
        # Extract error message from import attempts
        for attempt in import_probe.get("attempts", []):
            if attempt.get("result") == "fail":
                msg = attempt.get("error") or "import failed"
                issues.append({"severity": "high", "msg": f"Import failed: {msg}"})
                break
        if not import_probe.get("attempts"):
            issues.append({"severity": "high", "msg": "No importable top-level package found"})

    if test_count == 0:
        issues.append({"severity": "medium", "msg": "No tests collected"})

    if version_consistency == "mismatch":
        issues.append({"severity": "medium",
                       "msg": f"Version mismatch: pyproject={version_pins.get('pyproject_toml')} "
                              f"changelog={version_pins.get('changelog_top')}"})

    for err in test_collect.get("errors", []):
        if err:
            issues.append({"severity": "low", "msg": f"Test collect error: {err}"})

    # Score: start at 10, deduct for issues
    score = 10
    for issue in issues:
        if issue["severity"] == "high":
            score -= 4
        elif issue["severity"] == "medium":
            score -= 2
        else:
            score -= 1
    score = max(0, score)

    return {
        "can_run": can_run,
        "test_count": test_count,
        "version_consistency": version_consistency,
        "issues": issues,
        "score": score,
    }


# ---------------------------------------------------------------------------
# Status logic
# ---------------------------------------------------------------------------

def compute_status(import_probe: dict, integrity: dict) -> str:
    has_high = any(i["severity"] == "high" for i in integrity.get("issues", []))
    can_run = import_probe.get("can_import_top_level", False)

    if not can_run or has_high:
        return "broken"

    version_ok = integrity.get("version_consistency") != "mismatch"
    has_tests = integrity.get("test_count", 0) > 0
    if not version_ok or not has_tests:
        return "degraded"

    return "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ground-truth probe for synod-plus (Contract #1)"
    )
    parser.add_argument("target_path", help="Path to codebase root")
    parser.add_argument("--lang", choices=["auto", "python", "node", "go", "rust"],
                        default="auto")
    parser.add_argument("--output-dir", default=None,
                        help="Directory for artifact files (default: <target>/.synod-plus-probe/)")
    parser.add_argument("--max-tree-entries", type=int, default=200)
    args = parser.parse_args()

    target = Path(args.target_path).resolve()
    if not target.exists() or not os.access(str(target), os.R_OK):
        print(json.dumps({
            "error": f"Target path does not exist or is not readable: {target}"
        }))
        sys.exit(2)

    output_dir = Path(args.output_dir) if args.output_dir else target / ".synod-plus-probe"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Language detection
    lang = args.lang if args.lang != "auto" else detect_lang(target)

    # Parse project metadata
    project_info = {}
    if lang == "python":
        project_info = parse_pyproject(target)

    # Run all probes
    import_probe = run_import_probe(target, lang, project_info)
    test_collect = run_test_collect(target)
    file_tree_text = build_file_tree(target, args.max_tree_entries)
    version_pins = run_version_pins(target, project_info)
    integrity = compute_integrity(import_probe, test_collect, version_pins)

    # Write artifacts
    (output_dir / "import_probe.json").write_text(
        json.dumps(import_probe, indent=2), encoding="utf-8")
    (output_dir / "test_collect.json").write_text(
        json.dumps(test_collect, indent=2), encoding="utf-8")
    (output_dir / "file_tree.txt").write_text(file_tree_text, encoding="utf-8")
    (output_dir / "version_pins.json").write_text(
        json.dumps(version_pins, indent=2), encoding="utf-8")
    (output_dir / "integrity.json").write_text(
        json.dumps(integrity, indent=2), encoding="utf-8")

    # Compute final status
    status = compute_status(import_probe, integrity)

    # Build top_findings
    top_findings = []
    for attempt in import_probe.get("attempts", []):
        if attempt.get("result") == "fail" and attempt.get("error"):
            top_findings.append(attempt["error"])
    for issue in integrity.get("issues", []):
        msg = issue.get("msg", "")
        if msg and msg not in top_findings:
            top_findings.append(msg)
    top_findings = top_findings[:5]

    # Artifact paths (relative to output_dir for readability)
    artifact_files = [
        str(output_dir / "import_probe.json"),
        str(output_dir / "test_collect.json"),
        str(output_dir / "file_tree.txt"),
        str(output_dir / "version_pins.json"),
        str(output_dir / "integrity.json"),
    ]

    result = {
        "status": status,
        "lang": lang,
        "target": str(target),
        "artifacts": artifact_files,
        "top_findings": top_findings,
        "can_run": integrity["can_run"],
        "test_count": integrity["test_count"],
        "version_consistency": integrity["version_consistency"],
    }

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
