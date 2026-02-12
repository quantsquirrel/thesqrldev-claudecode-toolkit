<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# tests/unit/

## Purpose

Component-level unit tests for Blueprint plugin modules. Tests verify state management with file-based locking, frontmatter parsing (agent/skill metadata), configuration validation, constants consistency, hook I/O operations, MCP server integration, and core utilities. Each test file targets a specific module with comprehensive happy path and error case coverage.

## Key Files

| File | Description |
|------|-------------|
| `state-manager.test.mjs` | File I/O, locking, atomic writes, JSON parsing |
| `agent-frontmatter.test.mjs` | Agent metadata parsing from frontmatter blocks |
| `agent-resolution.test.mjs` | Agent name resolution against plugin registry |
| `skill-frontmatter.test.mjs` | Skill metadata parsing from SKILL.md frontmatter |
| `config-validation.test.mjs` | Config JSON schema validation, preset expansion |
| `constants.test.mjs` | Shared constants consistency and values |
| `hooks-io.test.mjs` | Hook file I/O operations, error scenarios |
| `mcp-server.test.mjs` | MCP server integration and tool availability |

## Test Structure

```
tests/unit/
├── state-manager.test.mjs      # State persistence, locking
├── agent-frontmatter.test.mjs   # Agent metadata extraction
├── agent-resolution.test.mjs    # Agent registry lookups
├── skill-frontmatter.test.mjs    # Skill metadata extraction
├── config-validation.test.mjs    # Config parsing/validation
├── constants.test.mjs            # Constant values
├── hooks-io.test.mjs             # Hook I/O utilities
└── mcp-server.test.mjs           # MCP integration
```

## Test Files

### state-manager.test.mjs

Tests file-based state management with locking and atomic writes.

**Test cases**:
- Read state from JSON file
- Write state with lock acquisition
- Concurrent access: one acquires lock, one waits
- Lock timeout after TTL (5 min)
- Atomic write: all-or-nothing (no partial files)
- Handle corrupted JSON: return default state with warning
- Handle missing file: create new state
- Lock released even on error (finally block)
- Update state with merge semantics

**Coverage**: 100% functions, 100% paths

### agent-frontmatter.test.mjs

Tests parsing agent metadata from frontmatter blocks.

**Test cases**:
- Parse valid frontmatter: extract name, description, allowed_tools
- Parse frontmatter with optional fields
- Handle missing frontmatter (file has no metadata block)
- Handle malformed frontmatter (invalid YAML)
- Extract allowed_tools array
- Extract triggers/keywords list
- Handle multiline descriptions
- Preserve order of tools/keywords

**Sample frontmatter**:
```markdown
---
name: executor
description: "Implements code changes from specifications."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
triggers: [implement, code, execute]
---
```

**Coverage**: 100% parsing paths

### agent-resolution.test.mjs

Tests agent name resolution against plugin registry.

**Test cases**:
- Resolve known agent: return agent object
- Resolve unknown agent: return null or throw
- Case-insensitive lookup
- Handle registry load errors
- Cache registry in memory for performance
- Return agent object with: name, model, description, allowed_tools

**Coverage**: 100% lookup paths

### skill-frontmatter.test.mjs

Tests parsing skill metadata from SKILL.md frontmatter.

**Test cases**:
- Parse valid SKILL.md frontmatter
- Extract: name, description, arguments, allowed_tools
- Parse arguments array with type/required/default
- Handle missing optional fields
- Handle malformed argument specifications
- Extract user-invocable flag
- Preserve argument order

**Sample frontmatter**:
```markdown
---
name: pdca
description: "Use when you want iterative improvement..."
argument-hint: <task> [--max-iterations=N]
allowed-tools: [Read, Write, Edit, Task]
user-invocable: true
---
```

**Coverage**: 100% parsing paths

### config-validation.test.mjs

Tests configuration file parsing and validation.

**Test cases**:
- Parse valid pdca-defaults.json
- Parse valid pipeline-phases.json
- Parse valid agent-overrides.json
- Validate against JSON schemas
- Reject invalid JSON
- Reject missing required fields
- Reject out-of-range values
- Expand preset: full → phase list
- Expand preset: standard → phase list
- Expand preset: minimal → phase list
- Handle missing config file (use defaults)
- Apply agent overrides (model per agent)
- Merge partial overrides with defaults

**Coverage**: 100% parsing and validation

### constants.test.mjs

Tests shared constants consistency.

**Test cases**:
- Verify STATE_PATHS defined and normalized
- Verify LOCK_TTL_MS is reasonable (> 1 minute)
- Verify HOOK_TIMEOUT_MS per event type
- Verify hook timeouts < LOCK_TTL_MS
- Verify AGENT_NAMES match plugin.json registry
- Verify PRESET_DEFINITIONS complete (full, standard, minimal)
- Verify no duplicate constants
- Verify path separators consistent (forward slashes)

**Coverage**: 100% constant values

### hooks-io.test.mjs

Tests hook file I/O utilities.

**Test cases**:
- Safe write: create file via temp + rename
- Ensure directory: create parents recursively
- Atomic rename: POSIX semantics
- Read JSON: parse valid JSON
- Read JSON: handle invalid JSON gracefully
- Read JSON: handle missing file
- Handle permission errors
- Handle disk full errors
- Clean up temp files on error

**Coverage**: 100% I/O paths, error scenarios

### mcp-server.test.mjs

Tests MCP server integration.

**Test cases**:
- Connect to MCP server (if available)
- Check available tools list
- Verify tool availability: ask_codex, ask_gemini
- Handle MCP server unavailable (fallback)
- Verify tool parameters valid
- Test tool invocation (mock)
- Handle tool errors gracefully

**Coverage**: Integration with MCP, fallback paths

## Test Execution

### Run All Tests

```bash
npm test
```

### Run Unit Tests Only

```bash
node tests/unit/*.test.mjs
```

Or individually:

```bash
node tests/unit/state-manager.test.mjs
node tests/unit/agent-frontmatter.test.mjs
# etc...
```

### Run with Coverage Report

```bash
npm test -- --coverage
```

## Coverage Goals

| Module | Target | Rationale |
|--------|--------|-----------|
| state-manager | 100% | Critical for data integrity, must test all paths |
| frontmatter parsing | 100% | Metadata extraction must be reliable |
| config validation | 100% | Bad config causes runtime failures |
| constants | 100% | All values must be correct |
| hooks-io | 95% | Most error paths exercised, edge cases may vary |
| MCP integration | 85% | Depends on external service availability |

## For AI Agents

### Working In This Directory

- **Test framework**: Node.js built-in `node --test` module (no dependencies)
- **Test file naming**: `*.test.mjs` suffix required for discovery
- **Isolation**: Each test creates temporary files, cleans up after
- **No external services**: Use mocks/stubs for external dependencies
- **Deterministic**: Tests should produce consistent results across runs

### Testing Requirements

- Every test file must import module under test
- Every test must have clear setup → action → assert phases
- Tests must clean up temporary files
- Error paths must be tested alongside happy paths
- State files must be isolated per test (different IDs)

### Common Patterns

**Setup test directory**:
```javascript
import { mkdir, rm } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';

const testDir = join(tmpdir(), `blueprint-test-${Date.now()}`);
await mkdir(testDir, { recursive: true });
```

**Teardown**:
```javascript
afterEach(async () => {
  await rm(testDir, { recursive: true });
});
```

**Assert state file**:
```javascript
import { readFile } from 'fs/promises';
const content = await readFile(statePath, 'utf-8');
const state = JSON.parse(content);
assert.equal(state.status, 'completed');
```

**Mock agent call**:
```javascript
const mockAgent = {
  name: 'executor',
  model: 'sonnet',
  call: async (prompt) => ({ output: 'mock result' })
};
```

## Test Execution Order

Tests should be independent and runnable in any order. Use unique IDs for state files to prevent collisions:

```javascript
const stateId = `test-${Date.now()}-${Math.random()}`;
const statePath = `.blueprint/pdca/cycles/${stateId}.json`;
```

## Dependencies

### Internal

All Blueprint modules:
- `hooks/lib/*.mjs` - Utilities being tested
- `config/*.json` - Configuration files
- `agents/` - Agent metadata
- `skills/*/SKILL.md` - Skill metadata

### External

- Node.js built-in `assert` module
- Node.js built-in `fs/promises` module
- Node.js built-in `test` module (no external dependencies)

## Limitations

**Cannot test**:
- Actual agent execution (use integration tests for end-to-end)
- Real MCP server calls (use mocks/stubs)
- File system permission errors on all platforms (platform-dependent)
- Network I/O (use mocks)

**Testing hooks**:
- Hook execution timing and events are tested in integration tests
- Unit tests verify hook helper functions in isolation

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
