<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-02 -->

# .claude

## Purpose

Claude Code local configuration and data directory. This directory stores project-specific Claude Code settings, handoff documents, and session-related data. It is typically gitignored except for example/template files.

## Key Files

| File | Description |
|------|-------------|
| `handoffs/` | Directory containing generated handoff documents |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `handoffs/` | Generated handoff markdown files with session context |

## For AI Agents

### Working In This Directory

- **Handoff files are auto-generated** - Do not manually edit unless recovering
- Files follow naming convention: `handoff-YYYYMMDD-HHMMSS.md`
- Draft files (`.draft-*.json`) are temporary and can be cleaned up
- Lock files (`.generating.lock`) indicate ongoing generation

### File Types

| Pattern | Type | Purpose |
|---------|------|---------|
| `handoff-*.md` | Generated | Complete handoff documents |
| `.draft-*.json` | Temporary | Session drafts for recovery |
| `.generating.lock` | Lock | Prevents concurrent generation |

### Security Considerations

- Handoff files may contain project context - review before sharing
- Secret detection runs during generation but manual review recommended
- Consider adding to `.gitignore` if sensitive data possible

### Recovery Operations

If generation was interrupted:

```bash
# Check for drafts and locks
node hooks/recover.mjs

# Manual cleanup if needed
rm .claude/handoffs/.generating.lock
```

## Dependencies

### Internal

- `../hooks/auto-handoff.mjs` - Creates draft files here
- `../hooks/lockfile.mjs` - Manages lock files
- `../hooks/recover.mjs` - Reads drafts for recovery
- `../SKILL.md` - Defines handoff document format

### External

- Claude Code session system for context data

<!-- MANUAL: -->
