<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# tests/

## Purpose

Unit and integration tests for Blueprint plugin components. Verify hooks, state management, agent coordination, configuration validation, and end-to-end workflows. Tests ensure reliability of state persistence, lock protocol, phase gating, and concurrent workflow isolation.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `unit/` | Component-level tests (hooks, state manager, config, utilities) |
| `integration/` | End-to-end workflow tests (complete PDCA cycle, pipeline execution, concurrent scenarios) |

## Test Structure

```
tests/
├── unit/
│   ├── state-manager.test.mjs      # File I/O, locking, atomic writes
│   ├── phase-tracker.test.mjs       # Phase gate evaluation, progress tracking
│   ├── config.test.mjs              # Config parsing, validation, preset expansion
│   ├── constants.test.mjs           # Shared constants
│   └── hook-detection.test.mjs      # Keyword detection, argument parsing
│
└── integration/
    ├── pdca-cycle.test.mjs          # Complete PDCA iteration (Plan → Do → Check → Act)
    ├── pipeline.test.mjs            # Full pipeline execution with phase gating
    ├── concurrent.test.mjs          # 2+ workflows running in parallel, lock contention
    ├── session-recovery.test.mjs     # State persistence, session restoration, context compaction
    └── error-handling.test.mjs       # Timeout, lock failure, missing agents, etc.
```

## Unit Tests

### state-manager.test.mjs

Tests file-based state management with locking.

**Test cases**:
- Read/write state JSON files
- Acquire lock before write, release after
- Handle concurrent lock attempts (one succeeds, others wait)
- Timeout stale locks (>5 min old)
- Atomic writes (all-or-nothing, no partial files)
- Corrupted state recovery (invalid JSON)

**Coverage**: state-manager.mjs (100% functions, 100% paths)

### phase-tracker.test.mjs

Tests phase gate evaluation and progress tracking.

**Test cases**:
- Gate evaluation: check pass/fail conditions
- Phase transition: gate passes → next phase triggered
- Retry logic: gate fails → retry up to max_retries
- Phase timeout: phase exceeds timeout → escalation
- Progress update: state reflects current phase and iteration

**Coverage**: phase-tracker.mjs (100% functions, 100% paths)

### config.test.mjs

Tests configuration parsing and validation.

**Test cases**:
- Parse pdca-defaults.json, pipeline-phases.json, agent-overrides.json
- Validate against JSON schemas
- Expand presets (full, standard, minimal, auto)
- Agent override application (model per agent, enable/disable)
- Error handling: invalid JSON, missing fields, out-of-range values

**Coverage**: config parsing (100% functions, 100% error paths)

### constants.test.mjs

Tests shared constants.

**Test cases**:
- Verify state paths exist and are normalized
- Check timeout values are reasonable (5-300s)
- Verify lock TTL > timeout
- Agent names match plugin.json registry

**Coverage**: constants (100% values defined and tested)

### hook-detection.test.mjs

Tests keyword detection and argument parsing.

**Test cases**:
- Detect `/blueprint:pdca` and variants
- Parse `--iterations 3 --auto-act`
- Parse `--severity high`
- Parse `--preset full`
- Ignore non-Blueprint keywords
- Handle malformed arguments (missing values, unknown flags)

**Coverage**: blueprint-detect.mjs (100% patterns)

## Integration Tests

### pdca-cycle.test.mjs

Tests complete PDCA iteration.

**Test scenario**:
1. Create PDCA cycle state (id, max_iterations=2)
2. Run Plan phase: call analyst agent
3. Run Do phase: call executor agent (mock file changes)
4. Run Check phase: call verifier agent (mock test results)
5. Run Act phase: call pdca-iterator agent (decide: iterate or complete)
6. If iteration < max: repeat from Plan
7. Finalize: verify cycle marked "done", report written

**Assertions**:
- State transitions correctly: initial → plan → do → check → act → (repeat or done)
- Agent outputs are passed to next phase
- Iteration counter incremented each cycle
- Final report contains all phase results and timing
- Locks released after completion

**Coverage**: Complete PDCA cycle orchestration

### pipeline.test.mjs

Tests full pipeline execution with phase gating.

**Test scenario**:
1. Create pipeline state (preset: "standard" = 6 phases)
2. Phase 0 (requirements): analyst → gate "requirements document exists" → pass
3. Phase 2 (design): design-writer → gate "design document exists" → pass
4. Phase 3 (implementation): executor → gate "code changes committed" → pass
5. Phase 4 (unit-test): tester → gate "unit tests pass" → pass
6. Phase 6 (code-review): reviewer → gate "review approved" → pass
7. Phase 8 (verification): verifier → gate "all checks pass" → pass
8. Finalize: all phases complete, pipeline marked "done"

**Assertions**:
- Phases run in order, no skipping
- Gates block until conditions met (simulated with mock agents)
- Phase timeout triggers retry or escalation
- Final report shows all 6 phases with results

**Coverage**: Complete pipeline orchestration with gates

### concurrent.test.mjs

Tests 2+ workflows running in parallel.

**Test scenario**:
1. Start workflow A (PDCA cycle, cycle-abc)
2. Start workflow B (pipeline, pipeline-def)
3. Verify A and B have separate state files
4. Both run phases in parallel
5. Lock contention test: both try to update state simultaneously
   - One acquires lock, one waits (up to 5s timeout)
   - After first releases, second acquires
6. Verify neither state corrupted, both complete successfully

**Assertions**:
- No state file collision (separate IDs)
- Lock acquisition serializes state updates
- Both workflows complete with correct final state
- No deadlock (timeout prevents indefinite wait)

**Coverage**: Concurrent workflow isolation and lock protocol

### session-recovery.test.mjs

Tests state persistence across session boundaries.

**Test scenario**:
1. Run PDCA cycle to phase 2 (Do phase)
2. Simulate session stop: write checkpoint
3. Create new session
4. Session-loader hook fires: restores active workflows
5. Verify workflow A state loaded correctly
6. User can resume workflow from phase 2
7. Simulate context compaction:
   - PreCompact hook backs up state to checkpoint
   - Verify checkpoint file created
8. New session: recover from checkpoint
9. Verify workflow state identical to pre-compaction

**Assertions**:
- State persisted to `.blueprint/` survives session end
- Session-loader restores state on SessionStart
- Checkpoint created before compaction
- Recovery from checkpoint produces identical state

**Coverage**: State persistence and session recovery

### error-handling.test.mjs

Tests failure scenarios and recovery.

**Test cases**:
- Timeout: phase exceeds timeout_ms → trigger escalation (retry or pause)
- Lock timeout: can't acquire lock in 5s → report contention error
- Missing agent: agent unavailable → fallback to inline prompt
- Invalid config: malformed JSON → fail gracefully with error message
- Corrupted state: state file invalid JSON → skip and reinitialize
- Agent failure: agent reports error → record failure, attempt retry

**Assertions**:
- Workflow continues despite transient failures (retries, fallbacks)
- Permanent failures are reported to user
- State remains consistent after errors
- Locks are released even when errors occur

**Coverage**: Error paths and recovery mechanisms

## Test Execution

### Run All Tests

```bash
npm test
```

### Run Unit Tests Only

```bash
node tests/unit/*.test.mjs
```

### Run Integration Tests Only

```bash
node tests/integration/*.test.mjs
```

### Run Specific Test

```bash
node tests/unit/state-manager.test.mjs
```

## Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| state-manager.mjs | 100% | Critical for data integrity |
| phase-tracker.mjs | 100% | Gate logic must be correct |
| config parsing | 100% | Config validation prevents runtime errors |
| hook detection | 95% | Edge cases less critical |
| agent coordination | 80% | Agent logic tested by agents themselves |
| error handling | 90% | Most paths exercised |

## For AI Agents

### Working In This Directory

- **Test framework**: Node.js built-in `node --test` (no external dependencies)
- **Test file naming**: `*.test.mjs` suffix (required for auto-discovery)
- **Mock agents**: Tests use mock/stub agents that return expected outputs
- **File isolation**: Each test creates temporary state files, cleans up after

### Testing Requirements

- Every new hook/config feature requires a test
- Integration tests must cover happy path and error cases
- Concurrent scenario tests prevent lock contention regressions
- Session recovery tests verify state persistence invariants

### Common Patterns

- **Setup**: Create test state files, mocked agents, temporary directories
- **Action**: Call hook/component with test inputs
- **Assert**: Verify state, files, agent calls, output format
- **Teardown**: Clean up temporary files, restore original state

## Dependencies

### Internal

- All Blueprint components (hooks, config, agents, state manager)
- `config/` - Configuration for test scenarios
- `hooks/lib/` - State manager and utilities

### External

None - uses Node.js built-in `node --test` module.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
