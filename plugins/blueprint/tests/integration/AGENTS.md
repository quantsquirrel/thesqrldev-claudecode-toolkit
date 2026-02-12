<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-12T00:00:00Z | Updated: 2026-02-12T00:00:00Z -->

# tests/integration/

## Purpose

End-to-end workflow tests for Blueprint skills. Verify complete PDCA cycles, gap analysis, pipeline execution, and cancellation workflows. Tests ensure correct state management, phase transitions, concurrent operations, and graceful failure handling.

## Key Files

| File | Description |
|------|-------------|
| `cancel-skill.test.mjs` | Cancel workflow tests - active cycle discovery, graceful shutdown, state cleanup (17 KB) |
| `gap-skill.test.mjs` | Gap analysis workflow tests - directory structure, state creation, report generation (9.5 KB) |
| `pdca-skill.test.mjs` | PDCA cycle integration tests - complete Plan-Do-Check-Act iterations, phase gates (17 KB) |
| `pipeline-skill.test.mjs` | Pipeline execution tests - phased workflows, gate conditions, preset expansion (19 KB) |

## For AI Agents

### Working In This Directory

- **Test framework**: Node.js built-in `node --test` (imported from `node:test`)
- **File naming**: `*.test.mjs` suffix required for auto-discovery
- **Mock strategy**: Use temporary directories (`mkdtemp`) and mock agent outputs
- **State isolation**: Each test creates isolated `.blueprint/` state directories
- **Cleanup**: Always clean up temporary files in `after()` hooks

### Testing Requirements

- Run tests: `npm test` or `node tests/integration/*.test.mjs`
- Each test must:
  - Create temporary state directory with `mkdtemp()`
  - Initialize Blueprint state structure (`.blueprint/pdca/`, `.blueprint/gaps/`, etc.)
  - Simulate complete workflow end-to-end
  - Verify state transitions, file creation, and final status
  - Clean up with `rm(tempDir, { recursive: true, force: true })`
- Tests should verify:
  - State file creation and updates
  - Lock acquisition and release
  - Phase transitions follow expected sequence
  - Error conditions handled gracefully
  - Concurrent operations don't corrupt state

### Common Patterns

- **Setup**: Create temp dir → initialize Blueprint structure → create initial state
- **Execute**: Simulate skill invocation → run workflow phases → check gates
- **Assert**: Verify state files exist → check status transitions → validate output format
- **Teardown**: Remove temp directory → verify locks released

**Test structure example**:
```javascript
import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { generateId, ensureDir, loadState, saveState } from '../../hooks/lib/state-manager.mjs';

describe('Workflow Integration', () => {
  let tempDir;
  let blueprintDir;

  before(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'blueprint-test-'));
    blueprintDir = join(tempDir, '.blueprint');
    ensureDir(blueprintDir);
  });

  after(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it('should complete workflow', () => {
    // Test implementation
  });
});
```

## Dependencies

### Internal

- `../../hooks/lib/state-manager.mjs` - State utilities (generateId, ensureDir, loadState, saveState, archiveState)
- `../../hooks/lib/constants.mjs` - Shared constants
- `../../config/` - Configuration files for test scenarios

### External

- Node.js built-in modules: `node:test`, `node:assert/strict`, `node:fs/promises`, `node:fs`, `node:path`, `node:os`

<!-- MANUAL: -->
