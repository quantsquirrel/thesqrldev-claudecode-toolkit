# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-12

### Added

#### Pipeline Auto-Preset
- 3-axis complexity analyzer (`hooks/lib/complexity-analyzer.mjs`)
  - Analyzes git diff to compute fileCount, LOC delta, moduleCount
  - Automatic preset recommendation: minimal / standard / full
  - Confidence score and human-readable reasoning
- `--preset=auto` is now the default for `/blueprint:pipeline`
- Users can always override with explicit `--preset=minimal|standard|full`

#### Debug Logging
- Dual-mode logging utility (`hooks/lib/logger.mjs`)
  - Default: silently writes to `.blueprint/debug.log` (never blocks Claude Code)
  - Strict mode: `BLUEPRINT_HOOK_STRICT=1` exits with code 1 on errors (CI opt-in)
- All 6 hooks now log errors and startup info instead of failing silently

#### MCP Write Tools
- `pdca_update` - Update PDCA cycle phase or status
- `pipeline_advance` - Advance pipeline to next phase or update phase status
- Buffered write via `pending_updates.json` (merged by cycle-finalize hook)

#### Code Deduplication
- Extracted shared `readStdin()` to `hooks/lib/io.mjs` (was duplicated in 5 ESM hooks)
- ~120 lines of duplicated code removed

#### Standalone Agent Suite (OMC-Independence)
- 9 custom agents for fully self-contained operation:
  - `blueprint:analyst` (opus) - Requirements analysis and acceptance criteria
  - `blueprint:executor` (sonnet) - Code implementation from design documents
  - `blueprint:verifier` (sonnet) - Evidence-based verification against acceptance criteria
  - `blueprint:architect` (opus) - Architecture design and trade-off evaluation (read-only)
  - `blueprint:reviewer` (sonnet) - Comprehensive code review with severity ratings (read-only)
  - `blueprint:tester` (sonnet) - Test strategy design and implementation
  - `blueprint:gap-detector` (opus) - Deep gap analysis
  - `blueprint:design-writer` (sonnet) - Design document generation
  - `blueprint:pdca-iterator` (sonnet) - PDCA cycle orchestration

#### Per-Project Agent Override
- `config/agent-overrides.json` for per-project agent customization
  - Override model selection per agent
  - Disable specific agents
  - Custom agent routing

#### Output Schema Validation
- Added output schema definitions to PDCA, Gap Analysis, and Pipeline SKILL.md
  - Structured JSON schemas for phase outputs
  - Enables downstream validation of agent results

#### Namespace Migration
- Replaced all `oh-my-claudecode:*` agent references with `blueprint:*`
- Migrated state directory from `.omc/blueprint/` to `.blueprint/`
- Renamed internal `findOmcRoot()` to `findBlueprintRoot()`
- Removed OMC fallback patterns from skill workflows
- Plugin now operates fully independently without external plugin dependencies

#### Core Skills
- PDCA cycle skill (`/blueprint:pdca`) with iterative improvement loops
  - Plan-Do-Check-Act methodology for continuous refinement
  - Configurable iteration count (default: 4 cycles)
  - Auto-act mode for autonomous progression
  - Phase timeout protection (5 minutes per phase)
- Gap Analysis skill (`/blueprint:gap`) with severity-based reporting
  - Current vs desired state comparison
  - Severity classification (critical/high/medium/low)
  - Actionable recommendations
  - Read-only analysis (no code modifications)
- Dev Pipeline skill (`/blueprint:pipeline`) with 3 presets
  - Full preset: 9-stage comprehensive workflow
  - Standard preset: 6-stage balanced workflow (default)
  - Minimal preset: 3-stage rapid iteration
  - Gate-based progression (each phase has entry criteria)
- Cancel skill (`/blueprint:cancel`) for graceful workflow termination
  - Cancel all active workflows with `--all`
  - Cancel specific cycle with `--cycle-id ID`
  - Cancel specific pipeline with `--pipeline-id ID`
  - Cleanup and lock release

#### Custom Agents
- `gap-detector` (opus model) for deep gap analysis
  - Read-only state examination
  - Multi-dimensional gap classification
  - Evidence-based recommendations
- `design-writer` (sonnet model) for design document generation
  - Architecture decision records
  - Implementation specifications
  - Structured documentation
- `pdca-iterator` (sonnet model) for PDCA cycle orchestration
  - Phase coordination
  - Iteration management
  - Convergence detection

#### Hooks
- `UserPromptSubmit` hook (blueprint-detect.mjs)
  - Keyword-based skill detection
  - Argument parsing and validation
  - Skill routing
- `PostToolUse` hook (phase-tracker.mjs)
  - Agent completion detection
  - Progress tracking
  - Phase transition triggering
- `SessionStart` hook (session-loader.mjs)
  - Active workflow restoration
  - State recovery
  - Session resumption
- `PreCompact` hook (compact-preserver.mjs)
  - State backup before compaction
  - Context window compression safety
- `Stop` hook (cycle-finalize.cjs)
  - Graceful shutdown
  - Partial result preservation
  - Lock cleanup
- `SessionEnd` hook (session-cleanup.mjs)
  - Workflow archival
  - Stale lock removal
  - Session state reset

#### MCP Server
- `blueprint-server.cjs` with 3 tools
  - `pdca_status` - Query PDCA cycle state (ID, phase, iteration, progress)
  - `gap_measure` - Measure gap metrics (severity distribution, closure rate)
  - `pipeline_progress` - Check pipeline progress (current phase, gates passed, ETA)
- JSON-RPC protocol implementation
- Stateless design with file-based storage
- Concurrent request handling

#### State Management
- ID-based isolation for concurrent workflows
  - Each cycle/pipeline has unique ID
  - Independent state files per workflow
  - No interference between concurrent operations
- Lock protocol for concurrency safety
  - Atomic state writes
  - Timeout-based stale lock cleanup (5 minutes)
  - Deadlock prevention
- Session isolation
  - State stored at `.blueprint/`
  - Per-session cleanup
  - Cross-session persistence

#### Agent Discovery
- Plugin agent loading (`blueprint:agent-name`)
- Fallback to inline prompts for robustness
- Inline prompt fallback for robustness
- Graceful degradation when agents unavailable

#### Configuration
- `config/pdca-defaults.json` for PDCA customization
  - Maximum iterations
  - Phase timeouts
  - Auto-act behavior
  - Default agent assignments
- `config/pipeline-phases.json` for pipeline definition
  - 9 phases with agents and gates
  - 3 presets (full/standard/minimal)
  - Auto-preset enabled by default
  - Error handling options
  - Retry limits

#### Documentation
- README.md with comprehensive usage guide
- README.ko.md (Korean translation)
- AGENTS.md with directory-by-directory breakdown
- CHANGELOG.md (this file)

#### Development
- Zero external dependencies (Node.js built-ins only)
- ESM modules for hooks and utilities
- CommonJS for MCP server (compatibility)
- Unit test structure
- Integration test structure

### Architecture Decisions

#### Why Zero Dependencies?
- Minimal installation footprint
- Faster startup time
- No version conflicts
- Easier maintenance
- Better security posture

#### Why ID-based State Isolation?
- Multiple workflows can run concurrently
- No state interference
- Easy cleanup and archival
- Clear ownership and lifecycle

#### Why Lock Protocol?
- Prevents race conditions in concurrent access
- Ensures atomic state updates
- Timeout prevents deadlock from crashed processes
- File-based locks work across processes

#### Why Agent Fallbacks?
- Plugin remains functional even if agents fail to load
- Graceful degradation rather than hard failure
- Users can still invoke skills manually
- Inline prompts as last resort

### Breaking Changes

None (initial release)

### Deprecated

None (initial release)

### Security

- No external network access (local file operations only)
- State files scoped to project directory
- Lock files prevent concurrent modification
- No credential storage

---

[1.0.0]: https://github.com/quantsquirrel/claude-blueprint-helix/releases/tag/v1.0.0
