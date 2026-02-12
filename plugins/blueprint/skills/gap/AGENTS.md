<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# skills/gap/

## Purpose

Systematically identify gaps between current codebase state and desired target state. Spawns gap-detector agent (or architect fallback) to analyze current vs desired, categorizes findings by type (features/architecture/quality/dependencies) and severity (CRITICAL/HIGH/MEDIUM/LOW), prioritizes by impact-to-effort ratio, and optionally generates actionable design document. Read-only analysis with no state persistence (results archived immediately).

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill metadata and instructions (user-facing documentation) |

## Skill Metadata

**Name**: gap

**Trigger**: `/blueprint:gap "desired state description"` or `/blueprint:gap path/to/design-doc.md`

**Arguments**:
- `desired-state` (required) - Target state description, file path, or URL
- `--scope=X` (optional) - Analysis scope: file, dir, or project (default: project)
- `--generate-design` (optional) - Auto-generate design document from gap analysis

**Allowed Tools**: Read, Write, Edit, Bash, Glob, Grep, Task

## Workflow Phases

### 1. Parse Desired State

Accept desired state from:
- **Inline**: `"implement OAuth2 with refresh tokens"`
- **File**: `path/to/design-doc.md` (read and extract)
- **URL**: `https://example.com/spec.md` (fetch via WebFetch)

If file/URL reference, read/fetch content and extract requirements.

Store normalized desired state for passing to gap detector.

### 2. Spawn Gap Detector Agent

**Primary path** (if blueprint:gap-detector available):
```javascript
Task(subagent_type="blueprint:gap-detector",
     model="opus",
     prompt="Analyze gap between current and desired state.\n\nCurrent scope: {scope}\nDesired state:\n{desired_state}\n\nIdentify missing features, architectural mismatches, and quality gaps. Categorize by type and severity.")
```

**Fallback** (if gap-detector unavailable):
```javascript
Task(subagent_type="blueprint:architect",
     model="opus",
     prompt="Analyze current codebase against desired state:\n{desired_state}\n\nIdentify gaps by category (features/architecture/quality/dependencies) and severity (CRITICAL/HIGH/MEDIUM/LOW). Estimate effort/impact.")
```

### 3. Process Gap Report

Structure findings from agent output:

```json
{
  "id": "gap-{timestamp}",
  "desired_state": "...",
  "scope": "project|dir|file",
  "timestamp": "ISO-8601",
  "gaps": [
    {
      "category": "features|architecture|quality|dependencies",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "Gap title",
      "description": "Detailed description",
      "current_state": "What exists now",
      "desired_state": "What should exist",
      "effort": "high|medium|low",
      "impact": "high|medium|low"
    }
  ],
  "summary": {
    "total_gaps": N,
    "by_severity": {"CRITICAL": N, "HIGH": N, ...},
    "by_category": {"features": N, ...}
  }
}
```

### 4. Prioritize Gaps

Sort by priority score: `(severity_weight * impact) / effort`

**Weights**:
- CRITICAL: 10
- HIGH: 7
- MEDIUM: 4
- LOW: 2

**Effort/Impact scoring**: high=3, medium=2, low=1

Example: CRITICAL + HIGH impact + MEDIUM effort = (10 * 3) / 2 = 15.0 (top priority)

### 5. Generate Design Doc (Optional)

If `--generate-design` flag set:

```javascript
Task(subagent_type="blueprint:design-writer",
     model="sonnet",
     prompt="Transform gap analysis into actionable design document.\n\nGap analysis:\n{gap_report}\n\nCreate design doc with implementation phases, acceptance criteria per gap, dependencies, risks, estimated effort.")
```

Output: Design document at `.blueprint/gaps/designs/gap-{id}-design.md`

### 6. Save Analysis and Output

**Save report**:
```bash
mkdir -p .blueprint/gaps/analyses
write .blueprint/gaps/analyses/gap-{id}.json (gap report)
update .blueprint/gaps/analyses/index.json (add entry)
```

**Display formatted output** to user with top-priority gaps and roadmap.

## Gap Categories

### Features
Missing functionality compared to desired state.

Example: Current has basic login; desired has OAuth2, MFA, SSO. Gaps: refresh tokens, MFA, SSO.

### Architecture
Structural mismatches requiring refactoring.

Example: Current is monolithic; desired is modular. Gaps: no abstraction layer, tight coupling.

### Quality
Missing tests, documentation, error handling, logging.

Example: Current 40% coverage; desired 80%. Gap: 40% coverage, missing error telemetry.

### Dependencies
Missing or outdated packages.

Example: Current has no JWT library; desired has jsonwebtoken + passport. Gap: 2 missing packages.

## Output Format

```
## Gap Analysis Complete: {analysis-id}

### Desired State
{description}

### Current State Assessment
Scope: {scope}
Total gaps found: {N}

### Gap Summary by Severity
- CRITICAL: {N} gaps
- HIGH: {N} gaps
- MEDIUM: {N} gaps
- LOW: {N} gaps

### Top Priority Gaps (sorted by priority score)

**1. [CRITICAL] {title}**
- Category: {type}
- Current: {current_state}
- Desired: {desired_state}
- Effort: {effort} | Impact: {impact} | Priority: {score}

[... remaining gaps ...]

### Implementation Roadmap
Phase 1 (CRITICAL gaps): {N} items, {estimated_days} days
Phase 2 (HIGH gaps): {N} items, {estimated_days} days
Phase 3 (MEDIUM gaps): {N} items, {estimated_days} days

### Design Document
{link to generated design doc if --generate-design}

### Analysis Artifacts
- Full report: .blueprint/gaps/analyses/{id}.json
- Design doc: .blueprint/gaps/designs/{id}-design.md (if generated)
```

## For AI Agents

### Working In This Directory

- **One file per skill**: SKILL.md contains all skill metadata
- **No handler code**: Skill invoked by blueprint-detect.mjs hook
- **Read-only analysis**: Gap skill doesn't modify source code, only creates analysis artifacts
- **Agent spawning**: Uses Task tool to spawn gap-detector or architect agent
- **Agent fallback**: If gap-detector unavailable, use architect agent

### Testing Requirements

- Test desired state parsing: inline, file, URL inputs
- Test gap detection: verify gaps identified by category and severity
- Test prioritization: verify priority scoring correct
- Test design generation: `--generate-design` flag produces design document
- Test artifact storage: gap report saved to `.blueprint/gaps/analyses/`
- Test scope filtering: `--scope=dir` narrows analysis to directory

### Common Patterns

**Parse desired state from file**:
```javascript
let desiredState = arg;
if (desiredState.endsWith('.md') || desiredState.endsWith('.txt')) {
  desiredState = await fs.readFile(desiredState, 'utf-8');
}
```

**Spawn gap detector**:
```javascript
const report = await Task(
  subagent_type="blueprint:gap-detector",
  model="opus",
  prompt=`Analyze gap...\n${desiredState}`
);
```

**Prioritize gaps**:
```javascript
const priority = (severityWeights[gap.severity] * impactWeights[gap.impact]) / effortWeights[gap.effort];
```

**Save gap report**:
```javascript
await ensureDir('.blueprint/gaps/analyses');
const id = `gap-${Date.now()}`;
await safeWrite(`.blueprint/gaps/analyses/${id}.json`, JSON.stringify(report));
```

## Gap Analysis Output Schema

Agents SHOULD structure output to match this schema:

```json
{
  "gap_report": {
    "type": "object",
    "required": ["id", "desired_state", "scope", "gaps", "summary"],
    "properties": {
      "id": { "type": "string", "pattern": "^gap-\\d{10}$" },
      "desired_state": { "type": "string" },
      "scope": { "type": "string", "enum": ["file", "dir", "project"] },
      "timestamp": { "type": "string", "format": "date-time" },
      "gaps": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["category", "severity", "title", "description"],
          "properties": {
            "category": { "type": "string", "enum": ["features", "architecture", "quality", "dependencies"] },
            "severity": { "type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"] },
            "title": { "type": "string" },
            "description": { "type": "string" },
            "current_state": { "type": "string" },
            "desired_state": { "type": "string" },
            "effort": { "type": "string", "enum": ["high", "medium", "low"] },
            "impact": { "type": "string", "enum": ["high", "medium", "low"] }
          }
        }
      },
      "summary": {
        "type": "object",
        "required": ["total_gaps", "by_severity", "by_category"],
        "properties": {
          "total_gaps": { "type": "integer", "minimum": 0 },
          "by_severity": { "type": "object" },
          "by_category": { "type": "object" }
        }
      }
    }
  }
}
```

## State File Locations

**Analysis artifacts**:
- Report: `.blueprint/gaps/analyses/{analysis-id}.json`
- Index: `.blueprint/gaps/analyses/index.json`
- Design (optional): `.blueprint/gaps/designs/{analysis-id}-design.md`

## Dependencies

### Internal

- `hooks/lib/state-manager.mjs` - State file I/O
- `hooks/lib/io.mjs` - File operations
- `hooks/lib/logger.mjs` - Logging

### External

- None - uses Node.js built-in modules only

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
