<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# hooks/lib/

## Purpose

Shared utility modules for Blueprint hooks. Provides file I/O operations, state management with file-based locking, complexity analysis for auto-preset detection, logging, and shared constants. These utilities enable hooks to safely read/write workflow state across concurrent sessions without corruption.

## Key Files

| File | Description |
|------|-------------|
| `constants.mjs` | Shared constants (state paths, lock TTL, timeout values, agent names) |
| `state-manager.mjs` | State file I/O with atomic writes and file-based locking protocol |
| `io.mjs` | Low-level file I/O utilities (safe writes, atomic renames, directory creation) |
| `logger.mjs` | Structured logging for hook execution with levels (debug, info, warn, error) |
| `complexity-analyzer.mjs` | Workspace complexity detection for auto-preset selection in pipeline skill |

## Module Overview

### constants.mjs

Centralized configuration values used by all hooks and utilities.

**Exports**:
- `STATE_PATHS` - Directory paths (`.blueprint/`, `.blueprint/pdca/cycles/`, etc.)
- `LOCK_TTL_MS` - Lock timeout (5 minutes)
- `HOOK_TIMEOUT_MS` - Per-hook timeout (5-10 seconds by event type)
- `AGENT_NAMES` - Available agent names from plugin registry
- `PRESET_DEFINITIONS` - Pipeline preset configurations (full, standard, minimal)

**Usage**: `import { STATE_PATHS, LOCK_TTL_MS } from './constants.mjs'`

### state-manager.mjs

Manages reading and writing workflow state files with ACID guarantees.

**Core Functions**:
- `readState(filePath)` - Read JSON state file
- `updateState(filePath, updates)` - Atomic update: acquire lock → write → release
- `acquireLock(lockFile)` - Get exclusive lock (waits up to LOCK_TTL_MS)
- `releaseLock(lockFile)` - Release lock
- `createState(filePath, initialData)` - Create new state file atomically

**Lock Protocol**:
1. Call `acquireLock(filePath + '.lock')`
2. Read current state (if exists)
3. Modify state
4. Write atomically via `io.safeWrite()`
5. Call `releaseLock(lock)` in finally block

**Error Handling**:
- Lock timeout after 5 min → throw LockTimeoutError
- Corrupted JSON → return empty object with warning log
- File permissions → throw FilePerm issuesError

### io.mjs

Low-level file I/O with atomic write semantics.

**Functions**:
- `safeWrite(path, content)` - Write to temp file, atomic rename
- `ensureDir(path)` - Create directory (parents auto-created)
- `atomicRename(oldPath, newPath)` - POSIX atomic rename
- `readJSON(path)` - Read and parse JSON, handle errors gracefully

**Atomicity Guarantee**: Files are never partially written. Uses temp file + rename pattern.

### logger.mjs

Structured logging for debugging hook execution and errors.

**Levels**: debug, info, warn, error

**Log Format**: `[{timestamp}] [{level}] [{hook-name}] {message}`

**Usage**:
```javascript
import logger from './logger.mjs';
logger.info('Starting phase-tracker');
logger.error('Lock acquisition failed', { filePath, reason });
```

### complexity-analyzer.mjs

Analyzes workspace to automatically select optimal pipeline preset.

**Function**: `analyzeComplexity(workspaceRoot)`

**Returns**:
```javascript
{
  preset: 'standard', // or 'minimal', 'full'
  confidence: 85,     // 0-100
  reasoning: 'File count (45) and module depth (3) suggest standard workflow',
  metrics: {
    fileCount: 45,
    totalLOC: 12000,
    moduleCount: 8,
    testCoverage: 0.72,
    complexity: 'medium'
  }
}
```

**Heuristics**:
- `fileCount < 20` AND `LOC < 5000` → minimal
- `fileCount 20-100` OR `LOC 5k-50k` → standard
- `fileCount > 100` OR `LOC > 50k` OR `complexity=high` → full

## For AI Agents

### Working In This Directory

- **No direct hook logic**: These are utilities only; business logic lives in `../`
- **Pure functions**: Utilities should not have side effects beyond file I/O
- **Error resilience**: All functions must handle missing files, permission errors gracefully
- **Atomic semantics**: State writes must be all-or-nothing; no partial updates ever persisted
- **Lock discipline**: Always use try-finally to release locks even on error

### Testing Requirements

- **state-manager**: Test lock contention (2+ concurrent writers blocked/serialized)
- **io**: Test atomic rename with file missing, target exists scenarios
- **logger**: Test all log levels, timestamp formatting
- **complexity-analyzer**: Test on variety of project sizes, verify heuristics
- **constants**: Verify all paths, timeouts, agent names consistent with plugin.json

### Common Patterns

**Safe State Update**:
```javascript
import { updateState } from './state-manager.mjs';
await updateState('.blueprint/pdca-abc.json', (current) => ({
  ...current,
  status: 'done',
  updated_at: new Date().toISOString()
}));
```

**Read with Fallback**:
```javascript
const state = await readState(filePath).catch(() => ({
  id: generateId(),
  status: 'new'
}));
```

**Ensure Directory Before Write**:
```javascript
import { ensureDir, safeWrite } from './io.mjs';
await ensureDir('.blueprint/pdca/history');
await safeWrite('.blueprint/pdca/history/pdca-123.json', JSON.stringify(data));
```

## Dependencies

### Internal

- None - these are leaf utilities

### External

- Node.js built-in: `fs/promises`, `path`, `crypto`

## Lock Contention Handling

When a hook tries to update state but lock is held:

1. Call `acquireLock()` with timeout (LOCK_TTL_MS = 5 min)
2. Poll lock file every 100ms with exponential backoff
3. If timeout expires, throw LockTimeoutError (hook exits with error)
4. When lock acquired, proceed with update
5. Release lock immediately after write (finally block)

**Example**: Two concurrent hooks updating same state file:
- Hook A acquires lock, writes, releases (100ms)
- Hook B waits (100ms), acquires lock, writes, releases
- Result: Both updates serialized, no corruption

## Lock File Format

Lock files are empty markers (0 bytes). Presence indicates lock held.

```
.blueprint/pdca/cycles/pdca-123.json.lock
```

TTL enforced by checking modification time:
```javascript
const now = Date.now();
const lockAge = now - fs.statSync(lockFile).mtime.getTime();
if (lockAge > LOCK_TTL_MS) {
  // Lock is stale, safe to remove and retry
  fs.unlinkSync(lockFile);
}
```

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
