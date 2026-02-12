---
name: gap
description: "Use when you want to analyze the gap between current state and desired state of code/architecture. Triggers: gap analysis, what's missing, compare current vs desired, assess readiness."
argument-hint: <desired-state> [--scope=file|dir|project] [--generate-design]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
user-invocable: true
---

# Gap Analysis Skill

Systematically identify gaps between current codebase state and desired target state.

## When to Use

Use this skill when:
- You need to assess what's missing before starting a feature
- You want to compare current architecture against a target design
- You need to evaluate readiness for a migration or upgrade
- You want to identify technical debt systematically

Do NOT use when:
- The desired state is not clearly defined
- You just need a general code review (use code-reviewer instead)
- The gap is already obvious (just implement directly)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `desired-state` | Yes | Description of target state (can be a file path to design doc) |
| `--scope=X` | No | Analysis scope: `file`, `dir`, or `project` (default: project) |
| `--generate-design` | No | Auto-generate design document from gap analysis |

Example: `/blueprint:gap "full OAuth2 implementation with refresh tokens" --scope=dir --generate-design`

## Workflow

### 1. Parse Desired State
Accept desired state from:
- Inline description: `"implement user authentication with JWT"`
- File reference: `path/to/design-doc.md`
- URL reference: `https://example.com/spec.md` (via WebFetch)

If file reference, read it first to extract full specification.

### 2. Spawn Gap Detector Agent
Analyze current vs desired state:

**Primary path:**
```javascript
Task(subagent_type="blueprint:gap-detector",
     model="opus",
     prompt="Analyze gap between current and desired state.\n\nCurrent scope: {scope}\nDesired state:\n{desired_state}\n\nIdentify missing features, architectural mismatches, and quality gaps.")
```

**Fallback (if gap-detector unavailable):**
```javascript
Task(subagent_type="blueprint:architect",
     model="opus",
     prompt="Analyze the current codebase against this desired state:\n{desired_state}\n\nIdentify gaps by category (features/architecture/quality/dependencies) and severity (CRITICAL/HIGH/MEDIUM/LOW).")
```

### 3. Generate Gap Report
Structure findings with severity levels:

```json
{
  "id": "gap-20260210-143022",
  "desired_state": "full OAuth2 implementation",
  "scope": "project",
  "timestamp": "2026-02-10T14:30:22Z",
  "gaps": [
    {
      "category": "features",
      "severity": "CRITICAL",
      "title": "Missing refresh token mechanism",
      "description": "Current implementation only supports access tokens...",
      "current_state": "src/auth/token.ts:42-80",
      "desired_state": "OAuth2 RFC 6749 section 6",
      "effort": "high",
      "impact": "high"
    },
    {
      "category": "architecture",
      "severity": "HIGH",
      "title": "Token storage not persistent",
      "description": "Tokens stored in memory, lost on restart",
      "current_state": "src/auth/store.ts:15",
      "desired_state": "Persistent storage (Redis/DB)",
      "effort": "medium",
      "impact": "high"
    }
  ],
  "summary": {
    "total_gaps": 12,
    "by_severity": {"CRITICAL": 2, "HIGH": 4, "MEDIUM": 5, "LOW": 1},
    "by_category": {"features": 6, "architecture": 3, "quality": 2, "dependencies": 1}
  }
}
```

### 4. Prioritize Gaps
Sort by priority score: `(severity_weight * impact) / effort`

Weights:
- CRITICAL: 10
- HIGH: 7
- MEDIUM: 4
- LOW: 2

Effort/Impact: high=3, medium=2, low=1

### 5. Generate Design Doc (Optional)
If `--generate-design` flag set:

```javascript
Task(subagent_type="blueprint:design-writer",
     model="sonnet",
     prompt="Transform gap analysis into actionable design document.\n\nGap analysis: {gap_report}\n\nCreate design doc with:\n- Implementation phases\n- Acceptance criteria per gap\n- Dependencies and risks\n- Estimated effort")
```

Output: Design document at `.blueprint/gaps/designs/gap-{id}-design.md`

### 6. Save Analysis
Write results to `.blueprint/gaps/analyses/{analysis-id}.json`

Update index: `.blueprint/gaps/analyses/index.json`

## Gap Categories

### Features
Missing functionality compared to desired state.

**Example:**
- Current: Basic user login
- Desired: OAuth2 with refresh tokens, MFA, SSO
- Gap: Missing refresh mechanism, MFA, SSO integration

### Architecture
Structural mismatches that require refactoring.

**Example:**
- Current: Monolithic auth in single file
- Desired: Modular auth with strategy pattern
- Gap: No abstraction layer, tight coupling

### Quality
Missing tests, documentation, error handling.

**Example:**
- Current: 40% test coverage, no error logging
- Desired: 80% coverage, structured logging
- Gap: 40% coverage gap, missing error telemetry

### Dependencies
Missing or outdated packages.

**Example:**
- Current: No JWT library
- Desired: jsonwebtoken + passport
- Gap: Missing 2 critical packages

## Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| **CRITICAL** | Blocks core functionality | Must address before launch |
| **HIGH** | Impacts user experience significantly | Address in current sprint |
| **MEDIUM** | Nice to have, improves quality | Plan for next sprint |
| **LOW** | Minor improvement | Backlog |

## Output Format

```
## Gap Analysis Complete: {analysis-id}

### Desired State
{desired_state_summary}

### Current State Assessment
Scope: {scope}
Total gaps found: {N}

### Gap Summary by Severity
- CRITICAL: {N} gaps
- HIGH: {N} gaps
- MEDIUM: {N} gaps
- LOW: {N} gaps

### Top Priority Gaps (sorted by priority score)

**1. [CRITICAL] Missing refresh token mechanism**
- Category: Features
- Current: `src/auth/token.ts:42-80` - only access tokens
- Desired: OAuth2 RFC 6749 section 6 - refresh token flow
- Effort: HIGH | Impact: HIGH | Priority: 33.3

**2. [HIGH] Token storage not persistent**
- Category: Architecture
- Current: `src/auth/store.ts:15` - in-memory Map
- Desired: Redis/PostgreSQL persistent storage
- Effort: MEDIUM | Impact: HIGH | Priority: 10.5

[... remaining gaps ...]

### Implementation Roadmap
Phase 1 (CRITICAL gaps): {N} items, {effort} days
Phase 2 (HIGH gaps): {N} items, {effort} days
Phase 3 (MEDIUM gaps): {N} items, {effort} days

### Design Document
{if --generate-design: Link to generated design doc}

### Analysis Artifacts
- Full report: `.blueprint/gaps/analyses/{id}.json`
- Design doc: `.blueprint/gaps/designs/{id}-design.md` (if generated)
```

## Output Schema

The gap analysis produces structured output that can be validated downstream.

```json
{
  "gap_report": {
    "type": "object",
    "required": ["id", "desired_state", "scope", "gaps", "summary"],
    "properties": {
      "id": { "type": "string", "pattern": "^gap-\\d{8}-\\d{6}$" },
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
  },
  "design_doc": {
    "type": "object",
    "required": ["phases", "acceptance_criteria"],
    "properties": {
      "phases": { "type": "array", "items": { "type": "object" } },
      "acceptance_criteria": { "type": "array", "items": { "type": "string" } },
      "dependencies": { "type": "array", "items": { "type": "string" } },
      "risks": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

Agents SHOULD structure their output to match these schemas. Downstream consumers MAY validate against them.

## Common Issues

| Issue | Solution |
|-------|----------|
| Too many gaps (>50) | Narrow scope with --scope=dir or --scope=file |
| Gaps too vague | Ensure desired state includes specific requirements |
| Cannot prioritize | Explicitly set effort/impact estimates in gap report |
| Overlapping gaps | Deduplicate and merge related gaps in post-processing |

## Example Session

User: `/blueprint:gap "complete REST API with pagination, filtering, auth" --scope=dir`

1. **Parse**: Extract desired state components (pagination, filtering, auth)
2. **Spawn gap-detector**: Analyze `src/api/` directory
3. **Findings**:
   - CRITICAL: No authentication middleware (current: none, desired: JWT middleware)
   - HIGH: No pagination support (current: returns all, desired: limit/offset)
   - HIGH: No filtering (current: no query params, desired: filter by fields)
   - MEDIUM: No rate limiting (current: none, desired: rate limit per user)
4. **Prioritize**: Sort by priority score
5. **Save**: Write to `.blueprint/gaps/analyses/gap-20260210-143022.json`
6. **Output**: Report with 4 gaps, roadmap with 2 phases

Result: Clear roadmap showing authentication as Phase 1, pagination/filtering as Phase 2
