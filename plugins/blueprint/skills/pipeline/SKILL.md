---
name: pipeline
description: "Use when you want to run a structured development pipeline from requirements to verification. Triggers: dev pipeline, structured development, waterfall, phased development."
argument-hint: <feature> [--preset=full|standard|minimal] [--start-phase=N] [--skip-phases=N,N] [--on-error=abort|skip|pause] [--resume=ID]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
user-invocable: true
---

# Development Pipeline Skill

Execute structured, phased development workflows with stage gates and error handling.

## When to Use

Use this skill when:
- You want systematic, waterfall-style development with clear phase boundaries
- Each phase depends on the previous phase's output
- You need auditable progression through development stages
- You want to ensure no phase is skipped accidentally

Do NOT use when:
- Rapid iteration is more important than phase discipline
- Requirements are unclear (use analyst first)
- Single-phase work (just call the agent directly)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `feature` | Yes | Feature description or path to requirements doc |
| `--preset=X` | No | Pipeline preset: `full`, `standard`, `minimal`, `auto` (default: auto) |
| `--start-phase=N` | No | Start from phase N (requires previous phases completed) |
| `--skip-phases=N,N` | No | Skip specific phases (use cautiously) |
| `--on-error=X` | No | Error handling: `abort`, `skip`, `pause` (default: pause) |
| `--resume=ID` | No | Resume paused pipeline by run ID |

Example: `/blueprint:pipeline "user dashboard with analytics" --preset=standard`

## Pipeline Presets

### Full (9 phases)
Comprehensive pipeline with all quality gates.

**Phases:**
1. **Requirements** (analyst) - Clarify requirements, define acceptance criteria
2. **Architecture** (architect) - System design, component boundaries
3. **Design** (design-writer) - Detailed design document
4. **Implementation** (executor) - Code the feature
5. **Unit Tests** (test-engineer) - Unit test coverage
6. **Integration Tests** (test-engineer) - Integration test coverage
7. **Code Review** (code-reviewer) - Comprehensive review
8. **Gap Analysis** (gap-detector) - Final gap check vs requirements
9. **Verification** (verifier) - End-to-end verification

Use when: High-stakes features, production-critical code

### Standard (6 phases)
Balanced pipeline for typical feature work.

**Phases:**
1. **Requirements** (analyst) - Requirements clarity
2. **Design** (design-writer) - Design document
3. **Implementation** (executor) - Code implementation
4. **Unit Tests** (test-engineer) - Test coverage
5. **Code Review** (code-reviewer) - Quality review
6. **Verification** (verifier) - Final verification

Use when: Most feature development, standard workflows

### Minimal (3 phases)
Lightweight pipeline for simple changes.

**Phases:**
1. **Design** (design-writer) - Quick design sketch
2. **Implementation** (executor) - Implementation
3. **Verification** (verifier) - Verification

Use when: Bug fixes, small features, prototypes

## Workflow

### 0. Auto-Preset Detection (when --preset=auto or no preset specified)

When preset is `auto` or omitted:
1. Run complexity analysis on the current workspace
2. Print reasoning: "Auto-preset: {preset} ({fileCount} files, {locDelta} LOC, {moduleCount} modules) [confidence: {score}%]"
3. Use the recommended preset
4. User can always override with explicit --preset=minimal|standard|full

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
  "created_at": "2026-02-10T14:30:22Z",
  "phases": [
    {"number": 1, "name": "requirements", "agent": "analyst", "status": "running", "output": null, "retries": 0},
    {"number": 2, "name": "design", "agent": "design-writer", "status": "pending", "output": null, "retries": 0},
    {"number": 3, "name": "implementation", "agent": "executor", "status": "pending", "output": null, "retries": 0},
    {"number": 4, "name": "unit-tests", "agent": "test-engineer", "status": "pending", "output": null, "retries": 0},
    {"number": 5, "name": "code-review", "agent": "code-reviewer", "status": "pending", "output": null, "retries": 0},
    {"number": 6, "name": "verification", "agent": "verifier", "status": "pending", "output": null, "retries": 0}
  ]
}
```

Save to: `.blueprint/pipeline/runs/{pipeline-id}.json`

### 2. Execute Phases Sequentially
For each phase:

**Stage Gate Check:**
- Previous phase must have `status="completed"`
- Previous phase output must be non-null
- Max retries not exceeded (2 retries per phase)

**Execute Phase:**
```javascript
const phaseConfig = {
  requirements: {agent: "blueprint:analyst", model: "opus"},
  architecture: {agent: "blueprint:architect", model: "opus"},
  design: {agent: "blueprint:design-writer", model: "sonnet"},
  implementation: {agent: "blueprint:executor", model: "sonnet"},
  "unit-tests": {agent: "blueprint:test-engineer", model: "sonnet"},
  "integration-tests": {agent: "blueprint:test-engineer", model: "sonnet"},
  "code-review": {agent: "blueprint:code-reviewer", model: "opus"},
  "gap-analysis": {agent: "blueprint:gap-detector", model: "opus"},
  verification: {agent: "blueprint:verifier", model: "sonnet"}
};

const phase = phases[currentPhase];
const config = phaseConfig[phase.name];

Task(subagent_type=config.agent,
     model=config.model,
     prompt="Pipeline phase: {phase.name}\nFeature: {feature}\nPrevious phase output: {previous_output}\n{phase_specific_instructions}")
```

**Record Output:**
```bash
jq --arg output "$phase_output" \
   '.phases['"$phase_num"'].status = "completed" |
    .phases['"$phase_num"'].output = $output |
    .updated_at = now' \
   state.json > tmp && mv tmp state.json
```

### 3. Error Handling
When a phase fails:

**--on-error=abort** (stop immediately):
```bash
jq '.status = "failed" | .current_phase = '"$phase_num" state.json > tmp && mv tmp state.json
exit 1
```

**--on-error=skip** (skip failed phase, continue):
```bash
jq '.phases['"$phase_num"'].status = "skipped" |
    .current_phase = ('"$phase_num"' + 1)' state.json > tmp && mv tmp state.json
# Continue to next phase
```

**--on-error=pause** (pause for manual intervention):
```bash
jq '.status = "paused" | .current_phase = '"$phase_num" state.json > tmp && mv tmp state.json
echo "Pipeline paused at phase $phase_num. Resume with: /blueprint:pipeline --resume={id}"
```

### 4. Retry Logic
Each phase allows up to 2 retries:

```javascript
if (phase.status === "failed" && phase.retries < 2) {
  phase.retries++;
  phase.status = "pending";
  // Re-run phase with refined prompt including previous error
  Task(subagent_type=config.agent,
       prompt="RETRY #{phase.retries}: Previous attempt failed.\nError: {error}\n{original_prompt}")
}
```

### 5. Resume Paused Pipeline
```bash
/blueprint:pipeline --resume=pipeline-20260210-143022
```

- Load state from `.blueprint/pipeline/runs/{id}.json`
- Verify status is "paused"
- Resume from `current_phase`
- Continue execution

### 6. Finalize
When all phases complete:

```bash
jq '.status = "completed" |
    .completed_at = now' state.json > tmp && mv tmp state.json

# Archive to history
cp state.json .blueprint/pipeline/history/{id}-{timestamp}.json
```

## Phase-Specific Instructions

### Requirements Phase (analyst)
```
Analyze feature request and produce:
- Clear, unambiguous requirements
- Acceptance criteria (testable)
- Edge cases and constraints
- Dependencies on other systems
```

### Architecture Phase (architect)
```
Design system architecture:
- Component boundaries and interfaces
- Data flow diagrams
- Technology choices with trade-offs
- Security and scalability considerations
```

### Design Phase (design-writer)
```
Create detailed design document:
- API signatures and data structures
- Algorithm choices
- Error handling strategy
- File structure and module organization
```

### Implementation Phase (executor)
```
Implement the design:
- Follow design doc exactly
- Write clean, maintainable code
- Include inline comments for complex logic
- Ensure all files pass lsp_diagnostics
```

### Unit Tests Phase (test-engineer)
```
Create unit tests:
- Cover all public functions
- Test edge cases from requirements
- Achieve >80% code coverage
- Ensure tests are fast and isolated
```

### Integration Tests Phase (test-engineer)
```
Create integration tests:
- Test component interactions
- Test external API integrations
- Verify end-to-end workflows
- Include error scenarios
```

### Code Review Phase (code-reviewer)
```
Comprehensive code review:
- Check adherence to design
- Identify potential bugs
- Verify test coverage
- Assess maintainability
```

### Gap Analysis Phase (gap-detector)
```
Final gap check:
- Compare implementation vs requirements
- Identify missing acceptance criteria
- Check for technical debt
- Verify all edge cases covered
```

### Verification Phase (verifier)
```
End-to-end verification:
- Run full test suite
- Verify all acceptance criteria met
- Check build passes
- Ensure no regression
```

## Output Format

```
## Pipeline Complete: {pipeline-id}

### Feature
{feature}

### Preset
{preset} ({N} phases)

### Execution Summary
- Status: {completed|failed|paused}
- Started: {timestamp}
- Completed: {timestamp}
- Duration: {duration}
- Phases: {N} completed, {M} skipped, {K} failed

### Phase Results

**Phase 1: Requirements** ✓
- Agent: analyst (opus)
- Status: completed
- Retries: 0
- Output: [summary]

**Phase 2: Design** ✓
- Agent: design-writer (sonnet)
- Status: completed
- Retries: 1
- Output: [summary]

[... all phases ...]

### Artifacts
- Pipeline state: `.blueprint/pipeline/runs/{id}.json`
- Phase outputs: [links to generated docs/code]

### Final Verification
- Build: [command] -> PASS
- Tests: [command] -> 42 passed
- Coverage: 85%
- All acceptance criteria: MET
```

## Output Schema

Each pipeline phase produces structured output that can be validated downstream.

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
  },
  "pipeline_result": {
    "type": "object",
    "required": ["id", "status", "phases_completed", "phases_total"],
    "properties": {
      "id": { "type": "string", "pattern": "^pipeline-\\d{8}-\\d{6}$" },
      "feature": { "type": "string" },
      "preset": { "type": "string", "enum": ["full", "standard", "minimal"] },
      "status": { "type": "string", "enum": ["completed", "failed", "paused"] },
      "phases_completed": { "type": "integer", "minimum": 0 },
      "phases_total": { "type": "integer", "minimum": 1 },
      "phases_skipped": { "type": "integer", "minimum": 0 },
      "phases_failed": { "type": "integer", "minimum": 0 },
      "started_at": { "type": "string", "format": "date-time" },
      "completed_at": { "type": "string", "format": "date-time" }
    }
  }
}
```

Agents SHOULD structure their output to match these schemas. Downstream consumers MAY validate against them.

## Common Issues

| Issue | Solution |
|-------|----------|
| Phase fails repeatedly | Use --on-error=pause, manually fix, then --resume |
| Pipeline too long | Use --preset=minimal or --skip-phases |
| Need to restart from middle | Use --start-phase=N (ensure previous phases already completed) |
| Agent not available | Pipeline uses inline prompts as fallback |

## Example Session

User: `/blueprint:pipeline "user authentication with JWT" --preset=standard`

1. **Initialize**: Create `pipeline-20260210-143022.json` with 6 phases
2. **Phase 1 (requirements)**: analyst produces requirements with JWT spec
3. **Phase 2 (design)**: design-writer creates API design with token endpoints
4. **Phase 3 (implementation)**: executor implements auth middleware + token service
5. **Phase 4 (unit-tests)**: test-engineer writes 15 unit tests
6. **Phase 5 (code-review)**: code-reviewer identifies missing token refresh logic → FAIL
7. **Retry Phase 5**: executor fixes refresh logic, code-reviewer approves → PASS
8. **Phase 6 (verification)**: verifier confirms all tests pass, build succeeds → PASS
9. **Finalize**: Pipeline complete, 6/6 phases successful (1 retry)

Result: Complete authentication feature with JWT, 85% test coverage, code reviewed and verified
