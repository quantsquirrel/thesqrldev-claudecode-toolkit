<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-04 -->

# .claude Directory - Claude Code Configuration

This directory contains Claude Code session data and handoff documentation for the Synod project.

## Purpose

Stores session context and handoff files that enable seamless continuation of work across Claude Code sessions. Handoffs capture project state, decisions made, and next steps for future sessions.

## Directory Structure

```
.claude/
├── AGENTS.md           # This file
└── handoffs/           # Session handoff documents
    ├── 2026-01-31_0230_synod-release.md
    ├── handoff-20260131-session.md
    └── handoff-20260201-session2.md
```

## Key Files

| File | Description |
|------|-------------|
| `handoffs/*.md` | Session handoff documents with context, decisions, and next steps |

## For AI Agents

### Working In This Directory

- **Read handoffs** before starting work to understand project context
- **Create new handoffs** when ending a significant work session
- **Use `/handoff` skill** to generate properly formatted handoff documents
- Handoff naming convention: `YYYY-MM-DD_HHMM_topic.md` or `handoff-YYYYMMDD-session.md`

### Handoff Document Structure

Typical handoff includes:
1. **Session Summary** - What was accomplished
2. **Key Decisions** - Architectural and implementation choices made
3. **Current State** - Where things stand now
4. **Next Steps** - Recommended actions for next session
5. **Open Questions** - Unresolved issues needing attention

### When to Create Handoffs

- After completing a major feature or milestone
- Before ending a long work session
- When context is complex and needs preservation
- Before switching to a different task area

## Dependencies

### Internal
- Root `AGENTS.md` for project architecture understanding
- `skills/` for skill definitions referenced in handoffs

### External
- Claude Code CLI for handoff skill invocation

---

**Last Updated**: 2026-02-04
**Purpose**: Session continuity and context preservation
