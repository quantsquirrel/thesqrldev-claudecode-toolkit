<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# hooks/

## Purpose

Claude Code lifecycle hooks for event-driven Blueprint behavior. Detect skill invocations, track workflow progress, restore active sessions, preserve state during context compaction, and clean up on session end. Each hook runs on specific Claude Code events with timeout protection.

## Key Files

| File | Description |
|------|-------------|
| `hooks.json` | Hook registration manifest (event → handler mapping, timeouts, priority) |
| `blueprint-detect.mjs` | UserPromptSubmit hook - detects Blueprint skill keywords, parses args, routes to handlers |
| `phase-tracker.mjs` | PostToolUse hook - monitors agent completion, updates phase progress, triggers next phase |
| `session-loader.mjs` | SessionStart hook - loads active cycles/pipelines from `.blueprint/`, restores workflow state |
| `compact-preserver.mjs` | PreCompact hook - backs up active state before context compaction, ensures recovery |
| `cycle-finalize.cjs` | Stop hook - gracefully finalizes incomplete cycles, writes reports, releases locks |
| `session-cleanup.mjs` | SessionEnd hook - archives completed workflows, removes stale locks, resets session state |

## Hook Registration (hooks.json)

```json
{
  "hooks": {
    "UserPromptSubmit": [...],    // User message detection (skill invocation)
    "PostToolUse": [...],          // After tool/agent execution
    "SessionStart": [...],         // Session initialization
    "PreCompact": [...],           // Before context compaction
    "Stop": [...],                 // User stops session/workflow
    "SessionEnd": [...]            // Session cleanup
  }
}
```

## Hook Lifecycle

```
Session Start
  ├─ SessionStart hook fires
  │  └─ session-loader.mjs: restore active workflows
  │
  ├─ User enters prompt
  │  └─ UserPromptSubmit hook fires
  │     └─ blueprint-detect.mjs: detect keywords, parse args, dispatch to skill
  │
  ├─ Skill spawns agents → agents work → report completion
  │  └─ PostToolUse hook fires
  │     └─ phase-tracker.mjs: check phase gates, update progress, trigger next phase
  │
  ├─ (Optional) Context compaction triggered
  │  └─ PreCompact hook fires
  │     └─ compact-preserver.mjs: backup active state to safe location
  │
  ├─ User stops workflow or session
  │  └─ Stop hook fires
  │     └─ cycle-finalize.cjs: finalize incomplete cycles, write reports
  │
  └─ Session end
     └─ SessionEnd hook fires
        └─ session-cleanup.mjs: archive results, remove stale locks, reset state
```

## Hook Details

### blueprint-detect.mjs (UserPromptSubmit)

**Event**: User submits prompt

**Behavior**:
1. Scan prompt for Blueprint keywords: `/blueprint:pdca`, `/blueprint:gap`, `/blueprint:pipeline`, `/blueprint:cancel`
2. Parse arguments: `--iterations N`, `--preset NAME`, `--severity LEVEL`, `--all`, `--cycle-id ID`
3. Route to appropriate skill handler (calls skill via plugin interface)
4. Return control to Claude Code

**Timeout**: 5 seconds

**Files read/written**:
- Read: none (stateless detection)
- Write: none (skill handler writes state)

### phase-tracker.mjs (PostToolUse)

**Event**: After agent tool/task completes

**Behavior**:
1. Read active workflow state from `.blueprint/` (if any)
2. Check if tool output matches current phase expectations
3. Evaluate phase gate conditions (tests pass? document exists? etc.)
4. If gate passed: update phase to complete, trigger next phase
5. If gate failed: record failure, trigger retry or escalation
6. Write updated state atomically

**Timeout**: 5 seconds

**Files read/written**:
- Read: `{type}-{ID}.json` (active workflow state)
- Write: `{type}-{ID}.json` (updated state with phase progress)

### session-loader.mjs (SessionStart)

**Event**: Session initializes

**Behavior**:
1. Scan `.blueprint/` for active workflow files
2. For each active file (not expired):
   - Load state and verify not corrupted
   - Display restoration prompt to user
   - Set state as "resumable" in session context
3. Clean up expired locks (>5 min old)

**Timeout**: 5 seconds

**Files read/written**:
- Read: `{type}-{ID}.json` (active workflows)
- Write: none (read-only state restoration)

### compact-preserver.mjs (PreCompact)

**Event**: Before context compaction (automatic or manual)

**Behavior**:
1. Read all active workflow state from `.blueprint/`
2. Serialize state to JSON
3. Write to `.omc/checkpoints/checkpoint-{timestamp}.json` as backup
4. Record checkpoint metadata (timestamp, workflow IDs, reason: "precompact")

**Timeout**: 10 seconds

**Files read/written**:
- Read: `{type}-{ID}.json` (all active workflows)
- Write: `.omc/checkpoints/checkpoint-{timestamp}.json` (backup)

### cycle-finalize.cjs (Stop)

**Event**: User stops session or workflow stop requested

**Behavior**:
1. Identify active workflows
2. For each incomplete workflow:
   - Write completion report with final state
   - Record conclusion reason: "user-stop", "timeout", "error", etc.
   - Close final phase with available evidence
3. Release all locks
4. Archive completed state to `.omc/` if requested by user

**Timeout**: 10 seconds

**Files read/written**:
- Read: `{type}-{ID}.json`, `{type}-{ID}.lock`
- Write: finalization report, release locks

### session-cleanup.mjs (SessionEnd)

**Event**: Session ends (gracefully or forced)

**Behavior**:
1. Scan `.blueprint/` for completed workflows (status: "done", "failed", "cancelled")
2. Archive to `.omc/sessions/{sessionId}/completed/` with timestamp
3. Remove stale locks (>10 min old)
4. Reset temporary session markers
5. Summary report: workflows completed, archived, cleaned

**Timeout**: 5 seconds

**Files read/written**:
- Read: `{type}-{ID}.json`, `{type}-{ID}.lock`
- Write: archived state files, cleanup log

## lib/ Subdirectory

Shared utilities for hooks.

| File | Purpose |
|------|---------|
| `constants.mjs` | Shared constants (state paths, IDs, timeouts, lock TTL) |
| `state-manager.mjs` | State file read/write with file-based locking |
| `io.mjs` | File I/O utilities (safe write, atomic rename) |
| `complexity-analyzer.mjs` | Workspace complexity detection (preset auto-selection) |

**Lock Protocol** (state-manager.mjs):
```javascript
async function updateState(filePath, newData) {
  const lock = await acquireLock(filePath + '.lock');
  try {
    await fs.writeFile(filePath, JSON.stringify(newData));
  } finally {
    await releaseLock(lock);
  }
}
```

## For AI Agents

### Working In This Directory

- **Hook isolation**: Each hook is independent - reads from `.blueprint/`, writes state, exits
- **No hook-to-hook communication**: Use state files as message passing mechanism
- **Timeout protection**: Each hook has max execution time (5-10s) - must not block indefinitely
- **Stateless design**: Hooks don't maintain memory; state is file-based

### Testing Requirements

- Test hook detection: verify keywords trigger correct hook handlers
- Test phase gating: run multi-phase workflow, verify gates block until conditions met
- Test session restoration: save workflow state, restart session, verify state loads correctly
- Test concurrent workflows: run 2+ workflows in parallel, verify no lock contention
- Test stale lock cleanup: create old lock file, run session-cleanup, verify removed
- Test context compaction: trigger precompact hook, verify checkpoint created, workflow recoverable

### Common Patterns

- **State file naming**: `{type}-{id}.json` (e.g., `pdca-abc123.json`)
- **Lock files**: `{file}.lock` - exists while state is being written
- **Lock timeout**: TTL 5 minutes (constants.LOCK_TTL_MS)
- **Atomic writes**: always rename temp file into place, never partial writes

## Dependencies

### Internal

- `hooks/lib/*` - utilities for file I/O, locking, complexity analysis
- `config/pdca-defaults.json` - PDCA parameters for phase-tracker
- `config/pipeline-phases.json` - phase definitions for gate evaluation

### External

- Node.js `fs/promises`, `path`, `crypto` (built-in modules only)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
