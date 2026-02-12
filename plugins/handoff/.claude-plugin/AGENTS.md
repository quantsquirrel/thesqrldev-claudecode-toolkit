<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# .claude-plugin

## Purpose

Plugin marketplace configuration directory. Contains metadata for registering and distributing the Handoff plugin through the Claude Code plugin marketplace system. This enables automatic discovery, installation, and updates.

## Key Files

| File | Description |
|------|-------------|
| `marketplace.json` | Marketplace registration: name, version, owner, plugin source paths |

## For AI Agents

### Working In This Directory

- `marketplace.json` is the sole configuration file
- Version must match `../plugins/handoff/plugin.json` version
- Owner info (name, email) is set once and rarely changes

### Version Management

When updating versions, these files must stay in sync:

1. `marketplace.json` version field
2. `marketplace.json` plugins[0].version field
3. `../plugins/handoff/plugin.json` version field

### Testing Requirements

- Validate JSON syntax: `cat marketplace.json | jq .`
- Verify version consistency: compare with `../plugins/handoff/plugin.json`

## Dependencies

### Internal

- `../plugins/handoff/plugin.json` - Must have matching version
- `../plugins/handoff/` - Source directory referenced in config

### External

- Claude Code marketplace system for plugin distribution

<!-- MANUAL: -->
