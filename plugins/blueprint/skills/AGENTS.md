<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# skills/

## Purpose

User-invocable skills (slash commands) for Blueprint workflows. Each skill is a named subdirectory containing skill metadata (`SKILL.md`) and orchestration logic. Skills are triggered by keywords detected in prompts (via blueprint-detect.mjs hook) and coordinate agents, manage state, and provide user feedback.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `pdca/` | PDCA cycle orchestration skill (see `pdca/AGENTS.md`) |
| `gap/` | Gap analysis skill (see `gap/AGENTS.md`) |
| `pipeline/` | Phased development pipeline skill (see `pipeline/AGENTS.md`) |
| `cancel/` | Workflow cancellation skill (see `cancel/AGENTS.md`) |

## Skill Invocation

Users invoke skills via keywords in their prompt:

```
/blueprint:pdca --iterations 3 --auto-act
/blueprint:gap --severity high
/blueprint:pipeline --preset standard
/blueprint:cancel --all
```

The `blueprint-detect.mjs` hook detects these patterns and routes to the appropriate skill handler.

## Skill Structure

Each skill subdirectory contains:

```
skills/{skill-name}/
├── SKILL.md              # Skill metadata & instructions
├── handler.mjs           # Skill implementation (if needed)
└── (agent coordination logic)
```

**SKILL.md format**:
```markdown
---
name: {skill-name}
trigger: /blueprint:{skill-name}
args:
  - name: {arg-name}
    type: string|number|boolean
    required: true|false
    default: {value}
---

Description of what this skill does.

## Agent Instructions
Instructions for agents spawned by this skill.

## Example Usage
/blueprint:{skill-name} --{arg1} {value1} --{arg2}
```

## Skill Summary

### /blueprint:pdca

**Trigger**: `/blueprint:pdca`

**Arguments**:
- `--iterations N` - Max iteration count (1-10, default 4)
- `--auto-act` - Auto-proceed to Act phase after Check (default false)

**Flow**:
1. Initialize PDCA cycle state with ID and iteration counter
2. Call analyst agent to clarify requirements (Plan)
3. Call executor agent to implement changes (Do)
4. Call verifier agent to check against acceptance criteria (Check)
5. Call pdca-iterator agent to evaluate and decide on next iteration (Act)
6. Loop: if iteration count < max and gaps remain, return to Plan
7. Finalize: write cycle report, release state

**State file**: `.blueprint/pdca-{ID}.json`

### /blueprint:gap

**Trigger**: `/blueprint:gap`

**Arguments**:
- `--severity [critical|high|medium|low]` - Filter by severity (default: all)

**Flow**:
1. Initialize gap analysis state with ID
2. Call gap-detector agent (read-only analysis)
3. Gap detector:
   - Scans codebase for gaps vs requirements
   - Categorizes by severity
   - Generates recommendations
4. Format results in report
5. Display findings to user
6. Finalize: write report, no state persistence (read-only)

**State file**: `.blueprint/gap-{ID}.json` (read-only, no checkpoint)

### /blueprint:pipeline

**Trigger**: `/blueprint:pipeline`

**Arguments**:
- `--preset [full|standard|minimal|auto]` - Preset workflow (default: auto)

**Flow**:
1. Expand preset to phase sequence (or compute auto-detect)
2. Initialize pipeline state with phase list
3. For each phase in sequence:
   - Load phase definition from config/pipeline-phases.json
   - Call phase agent
   - Evaluate phase gate condition
   - If gate passes: proceed to next phase
   - If gate fails: retry (up to max_retries) or pause for user input
4. Finalize: write completion report with all phase results

**State file**: `.blueprint/pipeline-{ID}.json`

### /blueprint:cancel

**Trigger**: `/blueprint:cancel`

**Arguments**:
- `--all` - Cancel all active workflows (default: cancel current)
- `--cycle-id ID` - Cancel specific PDCA cycle
- `--pipeline-id ID` - Cancel specific pipeline

**Flow**:
1. Identify workflows to cancel:
   - If `--all`: cancel all from `.blueprint/`
   - If `--cycle-id ID`: cancel specific pdca-{ID}
   - If `--pipeline-id ID`: cancel specific pipeline-{ID}
   - Otherwise: cancel most recent active workflow
2. For each workflow:
   - Update state: `status: "cancelled"`, `cancelled_at: timestamp`
   - Call cycle-finalize hook to gracefully shut down
   - Archive state if requested
3. Release all locks
4. Display summary: workflows cancelled, state archived

**State file**: Updates to `.blueprint/{type}-{ID}.json`, no new file created

## For AI Agents

### Working In This Directory

- **Skill discovery**: Skills are loaded from plugin.json skill registry
- **Nested structure**: Each skill is a subdirectory with its own AGENTS.md
- **Handler pattern**: Skills coordinate agents via plugin interface
- **State management**: Skills create and manage workflow state in `.blueprint/`

### Testing Requirements

- Test skill detection: verify keywords trigger correct skill handler
- Test argument parsing: verify `--arg value` syntax parsed correctly
- Test skill execution: run each skill, verify agents are called in correct order
- Test skill coordination: skills should not interfere with each other when running in parallel
- Test state isolation: each skill run creates unique ID, no state collision

### Common Patterns

- **Skill ID generation**: UUID or timestamp-based (see `constants.mjs`)
- **State initialization**: Skill creates state file with `{ id, type, phase, agents, results }`
- **Agent spawning**: Skill calls agents via plugin namespace or inline prompts
- **Progress tracking**: Skill updates state as agents complete, hooks track progress

## Dependencies

### Internal

- `config/pdca-defaults.json` - PDCA cycle defaults
- `config/pipeline-phases.json` - Pipeline definitions
- `config/agent-overrides.json` - Agent model assignments
- `agents/` - Agent prompts called by skills
- `hooks/lib/state-manager.mjs` - State file I/O and locking

### External

None - skills are orchestration logic using built-in Node.js modules.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
