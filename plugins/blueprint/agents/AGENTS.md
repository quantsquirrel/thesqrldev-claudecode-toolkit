<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-11T00:00:00Z | Updated: 2026-02-11T00:00:00Z -->

# agents/

## Purpose

Specialized agent prompts for Blueprint workflows. Each agent has a specific role in analysis, design, implementation, and verification cycles. Agents are discoverable via the plugin namespace (`blueprint:agent-name`) with inline prompt fallbacks.

## Key Files

| File | Description |
|------|-------------|
| `analyst.md` | Requirements analysis agent (opus) - clarifies specs, identifies edge cases, defines acceptance criteria |
| `architect.md` | Architecture design agent (opus, read-only) - designs component boundaries, evaluates trade-offs, assesses scalability |
| `design-writer.md` | Design documentation agent (sonnet) - creates structured design documents, documents architecture decisions |
| `executor.md` | Code implementation agent (sonnet) - implements changes from designs, follows project conventions, runs verification |
| `gap-detector.md` | Gap analysis agent (opus, read-only) - compares current vs desired state, identifies gaps by severity, recommends actions |
| `pdca-iterator.md` | PDCA orchestration agent (sonnet) - manages Plan-Do-Check-Act cycles, coordinates phases, evaluates completion |
| `reviewer.md` | Code review agent (sonnet, read-only) - comprehensive review (correctness, security, maintainability), file:line findings |
| `tester.md` | Test engineering agent (sonnet) - designs test strategies, creates tests, analyzes coverage and edge cases |
| `verifier.md` | Verification agent (sonnet, read-only) - verifies implementation vs acceptance criteria, runs tests, generates evidence-based verdicts |

## Agent Roles & Models

| Agent | Model | Role | Read-Only | Pipeline Phase |
|-------|-------|------|-----------|-----------------|
| analyst | opus | Requirements analysis & spec clarity | No | requirements |
| architect | opus | Architecture design & evaluation | Yes | architecture |
| design-writer | sonnet | Design document generation | No | design |
| executor | sonnet | Code implementation | No | implementation |
| gap-detector | opus | Gap analysis & recommendations | Yes | gap-analysis |
| pdca-iterator | sonnet | PDCA cycle orchestration | No | plan/act |
| reviewer | sonnet | Code review & quality checks | Yes | code-review |
| tester | sonnet | Test design & implementation | No | unit-test, integration-test |
| verifier | sonnet | Implementation verification | Yes | verification |

## For AI Agents

### Working In This Directory

- **Agent discovery**: Agents loaded via `blueprint:agent-name` from plugin namespace
- **Inline fallbacks**: If plugin agent unavailable, skill handlers use inline prompts as fallback
- **Read-only agents**: architect, gap-detector, reviewer, verifier must not modify files
- **Metadata format**: Each file starts with YAML frontmatter: `name:`, `description:`, `model:`

### Testing Requirements

- Test agent loading: verify each agent's prompt loads successfully from plugin namespace
- Test fallback paths: disable plugin loading, verify inline prompts work
- Test read-only enforcement: ensure read-only agents don't attempt file modifications
- Test agent coordination: verify agents can process outputs from previous phases

### Common Patterns

- **Prompt structure**: Role definition, success criteria, constraints, investigation protocol
- **Output requirements**: Structured JSON or markdown, scannable with headers and tables
- **Error handling**: Agents should flag ambiguities for user clarification rather than guess
- **Agent chaining**: Output from one agent feeds into next phase (e.g., analyst → architect → design-writer)

## Agent Coordination Flow

```
PDCA Cycle:
  Plan     → analyst (clarify requirements)
         → pdca-iterator (define cycle parameters)

  Do       → executor (implement from design)
         → tester (write and run tests)

  Check    → verifier (verify vs acceptance criteria)
         → reviewer (code quality review)
         → gap-detector (identify remaining gaps)

  Act      → pdca-iterator (decide next iteration or completion)

Pipeline (Phased):
  requirements → analyst (specs + acceptance criteria)
  architecture → architect (design document)
  design       → design-writer (implementation-ready design)
  implementation → executor (code changes)
  unit-test    → tester (unit test suite)
  integration-test → tester (integration tests)
  code-review  → reviewer (quality findings)
  gap-analysis → gap-detector (gap report)
  verification → verifier (evidence-based verdict)
```

## Dependencies

### Internal

- All agents load via plugin namespace from `plugin.json` agent registry
- config/agent-overrides.json controls model per-agent and enable/disable
- Skills call agents via plugin interface or inline prompts

### External

None - agents are self-contained prompt definitions.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
