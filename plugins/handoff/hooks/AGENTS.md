<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# hooks

## Purpose

Core automation engine for Claude Code integration. Implements PostToolUse and PrePromptSubmit hooks that monitor context usage, estimate task size, and suggest handoffs when approaching capacity limits. This is the critical infrastructure that makes the handoff plugin work seamlessly.

## Key Files

| File | Description |
|------|-------------|
| `auto-handoff.mjs` | PostToolUse hook - monitors context tokens, saves drafts, suggests handoff at thresholds |
| `constants.mjs` | Centralized configuration: thresholds, messages, task sizes, security patterns |
| `schema.mjs` | Structured JSON schema for handoff output (natural language + structured data) |
| `task-size-estimator.mjs` | PrePromptSubmit hook - analyzes prompt keywords to classify task size (S/M/L/XL) |
| `test-task-size.mjs` | Test script for task size estimation |
| `lockfile.mjs` | Lock file management API for tracking generation state |
| `recover.mjs` | CLI utility to find interrupted sessions and draft files |
| `install.sh` | Installation script - adds hooks to `~/.claude/settings.json` |

## For AI Agents

### Working In This Directory

**Modification safety:**
- `constants.mjs` - Safe to modify (thresholds, messages)
- `auto-handoff.mjs` - Modify with care, verify hook still outputs valid JSON
- `schema.mjs` - Stable API, extend carefully
- `task-size-estimator.mjs` - Safe to enhance keyword detection
- `recover.mjs` - Safe to enhance recovery features
- `lockfile.mjs` - Stable API, only extend exports if needed
- `install.sh` - Safe to improve, test idempotency

**Critical rules:**
- All scripts use ESM (`import`/`export`) with `.mjs` extension
- Import constants from `constants.mjs`, never hard-code values
- Hook stdin: JSON, hook stdout: JSON with `{ decision, additionalContext }`
- Always use `fs.existsSync()` before file reads
- Always use `{ recursive: true }` for directory creation
- Wrap JSON parse/stringify in try-catch

### Hook Lifecycle

```
PostToolUse (Read|Grep|Glob|Bash|WebFetch)
  -> auto-handoff.mjs reads JSON from stdin
  -> estimates tokens from tool_response (chars / 4)
  -> accumulates in /tmp/auto-handoff-state.json
  -> checks dynamic thresholds (task-size-aware)
  -> at 70%+: saves draft, outputs suggestion message
  -> at 80%+: outputs warning message
  -> at 90%+: outputs critical message

PrePromptSubmit
  -> task-size-estimator.mjs reads prompt from stdin
  -> scans for large-task keywords (refactor, migrate, all, etc.)
  -> saves task size to /tmp/task-size-state.json
  -> for XL tasks: outputs proactive warning
```

### Dynamic Thresholds (v2.0)

Thresholds adjust based on detected task size:

| Task Size | Handoff | Warning | Critical | Trigger |
|-----------|---------|---------|----------|---------|
| Small | 85% | 90% | 95% | Default for simple prompts |
| Medium | 70% | 80% | 90% | Default, or 10+ files found |
| Large | 50% | 60% | 70% | Keywords like "refactor", or 50+ files |
| XL | 30% | 40% | 50% | Keywords like "entire" + "migrate", or 200+ files |

### Testing Requirements

```bash
# Test hook execution with debug mode
AUTO_HANDOFF_DEBUG=1 node auto-handoff.mjs <<< '{"tool_name":"Read","session_id":"test-123","tool_response":"sample text"}'
cat /tmp/auto-handoff-debug.log

# Test state persistence
cat /tmp/auto-handoff-state.json | jq .

# Test task size estimation
node task-size-estimator.mjs <<< '{"prompt":"refactor all auth","session_id":"test-123"}'
cat /tmp/task-size-state.json | jq .

# Test installation (idempotent)
bash install.sh
jq '.hooks.PostToolUse' ~/.claude/settings.json

# Test recovery
node recover.mjs
```

### State Files

| File | Location | Purpose | Lifetime |
|------|----------|---------|----------|
| Session state | `/tmp/auto-handoff-state.json` | Token accumulation per session | System restart |
| Task size state | `/tmp/task-size-state.json` | Task classification per session | 1 hour (auto-cleanup) |
| Debug log | `/tmp/auto-handoff-debug.log` | Verbose hook execution logs | Manual deletion |
| Lock file | `.claude/handoffs/.generating.lock` | Marks ongoing generation | Auto-removed on completion |
| Draft files | `.claude/handoffs/.draft-*.json` | Session recovery data | Manual deletion |

### File Dependencies

```
auto-handoff.mjs
  <- constants.mjs (thresholds, messages, task sizes)
  <- fs, path, os, child_process (Node.js built-ins)

task-size-estimator.mjs
  <- constants.mjs (TASK_SIZE, LARGE_TASK_KEYWORDS, TASK_SIZE_STATE_FILE)
  <- fs, path, os (Node.js built-ins)

schema.mjs
  <- standalone (no imports)

recover.mjs
  <- constants.mjs (DRAFT_FILE_PREFIX)
  <- lockfile.mjs (checkLock)

lockfile.mjs
  <- constants.mjs (LOCK_FILE_NAME)

install.sh
  <- reads ~/.claude/settings.json
  <- references auto-handoff.mjs path

constants.mjs
  <- standalone (reads process.env for context limit detection)
```

## Dependencies

### Internal

- `../plugins/handoff/skills/handoff.md` - Skill templates that hooks support
- `../SKILL.md` - Root skill specification

### External

- Node.js (ESM support required)
- Claude Code hook system (PostToolUse, PrePromptSubmit)
- git (for branch/status in drafts)

<!-- MANUAL: -->
