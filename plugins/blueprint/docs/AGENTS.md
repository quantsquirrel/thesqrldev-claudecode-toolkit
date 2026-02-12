<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-12T00:00:00Z | Updated: 2026-02-12T00:00:00Z -->

# docs/

## Purpose

Comprehensive documentation for Blueprint Helix methodology, architecture, workflows, and integration patterns. Explains agent interactions, skill orchestration, state management, and the Blueprint+OMC workflow framework.

## Key Files

| File | Description |
|------|-------------|
| `agent-interactions.md` | Agent coordination patterns, phase transitions, and communication protocols |
| `blueprint-omc-workflow.md` | Blueprint + OMC integration guide (B-O-B-O cycle, complexity routing, cheat sheets) |
| `skill-orchestration.md` | Skill lifecycle, argument parsing, agent spawning, and phase gates |
| `state-management.md` | File-based state persistence, locking protocol, concurrency, and recovery |
| `README.md` | Documentation index and navigation |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `diagrams/` | Diagram source files (currently stores markdown docs, not actual diagrams) |

## For AI Agents

### Working In This Directory

- **Markdown format**: All docs are markdown with code blocks and tables
- **Cross-references**: Use relative links for internal navigation (`[text](./file.md)`)
- **Code examples**: Include runnable examples with expected output
- **Architecture diagrams**: ASCII art or mermaid syntax (if tooling supports)
- **Version notes**: Mark version-specific features with `(v1.0+)` annotations

### Testing Requirements

- Verify all internal links resolve correctly
- Check code examples are syntactically correct
- Ensure diagrams render properly in markdown viewers
- Validate no broken references to non-existent files

### Common Patterns

- **Documentation structure**: Purpose → Architecture → Usage → Examples → Troubleshooting
- **Code blocks**: Use triple backticks with language hints (```javascript, ```bash, etc.)
- **API references**: Document all hook parameters, return values, and side effects
- **Workflow diagrams**: Use numbered lists or ASCII flow for step-by-step processes

## Dependencies

### Internal

- References: `../agents/`, `../hooks/`, `../skills/`, `../config/`, `../.blueprint/`
- Used by: All Blueprint users learning the system

### External

None - pure documentation

<!-- MANUAL: -->
