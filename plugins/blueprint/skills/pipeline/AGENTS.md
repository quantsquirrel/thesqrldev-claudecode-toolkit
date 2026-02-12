<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# skills/pipeline/

## Purpose

Execute structured, phased development workflows with stage gates and error handling. Initialize pipeline state with phase sequence (from preset or auto-detection), spawn agents for each phase sequentially, evaluate phase gates before progressing, implement retry logic (up to 2 retries per phase), support pause/resume workflow, and handle error modes (abort, skip, pause). Coordinates multi-phase waterfall development with clear phase boundaries and auditable progression.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill metadata and instructions (user-facing documentation) |

## Skill Metadata

**Name**: pipeline

**Trigger**: `/blueprint:pipeline "feature description"` with optional arguments

**Arguments**:
- `feature` (required) - Feature description or path to requirements document
- `--preset=X` (optional) - Preset: full, standard, minimal, auto (default: auto)
- `--start-phase=N` (optional) - Start from phase N (requires previous phases completed)
- `--skip-phases=N,N` (optional) - Skip specific phases
- `--on-error=X` (optional) - Error handling: abort, skip, pause (default: pause)
- `--resume=ID` (optional) - Resume paused pipeline by run ID

**Allowed Tools**: Read, Write, Edit, Bash, Glob, Grep, Task

## Pipeline Presets

### Full (9 phases)
Comprehensive pipeline for high-stakes, production-critical features.

Phases:
1. Requirements (analyst) - Acceptance criteria
2. Architecture (architect) - System design
3. Design (design-writer) - Detailed design
4. Implementation (executor) - Code feature
5. Unit Tests (test-engineer) - Unit coverage
6. Integration Tests (test-engineer) - Integration coverage
7. Code Review (code-reviewer) - Quality review
8. Gap Analysis (gap-detector) - Final gap check
9. Verification (verifier) - End-to-end verification

### Standard (6 phases)
Balanced pipeline for typical feature development.

Phases:
1. Requirements (analyst) - Requirements clarity
2. Design (design-writer) - Design document
3. Implementation (executor) - Implementation
4. Unit Tests (test-engineer) - Test coverage
5. Code Review (code-reviewer) - Quality review
6. Verification (verifier) - Final verification

### Minimal (3 phases)
Lightweight pipeline for small changes, bug fixes, prototypes.

Phases:
1. Design (design-writer) - Quick design sketch
2. Implementation (executor) - Implementation
3. Verification (verifier) - Verification

## Workflow Phases

### 0. Auto-Preset Detection

When `--preset=auto` or not specified:

1. Run `complexity-analyzer.analyzeComplexity(workspaceRoot)`
2. Return recommended preset with reasoning
3. Display: `Auto-preset: {preset} ({fileCount} files, {locDelta} LOC) [confidence: {score}%]`
4. Use recommended preset (can override with explicit --preset)

### 1. Initialize Pipeline Run

Create pipeline state:

```json
{
  "id": "pipeline-20260210-143022",
  "feature": "user dashboard with analytics",
  "preset": "standard",
  "status": "running",
  "current_phase": 1,
  "total_phases": 6,
  "on_error": "pause",
  "start_phase": 1,
  "created_at": "2026-02-10T14:30:22Z",
  "updated_at": "2026-02-10T14:30:22Z",
  "phases": [
    {"number": 1, "name": "requirements", "agent": "analyst", "status": "pending", "output": null, "retries": 0},
    {"number": 2, "name": "design", "agent": "design-writer", "status": "pending", "output": null, "retries": 0},
    ...
  ]
}
```

Save to: `.blueprint/pipeline/runs/{pipeline-id}.json`

Add to active index: `.blueprint/pipeline/active-runs.json`

### 2. Execute Phases Sequentially

For each phase in sequence:

**Stage Gate Check**:
- Previous phase `status = "completed"`
- Previous phase output non-null
- Max retries not exceeded (limit: 2)

**Execute Phase**:

```javascript
const phaseConfig = {
  requirements: {agent: "blueprint:analyst", model: "opus"},
  design: {agent: "blueprint:design-writer", model: "sonnet"},
  implementation: {agent: "blueprint:executor", model: "sonnet"},
  "unit-tests": {agent: "blueprint:test-engineer", model: "sonnet"},
  "code-review": {agent: "blueprint:code-reviewer", model: "opus"},
  verification: {agent: "blueprint:verifier", model: "sonnet"}
};

const phase = phases[currentPhase];
const config = phaseConfig[phase.name];

Task(subagent_type=config.agent,
     model=config.model,
     prompt="Pipeline phase: {phase.name}\nFeature: {feature}\nPrevious output: {previous_output}\n{phase_instructions}")
```

**Record Output**:

```bash
jq --arg output "$output" \
   '.phases['"$phaseNum"'].status = "completed" |
    .phases['"$phaseNum"'].output = $output |
    .updated_at = now' \
   state.json > tmp && mv tmp state.json
```

### 3. Error Handling

When phase fails:

**--on-error=abort** (stop immediately):
```bash
jq '.status = "failed" | .current_phase = '"$phaseNum" state.json > tmp && mv tmp state.json
# Exit with error
```

**--on-error=skip** (skip failed phase, continue):
```bash
jq '.phases['"$phaseNum"'].status = "skipped" | .current_phase = ('"$phaseNum"' + 1)' \
   state.json > tmp && mv tmp state.json
# Continue to next phase
```

**--on-error=pause** (pause for manual intervention):
```bash
jq '.status = "paused" | .current_phase = '"$phaseNum" state.json > tmp && mv tmp state.json
# Display: "Pipeline paused at phase N. Resume with: /blueprint:pipeline --resume={id}"
```

### 4. Retry Logic

Each phase allows up to 2 retries:

```javascript
if (phase.status === 'failed' && phase.retries < 2) {
  phase.retries++;
  phase.status = 'pending';
  Task(
    subagent_type=config.agent,
    prompt="RETRY #{phase.retries}: Previous attempt failed.\nError: {error}\n{original_prompt}"
  );
}
```

After 2 retries, phase fails permanently (triggers on-error handler).

### 5. Resume Paused Pipeline

Command: `/blueprint:pipeline --resume=pipeline-20260210-143022`

1. Load state from `.blueprint/pipeline/runs/{id}.json`
2. Verify status = "paused"
3. Resume from `current_phase`
4. Continue execution

### 6. Finalize

When all phases complete:

```bash
jq '.status = "completed" | .completed_at = now' state.json > tmp && mv tmp state.json

# Archive to history
cp state.json .blueprint/pipeline/history/{id}-{timestamp}.json

# Remove from active index
jq --arg id "{id}" '.runs = [.runs[] | select(.id != $id)]' \
   .blueprint/pipeline/active-runs.json > tmp && mv tmp .blueprint/pipeline/active-runs.json
```

Generate and display summary report.

## Output Format

```
## Pipeline Complete: {pipeline-id}

### Feature
{feature_description}

### Preset
{preset} ({N} phases)

### Execution Summary
- Status: completed|failed|paused
- Started: {timestamp}
- Completed: {timestamp}
- Duration: {time}
- Phases: {completed} completed, {skipped} skipped, {failed} failed

### Phase Results

**Phase 1: Requirements** ✓
- Agent: analyst (opus)
- Status: completed
- Retries: 0
- Output: [summary]

[... all phases ...]

### Artifacts
- Pipeline state: .blueprint/pipeline/runs/{id}.json
- Phase outputs: [links to generated docs/code]

### Final Verification
- Build: PASS
- Tests: 42 passed
- Coverage: 85%
- All acceptance criteria: MET
```

## Phase-Specific Instructions

### Requirements Phase

```
Analyze feature request and produce:
- Clear, unambiguous requirements
- Testable acceptance criteria
- Edge cases and constraints
- Dependencies on other systems
```

### Architecture Phase

```
Design system architecture:
- Component boundaries and interfaces
- Data flow diagrams
- Technology choices with trade-offs
- Security and scalability considerations
```

### Design Phase

```
Create detailed design document:
- API signatures and data structures
- Algorithm choices
- Error handling strategy
- File structure and module organization
```

### Implementation Phase

```
Implement the design:
- Follow design doc exactly
- Write clean, maintainable code
- Include inline comments for complex logic
- Ensure all files pass lsp_diagnostics
```

### Unit Tests Phase

```
Create unit tests:
- Cover all public functions
- Test edge cases from requirements
- Achieve >80% code coverage
- Ensure tests are fast and isolated
```

### Integration Tests Phase

```
Create integration tests:
- Test component interactions
- Test external API integrations
- Verify end-to-end workflows
- Include error scenarios
```

### Code Review Phase

```
Comprehensive code review:
- Check adherence to design
- Identify potential bugs
- Verify test coverage
- Assess maintainability
```

### Gap Analysis Phase

```
Final gap check:
- Compare implementation vs requirements
- Identify missing acceptance criteria
- Check for technical debt
- Verify all edge cases covered
```

### Verification Phase

```
End-to-end verification:
- Run full test suite
- Verify all acceptance criteria met
- Check build passes
- Ensure no regression
```

## For AI Agents

### Working In This Directory

- **One file per skill**: SKILL.md contains all metadata
- **Sequential phase execution**: Each phase waits for previous to complete
- **State persistence**: State file updated after each phase
- **Error recovery**: Failed phases can retry (up to 2) or pause for manual fix
- **Resume capability**: Paused pipelines can be resumed from current phase

### Testing Requirements

- Test auto-preset detection: verify preset selected based on workspace complexity
- Test full pipeline: run all phases, verify correct sequence
- Test stage gates: verify phase cannot start until previous completed
- Test retry logic: verify failed phase retried up to 2 times
- Test error handling: abort/skip/pause modes work correctly
- Test pause/resume: pipeline can be paused, resumed from same phase
- Test skip phases: `--skip-phases=2,3` skips those phases
- Test concurrent pipelines: different pipeline IDs, no state collision

### Common Patterns

**Initialize pipeline**:
```javascript
const pipelineId = `pipeline-${Date.now()}`;
const preset = selectedPreset || 'standard';
const phases = PHASE_DEFINITIONS[preset];
const state = {
  id: pipelineId,
  feature: userFeature,
  preset,
  status: 'running',
  current_phase: 1,
  phases: phases.map((p, i) => ({ ...p, number: i+1, status: 'pending', retries: 0 }))
};
await updateState(`.blueprint/pipeline/runs/${pipelineId}.json`, state);
```

**Execute phase**:
```javascript
const config = PHASE_CONFIG[phase.name];
const output = await Task(
  subagent_type=config.agent,
  model=config.model,
  prompt=`Pipeline phase: ${phase.name}...\n${phaseInstructions[phase.name]}`
);
```

**Check gate before next phase**:
```javascript
if (phases[i-1].status !== 'completed' || !phases[i-1].output) {
  throw new Error(`Phase gate failed: ${phases[i-1].name} not completed`);
}
```

**Update state after phase**:
```javascript
state.phases[phaseNum].status = 'completed';
state.phases[phaseNum].output = output;
state.current_phase = phaseNum + 1;
await updateState(statePath, state);
```

## Output Schema

Each pipeline phase SHOULD produce structured output:

```json
{
  "phase_output": {
    "type": "object",
    "required": ["phase_name", "status", "output"],
    "properties": {
      "phase_name": { "type": "string" },
      "status": { "type": "string", "enum": ["completed", "failed", "skipped"] },
      "retries": { "type": "integer", "minimum": 0 },
      "output": { "type": "string" },
      "artifacts": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["document", "code", "test", "report"] },
            "path": { "type": "string" }
          }
        }
      }
    }
  }
}
```

## State File Locations

**Active pipelines**:
- Pipeline state: `.blueprint/pipeline/runs/{pipeline-id}.json`
- Active index: `.blueprint/pipeline/active-runs.json`

**History**:
- Completed pipeline: `.blueprint/pipeline/history/{pipeline-id}-{timestamp}.json`

## Dependencies

### Internal

- `hooks/lib/state-manager.mjs` - State file I/O with locking
- `hooks/lib/io.mjs` - Atomic file operations
- `hooks/lib/complexity-analyzer.mjs` - Auto-preset detection
- `hooks/lib/logger.mjs` - Logging

### External

- None - uses Node.js built-in modules only

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
