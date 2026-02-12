---
name: cancel
description: "Use when you want to cancel active PDCA cycles or pipeline runs. Triggers: cancel blueprint, stop cycle, stop pipeline, blueprint cancel."
argument-hint: [--force]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
user-invocable: true
---

# Blueprint Cancel Skill

Cancel active PDCA cycles and pipeline runs gracefully.

## When to Use

Use this skill when:
- You want to stop an active PDCA cycle that's not making progress
- A pipeline run needs to be terminated
- You need to clean up stalled blueprint workflows
- You want to force-cancel all blueprint operations

Do NOT use when:
- A pipeline is paused (it's already stopped; use --resume to continue or this to cancel)
- You just want to skip a phase (use --skip-phases in pipeline instead)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--force` | No | Force cancel all blueprint operations without confirmation |

Example: `/blueprint:cancel` or `/blueprint:cancel --force`

## Workflow

### 1. Discovery Phase
Scan for active blueprint operations:

**Check PDCA cycles:**
```bash
# Read active cycles index
ACTIVE_CYCLES=$(cat .blueprint/pdca/active-cycles.json 2>/dev/null || echo '{"cycles":[]}')

# List all cycle state files
find .blueprint/pdca/cycles/ -name "*.json" -exec jq -r 'select(.status=="active") | .id' {} \;
```

**Check pipeline runs:**
```bash
# Find active or paused pipeline runs
find .blueprint/pipeline/runs/ -name "*.json" -exec jq -r 'select(.status=="running" or .status=="paused") | .id' {} \;
```

### 2. Present Findings
If no active operations found:
```
No active blueprint operations found.
- PDCA cycles: 0 active
- Pipeline runs: 0 active/paused
```

If operations found:
```
Found active blueprint operations:

PDCA Cycles (2):
- pdca-20260210-143022: "improve auth module" (iteration 2/4, phase: check)
- pdca-20260210-150000: "refactor API layer" (iteration 1/3, phase: do)

Pipeline Runs (1):
- pipeline-20260210-144500: "user dashboard" (preset: standard, phase 4/6, status: paused)

Cancel these operations? [y/N]
```

If `--force` flag set, skip confirmation.

### 3. Status Change Phase
For each operation, update status to 'cancelled':

**PDCA cycle:**
```bash
CYCLE_FILE=".blueprint/pdca/cycles/${cycle_id}.json"

jq '.status = "cancelled" |
    .cancelled_at = now |
    .cancel_reason = "User requested cancellation"' \
   "$CYCLE_FILE" > tmp && mv tmp "$CYCLE_FILE"
```

**Pipeline run:**
```bash
PIPELINE_FILE=".blueprint/pipeline/runs/${pipeline_id}.json"

jq '.status = "cancelled" |
    .cancelled_at = now |
    .cancel_reason = "User requested cancellation"' \
   "$PIPELINE_FILE" > tmp && mv tmp "$PIPELINE_FILE"
```

### 4. Archive Phase
Move cancelled operations to history:

**PDCA cycle:**
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p .blueprint/pdca/history/

mv ".blueprint/pdca/cycles/${cycle_id}.json" \
   ".blueprint/pdca/history/${cycle_id}-${TIMESTAMP}.json"
```

**Pipeline run:**
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p .blueprint/pipeline/history/

mv ".blueprint/pipeline/runs/${pipeline_id}.json" \
   ".blueprint/pipeline/history/${pipeline_id}-${TIMESTAMP}.json"
```

### 5. Index Cleanup Phase
Remove cancelled operations from active indices:

**Update PDCA active-cycles.json:**
```bash
jq --arg id "$cycle_id" \
   '.cycles = [.cycles[] | select(.id != $id)]' \
   .blueprint/pdca/active-cycles.json > tmp && mv tmp .blueprint/pdca/active-cycles.json
```

**Update pipeline active-runs.json (if exists):**
```bash
jq --arg id "$pipeline_id" \
   '.runs = [.runs[] | select(.id != $id)]' \
   .blueprint/pipeline/active-runs.json > tmp && mv tmp .blueprint/pipeline/active-runs.json
```

### 6. Output Phase
Generate cancellation summary:

```
## Blueprint Cancellation Complete

### Cancelled Operations

**PDCA Cycles (2)**
- pdca-20260210-143022: "improve auth module"
  - Status: iteration 2/4, phase: check
  - Archived to: `.blueprint/pdca/history/pdca-20260210-143022-20260210-160000.json`

- pdca-20260210-150000: "refactor API layer"
  - Status: iteration 1/3, phase: do
  - Archived to: `.blueprint/pdca/history/pdca-20260210-150000-20260210-160000.json`

**Pipeline Runs (1)**
- pipeline-20260210-144500: "user dashboard"
  - Status: phase 4/6 (paused)
  - Archived to: `.blueprint/pipeline/history/pipeline-20260210-144500-20260210-160000.json`

### Summary
- Total operations cancelled: 3
- PDCA cycles: 2
- Pipeline runs: 1
- All operations archived to history/

### Note on Running Agents
Blueprint operations cancelled, but any currently running agents cannot be interrupted immediately. They will gracefully stop at the next phase transition.
```

## Agent Interruption Note

**Important**: This skill can only update state files. It cannot forcefully terminate running agents.

When you cancel an operation:
- The state file is marked as 'cancelled'
- Future phases will not start
- Currently executing agent will complete its current work
- Agent will check status before starting next phase and see 'cancelled' status
- Agent will then gracefully exit

**Timing:**
- PDCA: Agent stops between phases (Plan→Do, Do→Check, Check→Act, Act→Plan)
- Pipeline: Agent stops between pipeline phases

If immediate termination is critical, you may need to manually kill the agent process.

## Common Issues

| Issue | Solution |
|-------|----------|
| "No operations found" but I know one is running | Check if state file exists; agent may not have written it yet |
| Agent continues after cancel | Normal; agent will stop at next phase boundary |
| Cannot access state files | Verify .blueprint/ directories exist and have correct permissions |
| Archive fails | Ensure history/ directories exist; create them manually if needed |

## Example Sessions

### Example 1: Cancel with confirmation

User: `/blueprint:cancel`

```
Found active blueprint operations:

PDCA Cycles (1):
- pdca-20260210-143022: "improve auth module" (iteration 2/4, phase: check)

Pipeline Runs (0)

Cancel these operations? [y/N] y

Cancelling...
✓ PDCA cycle pdca-20260210-143022 cancelled
✓ Archived to history/

Summary: 1 operation cancelled
```

### Example 2: Force cancel

User: `/blueprint:cancel --force`

```
Scanning for active operations...

Found 3 active operations:
- 2 PDCA cycles
- 1 pipeline run

Force cancelling all...
✓ pdca-20260210-143022 cancelled
✓ pdca-20260210-150000 cancelled
✓ pipeline-20260210-144500 cancelled

All operations archived to history/

Summary: 3 operations cancelled
```

### Example 3: Nothing to cancel

User: `/blueprint:cancel`

```
No active blueprint operations found.
- PDCA cycles: 0 active
- Pipeline runs: 0 active/paused

Nothing to cancel.
```

## State File Locations

**PDCA:**
- Active: `.blueprint/pdca/cycles/{id}.json`
- Index: `.blueprint/pdca/active-cycles.json`
- History: `.blueprint/pdca/history/{id}-{timestamp}.json`

**Pipeline:**
- Active: `.blueprint/pipeline/runs/{id}.json`
- Index: `.blueprint/pipeline/active-runs.json` (optional)
- History: `.blueprint/pipeline/history/{id}-{timestamp}.json`

## Verification

After cancellation, verify:
```bash
# Check no active cycles remain
jq '.cycles | length' .blueprint/pdca/active-cycles.json
# Output: 0

# Check history contains archived operations
ls -l .blueprint/pdca/history/
ls -l .blueprint/pipeline/history/
```
