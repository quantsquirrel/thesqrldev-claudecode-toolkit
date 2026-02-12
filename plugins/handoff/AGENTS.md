<!-- Generated: 2026-02-10 | Updated: 2026-02-10 -->

# claude-handoff-baton

## Purpose

Session handoff tool for Claude Code that preserves context across sessions. When long-running work spans multiple sessions or autocompact triggers, `/handoff` captures what was accomplished, what's pending, what failed, and how to resume. Output scales automatically based on session complexity (L1/L2/L3 levels).

**Version:** 2.3.0
**License:** MIT

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Core skill definition with YAML frontmatter - the `/handoff` command spec |
| `README.md` | User-facing documentation (English) |
| `README-ko.md` | User-facing documentation (Korean) |
| `LICENSE` | MIT License |
| `.gitignore` | Git ignore patterns |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Marketplace registration metadata (see `.claude-plugin/AGENTS.md`) |
| `assets/` | Static assets for documentation (see `assets/AGENTS.md`) |
| `examples/` | Reference handoff documents (see `examples/AGENTS.md`) |
| `hooks/` | PostToolUse/PrePromptSubmit hook system - core automation (see `hooks/AGENTS.md`) |
| `plugins/` | Claude Code plugin implementation (see `plugins/AGENTS.md`) |
| `scripts/` | Validation and utility scripts (see `scripts/AGENTS.md`) |

## For AI Agents

### Working In This Directory

- Read `SKILL.md` first for the complete workflow and template
- The `/handoff` command follows a 7-step workflow: create dir, analyze, scale, redact, save, copy, confirm
- Output scales by level: L1 (~100 tokens), L2 (~300 tokens, default), L3 (~500 tokens)
- Sensitive values are always redacted before saving
- Files are saved to `.claude/handoffs/` with random suffix to prevent collisions

### Architecture Overview

```
User runs /handoff
       |
       v
plugins/handoff/skills/handoff.md    <-- Skill definition (L1/L2/L3 templates)
       |
       v
hooks/auto-handoff.mjs               <-- PostToolUse hook (monitors context, suggests handoff)
hooks/task-size-estimator.mjs         <-- PrePromptSubmit hook (analyzes task size)
hooks/constants.mjs                   <-- Shared thresholds and messages
       |
       v
.claude/handoffs/                     <-- Output directory (generated at runtime)
```

### Testing Requirements

```bash
# Test the /handoff command
/handoff "test-topic"

# Verify file created
ls -la .claude/handoffs/

# Validate handoff quality
./scripts/validate.sh .claude/handoffs/handoff-*.md

# Test auto-handoff hook
AUTO_HANDOFF_DEBUG=1 node hooks/auto-handoff.mjs <<< '{"tool_name":"Read","session_id":"test","tool_response":"..."}'
```

### Common Patterns

- All hook scripts use ESM (`import`/`export`) with `.mjs` extension
- Constants are centralized in `hooks/constants.mjs`
- State files go to `/tmp/` (ephemeral) or `.claude/handoffs/` (persistent)
- Version must stay consistent across: `plugins/handoff/plugin.json`, `.claude-plugin/marketplace.json`

## Dependencies

### External

| Dependency | Purpose |
|------------|---------|
| Node.js | Hook script execution |
| Claude Code | Runs `/handoff` skill and hooks |
| pbcopy / xclip | Clipboard operations |
| git | File change detection and branch info |

### Security

- Always redact sensitive values (API keys, tokens, passwords, JWTs)
- Users should add `.claude/handoffs/` to `.gitignore`
- Never commit handoff files to public repos

<!-- MANUAL: -->
