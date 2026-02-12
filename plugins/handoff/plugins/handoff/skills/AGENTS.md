<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-10 | Updated: 2026-02-10 -->

# skills

## Purpose

Skill definition files for the handoff plugin. Each `.md` file defines a Claude Code slash command with YAML frontmatter (name, description) and markdown body (usage docs, templates, behavior spec).

## Key Files

| File | Description |
|------|-------------|
| `handoff.md` | `/handoff` skill definition - 3-level output (L1/L2/L3) with templates and behavior spec |

## For AI Agents

### Working In This Directory

- Skill files use YAML frontmatter (`---` delimiters) for metadata
- The markdown body IS the skill prompt - Claude reads it to know how to execute
- Templates in code blocks define the output format for each level
- L1 (~100 tokens): quick checkpoint, L2 (~300 tokens, default): standard, L3 (~500 tokens): full documentation

### handoff.md Structure

```
---
name: handoff
description: Save session context to clipboard...
---

# Skill Content
- Usage section with CLI syntax
- Level definitions (L1, L2, L3) with templates
- Clipboard format specification
- Edge case handling
- Secret detection rules
```

### When Modifying Skills

1. Preserve YAML frontmatter format exactly
2. Keep templates in fenced code blocks
3. Test with `/handoff l1`, `/handoff l2`, `/handoff l3`
4. Verify clipboard output matches the Clipboard Format section
5. Ensure secret redaction patterns are maintained

### Legacy Aliases

- `/handoff fast` = `/handoff l1`
- `/handoff slow` = `/handoff l3`
- `/handoff` (no level) = `/handoff l2`

## Dependencies

### Internal

- `../plugin.json` - Registers this directory as skills source
- `../../../SKILL.md` - Root skill specification (reference)
- `../../../hooks/constants.mjs` - Security patterns for redaction

### External

- Claude Code skill system for YAML frontmatter parsing

<!-- MANUAL: -->
