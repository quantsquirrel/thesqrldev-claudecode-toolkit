<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# skills/pdca/

## Purpose

Execute iterative Plan-Do-Check-Act improvement cycles with measurable quality progression. Initialize PDCA cycle state with unique ID, spawn agents for each phase (analyst for Plan, executor for Do, verifier for Check, pdca-iterator for Act), track iteration count and current phase, evaluate quality targets at each iteration, and loop until targets met or max iterations reached. Coordinates multi-phase workflows with phase-tracker.mjs hook monitoring completion.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill metadata and instructions (user-facing documentation) |

## Skill Metadata

**Name**: pdca

**Trigger**: `/blueprint:pdca "task description"` or `/blueprint:pdca "task" --max-iterations=N --auto-act`

**Arguments**:
- `task` (required) - Improvement task or feature to iteratively refine
- `--max-iterations=N` (optional) - Maximum PDCA cycles (1-10, default: 4)
- `--auto-act` (optional) - Auto-proceed to Act phase without manual approval

**Allowed Tools**: Read, Write, Edit, Bash, Glob, Grep, Task

## Workflow Phases

### 1. Initialize

Generate unique cycle-id (format: `pdca-{YYYYMMdd-HHMMSS}`)

Create state file at `.blueprint/pdca/cycles/{cycle-id}.json`:

```json
{
  "id": "pdca-20260210-143022",
  "task": "improve auth module error handling",
  "status": "active",
  "current_phase": "plan",
  "iteration": 1,
  "max_iterations": 4,
  "auto_act": false,
  "created_at": "2026-02-10T14:30:22Z",
  "updated_at": "2026-02-10T14:30:22Z",
  "phases": {
    "plan": {"status": "pending", "output": null},
    "do": {"status": "pending", "output": null},
    "check": {"status": "pending", "output": null},
    "act": {"status": "pending", "decision": null}
  },
  "iterations": []
}
```

Add entry to `.blueprint/pdca/active-cycles.json`:
```json
{
  "cycles": [
    {"id": "pdca-20260210-143022", "task": "improve auth module error handling", "iteration": 1, "status": "active"}
  ]
}
```

### 2. Plan Phase

Spawn agent to analyze current state and create improvement plan:

```javascript
Task(subagent_type="blueprint:pdca-iterator",
     model="sonnet",
     prompt="Plan phase: Analyze task and create improvement plan.\nTask: {user_task}\nIteration: {N}/{max_iterations}\nFocus on: quality targets, acceptance criteria, approach.")
```

Expected output structure:
```json
{
  "targets": ["Target 1", "Target 2"],
  "acceptance_criteria": ["Criterion 1", "Criterion 2"],
  "approach": "Step-by-step implementation approach"
}
```

Update state: `phases.plan.status = "completed"`, `phases.plan.output = {output}`

### 3. Do Phase

Implement the plan from Plan phase:

```javascript
Task(subagent_type="blueprint:executor",
     model="sonnet",
     prompt="Implement PDCA plan:\n{plan_output}\n\nTask: {user_task}\nIteration: {N}\nFocus on: clean, maintainable code; commit changes.")
```

Expected output:
```json
{
  "changes": ["Change 1", "Change 2"],
  "files_modified": ["file.ts:42-50", "file2.ts:10"]
}
```

Update state: `phases.do.status = "completed"`, `phases.do.output = {output}`

### 4. Check Phase

Verify implementation against quality targets:

```javascript
Task(subagent_type="blueprint:verifier",
     model="sonnet",
     prompt="Verify PDCA implementation meets targets:\n\nPlan targets:\n{plan_output.targets}\n\nImplementation:\n{do_output}\n\nCheck each acceptance criterion and verify targets met.")
```

Expected output:
```json
{
  "verdict": "PASS",
  "criteria_results": [
    {"criterion": "Criterion 1", "status": "pass", "evidence": "..."},
    {"criterion": "Criterion 2", "status": "fail", "evidence": "..."}
  ]
}
```

Update state: `phases.check.status = "completed"`, `phases.check.output = {output}`

### 5. Act Phase

Decide whether to continue iterating or complete:

```javascript
Task(subagent_type="blueprint:pdca-iterator",
     model="sonnet",
     prompt="Act phase: Review verification results and decide next action.\n\nVerification results:\n{check_output}\n\nDecide: CONTINUE (iterate again) or COMPLETE (finish cycle)\n\nIteration: {N}/{max_iterations}")
```

Expected output:
```json
{
  "decision": "CONTINUE",
  "reason": "Quality targets not fully met, 2 more iterations possible"
}
```

Or:
```json
{
  "decision": "COMPLETE",
  "reason": "All acceptance criteria passed, targets met"
}
```

Update state: `phases.act.status = "completed"`, `phases.act.decision = {decision}`

### 6. Loop Decision

**If decision = CONTINUE and iteration < max_iterations**:
- Increment iteration counter: `state.iteration += 1`
- Reset phases to "pending"
- Return to Plan phase (step 2)

**If decision = COMPLETE or iteration == max_iterations**:
- Proceed to Finalize (step 7)

### 7. Finalize

When all iterations complete:

1. Set `status = "completed"` in state file
2. Calculate final metrics:
   - Total iterations completed
   - Quality progression (before → after)
   - Time elapsed
3. Archive to `.blueprint/pdca/history/{cycle-id}-{timestamp}.json`
4. Remove from `.blueprint/pdca/active-cycles.json`
5. Generate and display summary report

## Output Format

```
## PDCA Cycle Complete: {cycle-id}

### Task
{user_task}

### Iterations
- Total cycles completed: {N}
- Final status: {COMPLETE/INCOMPLETE}

### Iteration Summary

**Iteration 1**
- Plan: [2 targets, 4 criteria identified]
- Do: [5 files modified]
- Check: 2/4 criteria passed (50%)
- Act: CONTINUE (targets not met)

**Iteration 2**
- Plan: [refined plan, 3 criteria revised]
- Do: [3 files modified]
- Check: 4/4 criteria passed (100%)
- Act: COMPLETE (targets met)

### Final Outcome
{2-3 sentence summary of improvements achieved}

### Evidence
- Build: `npm run build` -> PASS
- Tests: `npm test` -> 45 passed
- Quality progression: [baseline metric] → [final metric]
```

## State File Locations

**Active cycles**:
- Cycle state: `.blueprint/pdca/cycles/{cycle-id}.json`
- Active index: `.blueprint/pdca/active-cycles.json`

**History**:
- Completed cycle: `.blueprint/pdca/history/{cycle-id}-{timestamp}.json`

## Phase-Tracker Hook Integration

After each phase completes, the PostToolUse hook fires and:
1. Reads current cycle state
2. Checks if phase gate conditions are met
3. If gate passes: updates phase to "completed", may trigger next phase automatically
4. If gate fails: records failure, may trigger retry

The hook enables external gate evaluation without modifying PDCA logic.

## For AI Agents

### Working In This Directory

- **One file per skill**: SKILL.md contains all metadata
- **Iterative coordination**: Each phase produces output fed to next phase
- **State persistence**: State file updated after each phase completes
- **Loop discipline**: Always check iteration counter and max_iterations
- **Error resilience**: If agent fails, cycle pauses; can be resumed manually

### Testing Requirements

- Test initialization: verify state file created with correct structure
- Test full cycle: run all 4 phases, verify state transitions
- Test iteration loop: verify iteration counter incremented, phase gate re-evaluated
- Test max iterations: verify cycle stops when limit reached regardless of targets
- Test agent outputs: verify output schema matches expectations
- Test state persistence: verify state survives session restart
- Test concurrent cycles: verify different cycle IDs, no state collision

### Common Patterns

**Initialize cycle**:
```javascript
const cycleId = `pdca-${Date.now()}`;
const state = {
  id: cycleId,
  task: userTask,
  status: 'active',
  current_phase: 'plan',
  iteration: 1,
  max_iterations: maxIt,
  phases: { plan: {}, do: {}, check: {}, act: {} }
};
await updateState(`.blueprint/pdca/cycles/${cycleId}.json`, state);
```

**Spawn phase agent**:
```javascript
const output = await Task(
  subagent_type="blueprint:pdca-iterator",
  model="sonnet",
  prompt=`Plan phase: ${userTask}...`
);
```

**Update phase status**:
```javascript
const state = await readState(`.blueprint/pdca/cycles/${cycleId}.json`);
state.phases.plan.status = 'completed';
state.phases.plan.output = output;
await updateState(`.blueprint/pdca/cycles/${cycleId}.json`, state);
```

**Evaluate decision and loop**:
```javascript
if (output.decision === 'CONTINUE' && state.iteration < state.max_iterations) {
  state.iteration++;
  state.current_phase = 'plan';
  // Return to Plan phase
} else {
  state.status = 'completed';
  // Finalize
}
```

## Output Schema

Each phase SHOULD produce structured output matching these schemas:

**Plan output**:
```json
{
  "targets": ["string"],
  "acceptance_criteria": ["string"],
  "approach": "string"
}
```

**Do output**:
```json
{
  "changes": ["string"],
  "files_modified": ["string"]
}
```

**Check output**:
```json
{
  "verdict": "PASS|FAIL",
  "criteria_results": [
    {"criterion": "string", "status": "pass|fail", "evidence": "string"}
  ]
}
```

**Act output**:
```json
{
  "decision": "CONTINUE|COMPLETE",
  "reason": "string"
}
```

## Dependencies

### Internal

- `hooks/lib/state-manager.mjs` - State file I/O with locking
- `hooks/lib/io.mjs` - Atomic file operations
- `hooks/lib/logger.mjs` - Logging

### External

- None - uses Node.js built-in modules only

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
