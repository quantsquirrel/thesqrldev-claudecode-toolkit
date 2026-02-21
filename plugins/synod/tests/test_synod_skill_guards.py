"""Tests for Synod skill MCP guard directives.

Validates that:
1. allowed-tools frontmatter excludes MCP tools
2. MCP prohibition directives exist in skill markdown files
3. Phase 1 uses run_cli pattern for zsh compatibility
"""

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent / "skills"
SYNOD_MD = SKILLS_DIR / "synod" / "SKILL.md"
PHASE0_MD = SKILLS_DIR / "synod" / "modules" / "synod-phase0-setup.md"
PHASE1_MD = SKILLS_DIR / "synod" / "modules" / "synod-phase1-solver.md"


def _parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    text = filepath.read_text()
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


class TestAllowedToolsFrontmatter:
    """Verify allowed-tools excludes MCP tools."""

    def test_synod_frontmatter_excludes_mcp_tools(self):
        fm = _parse_frontmatter(SYNOD_MD)
        allowed = fm.get("allowed-tools", "")

        # Must not contain MCP tool names
        assert "ask_codex" not in allowed
        assert "ask_gemini" not in allowed
        assert "mcp__" not in allowed

        # Must contain exactly the expected tools
        expected = {"Read", "Write", "Bash", "Glob", "Grep", "Task"}
        tools = {t.strip().strip("[]") for t in allowed.split(",")}
        assert tools == expected


class TestMCPProhibitionDirectives:
    """Verify MCP prohibition directives exist in skill files."""

    def test_synod_md_has_mcp_prohibition_directive(self):
        text = SYNOD_MD.read_text()
        assert "MCP TOOL PROHIBITION" in text
        assert "ask_codex" in text
        assert "ask_gemini" in text
        assert "mcp__*" in text

    def test_phase1_has_mcp_prohibition_in_guard(self):
        text = PHASE1_MD.read_text()
        assert "MANDATORY EXTERNAL EXECUTION" in text
        assert "ask_codex" in text
        assert "ask_gemini" in text

    def test_phase0_has_cli_only_note(self):
        text = PHASE0_MD.read_text()
        assert "CLI tools" in text or "CLI" in text
        assert "ask_codex" in text
        assert "ask_gemini" in text


class TestZshCompatibility:
    """Verify zsh-compatible CLI execution patterns."""

    def test_synod_md_has_run_cli_helper(self):
        text = SYNOD_MD.read_text()
        assert "run_cli()" in text or "run_cli ()" in text
        assert '*.py' in text
        assert "python3" in text

    def test_phase1_uses_run_cli_pattern(self):
        text = PHASE1_MD.read_text()
        assert 'run_cli "$GEMINI_CLI"' in text
        assert 'run_cli "$OPENAI_CLI"' in text

    def test_resolve_cli_no_python3_prefix(self):
        text = SYNOD_MD.read_text()
        # resolve_cli should NOT return "python3 ${TOOLS_DIR}/..."
        assert 'echo "python3 ${TOOLS_DIR}' not in text
