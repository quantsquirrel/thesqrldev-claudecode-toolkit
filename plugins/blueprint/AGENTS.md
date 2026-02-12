<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# claude-blueprint-helix

## Purpose

A structured development methodology plugin for Claude Code that implements PDCA (Plan-Do-Check-Act) cycles, gap analysis, and phased development pipelines. Provides specialized agents, lifecycle hooks, and MCP tools for systematic code quality improvement and strategic development workflows.

## Key Files

| File | Description |
|------|-------------|
| `package.json` | Node.js package manifest with plugin metadata |
| `plugin.json` | Claude Code plugin configuration |
| `CHANGELOG.md` | Version history and release notes |
| `README.md` | Project documentation (English) |
| `README.ko.md` | Project documentation (Korean) |
| `LICENSE` | MIT license file |
| `.gitignore` | Git exclusion patterns |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `agents/` | Specialized agent prompts for analysis and orchestration (see `agents/AGENTS.md`) |
| `config/` | JSON configuration files for PDCA and pipeline customization (see `config/AGENTS.md`) |
| `hooks/` | Claude Code lifecycle hooks for event-driven behavior (see `hooks/AGENTS.md`) |
| `mcp/` | MCP server exposing Blueprint tools via JSON-RPC (see `mcp/AGENTS.md`) |
| `skills/` | User-invocable skills (slash commands) (see `skills/AGENTS.md`) |
| `tests/` | Unit and integration tests (see `tests/AGENTS.md`) |
| `assets/` | Visual assets - hero banner, SVG graphics (see `assets/AGENTS.md`) |
| `docs/` | Architecture documentation and workflow guides (see `docs/AGENTS.md`) |
| `.github/` | GitHub workflows - CI, PR checks, release automation |
| `.claude/` | Session handoff storage (see `.claude/AGENTS.md`) |
| `.claude-plugin/` | Plugin marketplace metadata (see `.claude-plugin/AGENTS.md`) |
| `.omc/` | OMC state management and session data (see `.omc/AGENTS.md`) |
| `.blueprint/` | Active workflow state (PDCA cycles, pipelines) - runtime generated |

## For AI Agents

### Working In This Directory

- **Plugin structure**: This is a Claude Code plugin - `plugin.json` defines the integration points
- **No external dependencies**: Project uses Node.js built-in modules only
- **ESM by default**: Use `.mjs` for hooks and utilities; `.cjs` only for MCP server (compatibility)
- **State management**: Active workflows stored in `.blueprint/` with file-based locking
- **Agent discovery**: Agents loaded from plugin namespace (`blueprint:agent-name`) with inline fallbacks

### Testing Requirements

- Run unit tests: `node tests/unit/*.test.mjs`
- Run integration tests: `node tests/integration/*.test.mjs`
- Test in Claude Code: `claude plugin link .`
- Coverage targets: state management, hook behavior, agent coordination

### Common Patterns

- **Async/await**: Prefer over callbacks for all async operations
- **File locking**: Acquire lock → write state → release lock (see `hooks/lib/state-manager.mjs`)
- **Hook isolation**: Each hook reads from `.blueprint/` independently
- **Agent coordination**: Use phase gates for sequential workflows

## Dependencies

### Internal

- `agents/` → Loaded by skills via plugin namespace or inline prompts
- `config/` → Read by hooks and MCP server for runtime configuration
- `hooks/lib/` → Shared utilities (constants, state manager, I/O)
- `.blueprint/` → Runtime state directory (created on first workflow)

### External

**None** - Zero npm dependencies by design. Uses Node.js built-in modules:
- `fs/promises` - File I/O
- `path` - Path manipulation
- `crypto` - ID generation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ User invokes skill: /blueprint:pdca, /blueprint:gap, etc.   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Hook detects keyword (blueprint-detect.mjs)                 │
│ → Parses arguments, routes to skill handler                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Skill spawns agents (from agents/ or inline prompts)        │
│ → Writes state to .blueprint/{type}-{ID}.json               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Lifecycle hooks track progress (phase-tracker.mjs)          │
│ → Updates state, triggers next phase when gates are met     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ On completion or stop: finalize/cleanup hooks run           │
│ → Archives results, releases locks, resets state            │
└─────────────────────────────────────────────────────────────┘
```

## State Management

**Location**: `.blueprint/`

**File naming**:
- PDCA cycles: `pdca-{ID}.json`
- Pipelines: `pipeline-{ID}.json`
- Locks: `{type}-{ID}.lock`

**Lock protocol**:
1. Acquire lock before state modification
2. Write state atomically
3. Release lock after write
4. Timeout locks after 5 minutes (stale lock cleanup)

**Concurrency**: Multiple cycles/pipelines can run concurrently with ID-based isolation.

## Plugin Integration

**Registration**: `plugin.json` declares:
- Agents: 9 specialized agents (analyst, architect, executor, etc.)
- Skills: 4 user-invocable skills (pdca, gap, pipeline, cancel)
- Hooks: 6 lifecycle hooks (session, compact, tool, stop events)
- MCP Server: Blueprint tools (pdca_status, gap_measure, pipeline_progress)

**Discovery**: Claude Code loads agents via `blueprint:agent-name` namespace. Fallback to inline prompts if agent fails to load.

<!-- MANUAL: Detailed directory documentation below -->

---

## Detailed Directory Documentation

### agents/

Custom agents for specialized analysis and orchestration.

**Files:**
- `analyst.md` - Requirements analysis agent (opus model)
  - Analyzes requirements and produces specifications
  - Identifies edge cases and boundary conditions
  - Defines testable acceptance criteria
  - Used in pipeline requirements phase

- `architect.md` - Architecture design agent (opus model, read-only)
  - Designs component boundaries and interfaces
  - Evaluates technology trade-offs
  - Assesses scalability and security implications
  - No file modifications (analysis only)

- `design-writer.md` - Design document generation agent (sonnet model)
  - Creates structured design documents
  - Documents architecture decisions
  - Produces implementation-ready specifications
  - Used in pipeline design phase

- `executor.md` - Code implementation agent (sonnet model)
  - Implements code changes from design documents
  - Follows existing project patterns and conventions
  - Runs verification checks after implementation
  - Used in pipeline implementation phase

- `gap-detector.md` - Read-only gap analysis agent (opus model)
  - Compares current state vs desired state
  - Identifies gaps by severity (critical/high/medium/low)
  - Generates actionable recommendations
  - No file modifications (analysis only)

- `pdca-iterator.md` - PDCA cycle orchestration agent (sonnet model)
  - Manages Plan-Do-Check-Act iterations
  - Coordinates phase transitions
  - Evaluates cycle completion criteria
  - Decides continuation or termination

- `reviewer.md` - Code review agent (sonnet model, read-only)
  - Comprehensive code review (correctness, security, maintainability)
  - Severity-rated findings with file:line references
  - Design adherence verification
  - No file modifications (review only)

- `tester.md` - Test engineering agent (sonnet model)
  - Designs and implements test strategies
  - Creates unit and integration tests
  - Analyzes coverage and edge cases
  - Used in pipeline test phases

- `verifier.md` - Verification agent (sonnet model, read-only)
  - Verifies implementation against acceptance criteria
  - Runs tests and checks build status
  - Evidence-based PASS/FAIL verdicts
  - No file modifications (verification only)

**Agent Discovery:**
Agents are loaded from the plugin namespace (`blueprint:agent-name`). If a plugin agent is unavailable, inline prompts within skill handlers serve as fallbacks. No external dependencies required.

---

### config/

JSON configuration files for customizing behavior.

**Files:**
- `pdca-defaults.json` - PDCA cycle configuration
  - `max_iterations`: Maximum cycle count (default: 4)
  - `phase_timeout_ms`: Phase timeout in milliseconds (default: 300000)
  - `auto_act`: Whether to automatically proceed after Check phase (default: false)
  - `default_agents`: Agent assignments for each PDCA phase

- `pipeline-phases.json` - Pipeline phase definitions
  - 9 phases: requirements, architecture, design, implementation, unit-test, integration-test, code-review, gap-analysis, verification
  - Each phase has: index, name, agent, gate condition
  - 3 presets: full (9 stages), standard (6 stages), minimal (3 stages)
  - Defaults: preset selection, error handling, retry limits

**Customization:**
Edit these files to adjust workflows, timeouts, or agent assignments.

---

### hooks/

Claude Code hooks for event-driven behavior.

**Files:**
- `hooks.json` - Hook registration manifest
  - Maps hook names to handler scripts
  - Defines execution order and priority

- `blueprint-detect.mjs` - Keyword detection (UserPromptSubmit hook)
  - Detects skill invocation patterns
  - Parses arguments and flags
  - Routes to appropriate skill handler

- `phase-tracker.mjs` - Progress tracking (PostToolUse hook)
  - Monitors agent completion
  - Updates phase progress
  - Triggers next phase when gates are met

- `session-loader.mjs` - State restoration (SessionStart hook)
  - Loads active cycles/pipelines from `.blueprint/`
  - Restores in-progress workflows
  - Displays restoration summary

- `compact-preserver.mjs` - State preservation (PreCompact hook)
  - Backs up active state before compaction
  - Ensures state survives context window compression

- `cycle-finalize.cjs` - Graceful shutdown (Stop hook)
  - Finalizes incomplete cycles
  - Writes completion reports
  - Releases locks

- `session-cleanup.mjs` - Session cleanup (SessionEnd hook)
  - Archives completed workflows
  - Removes stale locks
  - Resets session state

**lib/ subdirectory:**
- `constants.mjs` - Shared constants (state paths, IDs, timeouts)
- `state-manager.mjs` - State file read/write utilities with locking

---

### mcp/

MCP (Model Context Protocol) server for external tool access.

**Files:**
- `blueprint-server.cjs` - JSON-RPC server implementation
  - Exposes 3 tools via MCP:
    - `pdca_status` - Query active PDCA cycle state (ID, phase, iteration, progress)
    - `gap_measure` - Measure gap metrics (severity distribution, closure rate)
    - `pipeline_progress` - Check pipeline progress (current phase, gates passed, ETA)
  - Stateless design (reads from `.blueprint/`)
  - Handles concurrent requests

**Integration:**
Referenced by `.mcp.json` at plugin root. Claude Code loads the server at session start.

---

### skills/

User-invocable skills (slash commands).

**Directory structure:**
```
skills/
├── pdca/
│   └── SKILL.md
├── gap/
│   └── SKILL.md
├── pipeline/
│   └── SKILL.md
└── cancel/
    └── SKILL.md
```

**Skills:**
- `/blueprint:pdca` - Run PDCA improvement cycles
  - Args: `--iterations N`, `--auto-act`
  - Orchestrates Plan → Do → Check → Act loop
  - Continues until max iterations or convergence

- `/blueprint:gap` - Perform gap analysis
  - Args: `--severity [critical|high|medium|low]`
  - Generates gap report with recommendations
  - Read-only (no code changes)

- `/blueprint:pipeline` - Execute dev pipeline
  - Args: `--preset [full|standard|minimal]`
  - Runs phased development workflow
  - Each phase has a gate condition

- `/blueprint:cancel` - Cancel active workflows
  - Args: `--all`, `--cycle-id ID`, `--pipeline-id ID`
  - Graceful termination with cleanup
  - Preserves partial results

**Skill Metadata:**
Each `SKILL.md` contains:
- Trigger patterns (keywords)
- Argument schema
- Agent instructions
- Example usage

---

### tests/

Unit and integration tests.

**Directory structure:**
```
tests/
├── unit/
└── integration/
```

**Unit tests:**
Test individual components (hooks, state manager, agent prompts) in isolation.

**Integration tests:**
Test end-to-end workflows (complete PDCA cycle, pipeline execution, concurrent operations).

**Coverage targets:**
- State management (locking, concurrency, recovery)
- Hook behavior (detection, tracking, cleanup)
- Agent coordination (phase transitions, error handling)

---

## Contributing

1. Add tests for new features
2. Update configuration schemas if adding options
3. Document new hooks/agents in this file
4. Follow existing code style (ESLint config)
5. Ensure zero external dependencies

---

## License

MIT License - see [LICENSE](./LICENSE) for details.
