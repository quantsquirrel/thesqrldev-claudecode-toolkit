<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# plugins

## Purpose

Claude Code plugin implementations. Each plugin lives in its own subdirectory with a `plugin.json` manifest and skill definition files. Currently contains the `handoff` plugin.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `handoff/` | Core handoff plugin with `/handoff` skill (see `handoff/AGENTS.md`) |

## For AI Agents

### Working In This Directory

- Each plugin follows the structure: `{name}/plugin.json` + `{name}/skills/{skill}.md`
- Plugin names: lowercase, hyphenated
- Version follows semver (MAJOR.MINOR.PATCH)

### Plugin Structure

```
plugins/
  {plugin-name}/
    plugin.json           # Metadata: name, version, author, skills path
    skills/
      {skill-name}.md     # Skill definition (YAML frontmatter + markdown)
```

## Dependencies

### Internal

- `../SKILL.md` - Root skill definition reference
- `../hooks/` - Auto-handoff hook integration
- `../.claude-plugin/marketplace.json` - Version must match

### External

- Claude Code skill system for plugin loading and command registration

<!-- MANUAL: -->
