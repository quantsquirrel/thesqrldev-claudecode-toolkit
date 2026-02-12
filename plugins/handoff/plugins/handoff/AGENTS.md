<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# handoff (Plugin)

## Purpose

Core handoff plugin for Claude Code. Provides the `/handoff` skill with 3-level auto-scaling output (L1/L2/L3) for session context preservation. This is the primary deliverable of the project.

## Key Files

| File | Description |
|------|-------------|
| `plugin.json` | Plugin manifest: name, version (2.2.0), author, skills path (`./skills/`) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `skills/` | Skill definition files (see `skills/AGENTS.md`) |

## For AI Agents

### Working In This Directory

- `plugin.json` defines plugin identity and points to `./skills/` for skill files
- Changes here directly affect `/handoff` command behavior
- Version in `plugin.json` must match `../../.claude-plugin/marketplace.json`

### plugin.json Schema

```json
{
  "name": "handoff",
  "version": "2.3.0",
  "description": "Session context handoff with smart auto-scaling output",
  "author": { "name": "quantsquirrel" },
  "repository": "https://github.com/quantsquirrel/claude-handoff-baton",
  "license": "MIT",
  "skills": "./skills/"
}
```

### Testing Requirements

1. Verify JSON validity: `cat plugin.json | jq .`
2. Run `/handoff "test"` and verify file creation
3. Test all 3 levels: `/handoff l1`, `/handoff l2`, `/handoff l3`
4. Verify clipboard contains `<previous_session>` format

## Dependencies

### Internal

- `../../SKILL.md` - Original skill specification
- `../../hooks/auto-handoff.mjs` - Auto-suggests `/handoff` at context thresholds
- `../../.claude-plugin/marketplace.json` - Version must match

### External

- Claude Code skill system for command registration
- System clipboard (pbcopy/xclip) for copy functionality

<!-- MANUAL: -->
