<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# skills/cancel/

## Purpose

Gracefully cancel active PDCA cycles and pipeline runs. Updates workflow state to "cancelled" status, archives cancelled operations to history directories, and removes them from active indices. Provides two modes: interactive (with confirmation) and force (--force flag). Handles edge cases like already-completed workflows and missing state files.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill metadata and instructions (user-facing documentation) |

## Skill Metadata

**Name**: cancel

**Trigger**: `/blueprint:cancel` or `/blueprint:cancel --force`

**Arguments**:
- `--force` (optional) - Force cancel all active workflows without confirmation

**Allowed Tools**: Read, Write, Edit, Bash, Glob, Grep

## Workflow Phases

### 1. Discovery Phase

Scan for active PDCA cycles and pipeline runs:

- Read `.blueprint/pdca/active-cycles.json` (list of active cycle IDs)
- Scan `.blueprint/pdca/cycles/*.json` for status=active records
- Read `.blueprint/pipeline/active-runs.json` (if exists)
- Scan `.blueprint/pipeline/runs/*.json` for status=running or status=paused

Present findings to user with format:
```
Found active blueprint operations:
- PDCA Cycles (N): [list with iteration, phase]
- Pipeline Runs (M): [list with phase, preset]
```

If no active operations, display: `No active blueprint operations found.`

### 2. Confirmation Phase (unless --force)

When operations found and `--force` not set:

Display confirmation prompt: `Cancel these operations? [y/N]`

- User responds `y` → continue to Status Change
- User responds `n` or timeout → exit without changes

With `--force`: skip confirmation, proceed directly to Status Change.

### 3. Status Change Phase

For each identified operation:

**Update PDCA cycle**:
```bash
jq '.status = "cancelled" | .cancelled_at = now | .cancel_reason = "User requested"' \
  .blueprint/pdca/cycles/{id}.json > tmp && mv tmp .blueprint/pdca/cycles/{id}.json
```

**Update pipeline run**:
```bash
jq '.status = "cancelled" | .cancelled_at = now | .cancel_reason = "User requested"' \
  .blueprint/pipeline/runs/{id}.json > tmp && mv tmp .blueprint/pipeline/runs/{id}.json
```

### 4. Archive Phase

Move cancelled operations to history directories:

**PDCA cycle**:
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p .blueprint/pdca/history/
mv .blueprint/pdca/cycles/{id}.json .blueprint/pdca/history/{id}-{TIMESTAMP}.json
```

**Pipeline run**:
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p .blueprint/pipeline/history/
mv .blueprint/pipeline/runs/{id}.json .blueprint/pipeline/history/{id}-{TIMESTAMP}.json
```

### 5. Index Cleanup Phase

Remove cancelled operations from active indices:

**PDCA**: Update `.blueprint/pdca/active-cycles.json`:
```bash
jq --arg id "{id}" '.cycles = [.cycles[] | select(.id != $id)]' \
  .blueprint/pdca/active-cycles.json > tmp && mv tmp .blueprint/pdca/active-cycles.json
```

**Pipeline** (if index exists): Update `.blueprint/pipeline/active-runs.json`:
```bash
jq --arg id "{id}" '.runs = [.runs[] | select(.id != $id)]' \
  .blueprint/pipeline/active-runs.json > tmp && mv tmp .blueprint/pipeline/active-runs.json
```

### 6. Output Phase

Generate cancellation summary:

```
## Blueprint Cancellation Complete

### Cancelled Operations

**PDCA Cycles (N)**
- {id}: "{task}"
  - Archived to: .blueprint/pdca/history/{id}-{timestamp}.json

**Pipeline Runs (M)**
- {id}: "{feature}"
  - Archived to: .blueprint/pipeline/history/{id}-{timestamp}.json

### Summary
- Total operations cancelled: N+M
- All operations archived to history/
```

## For AI Agents

### Working In This Directory

- **One file per skill**: SKILL.md contains all skill metadata and instructions
- **No handler code**: This skill is invoked by blueprint-detect.mjs hook which routes to coordinator
- **State file operations**: Use utilities from `hooks/lib/` (state-manager, io)
- **User interaction**: Present confirmation prompts clearly, handle user input robustly

### Testing Requirements

- Test discovery: verify detection of active cycles and runs
- Test confirmation: `--force` skips prompt, interactive mode shows prompt
- Test status update: verify cancelled operations marked with status and timestamp
- Test archiving: verify files moved to history directories
- Test index cleanup: verify active indices updated, cancelled IDs removed
- Test edge cases: no active operations, invalid IDs, permission errors

### Common Patterns

**Read active cycles**:
```javascript
const activeIndex = await readState('.blueprint/pdca/active-cycles.json')
  .catch(() => ({ cycles: [] }));
const activeIds = activeIndex.cycles.map(c => c.id);
```

**Update operation status**:
```javascript
const state = await readState(`.blueprint/pdca/cycles/${id}.json`);
state.status = 'cancelled';
state.cancelled_at = new Date().toISOString();
state.cancel_reason = 'User requested cancellation';
await updateState(`.blueprint/pdca/cycles/${id}.json`, state);
```

**Archive to history**:
```javascript
const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
const historyPath = `.blueprint/pdca/history/${id}-${timestamp}.json`;
await ensureDir('.blueprint/pdca/history');
await atomicRename(sourcePath, historyPath);
```

## State File Locations

**PDCA**:
- Active: `.blueprint/pdca/cycles/{id}.json`
- Index: `.blueprint/pdca/active-cycles.json`
- History: `.blueprint/pdca/history/{id}-{timestamp}.json`

**Pipeline**:
- Active: `.blueprint/pipeline/runs/{id}.json`
- Index: `.blueprint/pipeline/active-runs.json` (optional)
- History: `.blueprint/pipeline/history/{id}-{timestamp}.json`

## Dependencies

### Internal

- `hooks/lib/state-manager.mjs` - State file I/O with locking
- `hooks/lib/io.mjs` - Atomic file operations
- `hooks/lib/logger.mjs` - Logging

### External

- None - uses Node.js built-in modules only

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
