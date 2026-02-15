<div id="top"></div>

<div align="center">

<img src="assets/handoff.jpeg" alt="Handoff Baton - Don't pass raw history, pass a baton">

**Don't pass raw history. Pass a baton — distilled, structured, ready to run.**

**English** | **[한국어](README-ko.md)**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-success?style=flat-square)](https://github.com/anthropics/claude-code)
[![Version](https://img.shields.io/badge/version-2.4.0-blue?style=flat-square)](https://github.com/quantsquirrel/claude-handoff-baton)
[![Task Size Detection](https://img.shields.io/badge/Task%20Size-Dynamic-orange?style=flat-square)](https://github.com/quantsquirrel/claude-handoff-baton)

</div>

---

## Quick Start

### Option 1: Skill Only (Simplest)

```bash
curl -o ~/.claude/commands/handoff.md \
  https://raw.githubusercontent.com/quantsquirrel/claude-handoff-baton/main/SKILL.md
```

**Done.** Now you can use `/handoff` to save and resume context manually.

### Option 2: Full Install with Hooks (Recommended)

Get automatic context monitoring, compaction protection, and session restoration:

```bash
# Clone the repository
git clone https://github.com/quantsquirrel/claude-handoff-baton.git ~/.claude/skills/handoff

# Register all 4 hooks
cd ~/.claude/skills/handoff && bash hooks/install.sh
```

**Done.** Everything works automatically from here.

### What You Get

|  | Skill Only | Full Install |
|--|:---:|:---:|
| `/handoff` command | O | O |
| Auto token monitoring | - | O |
| Handoff reminder at threshold | - | O |
| Auto snapshot before compaction | - | O |
| Auto context restore on resume | - | O |

Start with **Option 1**, upgrade to **Option 2** when you want automation.

---

## Updating

### Marketplace Users

```bash
/plugin update handoff
```

### Git Clone Users

```bash
cd ~/.claude/skills/handoff && git pull
```

### Manual Install Users

Re-run the curl command from Quick Start to download the latest version.

---

## What is Handoff Baton?

**`--continue` restores conversations. Handoff passes a baton — distilled, structured, ready to run.**

| `--continue` (Raw History) | Handoff Baton (Distilled Knowledge) |
|---------------------------|-------------------------------|
| Loads entire message history (100K+ tokens) | Extracts essence in 100-500 tokens |
| Replays tool calls, file reads, errors | Captures decisions, failures, and next steps |
| Same session, same machine only | Clipboard: any session, any device, any AI |
| Doesn't highlight what failed | Explicitly tracks failed approaches |
| No prioritization of information | Smart auto-scaling for your needs |

**One command. One baton. 500x compression.**

---

## Why Not Just `--continue`?

`claude --continue` is great for short breaks. But it has limits:

- **Token bloat**: Restores *everything* — tool outputs, file contents, dead ends. Your 200K context fills fast.
- **No knowledge extraction**: Raw history doesn't highlight what matters. Failed approaches hide in noise.
- **Single-tool lock-in**: Only works within Claude Code. Can't share context with Claude.ai, teammates, or other AIs.
- **Reliability**: [Session resume bugs](https://github.com/anthropics/claude-code/issues/22107) can lose context silently.

**Handoff complements `--continue`:**

| Situation | Best Tool |
|-----------|-----------|
| Short break (< 30 min) | `claude --continue` |
| Long break (2+ hours) | `/handoff` → Cmd+V |
| Switching devices | `/handoff` → Cmd+V |
| Sharing context with team | `/handoff` |
| Context at 70%+ | `/handoff` |

---

## Usage

### Workflow

```
1. /handoff          → Context saved to clipboard
2. /clear            → Start fresh session
3. Cmd+V (paste)     → Resume with full context
```

### Commands

```bash
/handoff [topic]             # Smart handoff (auto-scales based on session complexity)
```

<sub>Examples: `/handoff` · `/handoff "auth migration"` · `/handoff "JWT refactor"`</sub>

| Situation | Command |
|-----------|---------|
| Context 70%+ reached | `/handoff` |
| Session checkpoint | `/handoff` |
| Session end | `/handoff` |
| Long break (2+ hours) | `/handoff` |

---

## Smart Auto-Scaling (v2.3 — L1/L2/L3)

Output depth adjusts automatically based on session complexity:

| Level | Budget | Trigger | Sections |
|-------|--------|---------|----------|
| **L1** | ~100 tokens | Under 10 messages OR 1 file modified | Time, Topic, Summary, Next Step |
| **L2** | ~300 tokens | 10-50 messages OR 2-10 files modified | L1 + User Requests, Key Decisions, Failed Approaches, Files Modified |
| **L3** | ~500 tokens | 50+ messages OR 10+ files modified | Full template (all sections) |

When message count and file count suggest different levels, the **higher** level wins. No manual level selection needed — just run `/handoff`.

---

## Context Fidelity (v2.3)

v2.3 preserves the original context more faithfully:

| Feature | Description |
|---------|-------------|
| **Phase 0 Validation** | Skips handoff when the session has no meaningful work |
| **User Requests** | Captures original user requests verbatim (10+ messages) |
| **Constraints** | Records user-stated constraints as-is (50+ messages) |
| **Perspective Guide** | Completed work in first person, pending work in objective voice |

### Phase 0: Empty Session Check

Before creating a handoff, the skill validates that at least one of these is true:
- A tool was used
- A file was modified
- A substantive user message exists

If none: `"No significant work in this session. Handoff skipped."`

### User Requests Section

Original user requests are captured verbatim — not paraphrased:

```markdown
## User Requests
- "JWT auth with refresh token rotation and RBAC"
- "Use async bcrypt, sync is too slow"
```

### Constraints Section

User-stated constraints are preserved exactly as spoken (full-detail sessions only):

```markdown
## Constraints
- "Use async bcrypt, sync is too slow"
- "Store tokens in httpOnly cookies, not localStorage"
```

---

## Workflow

```
Session 1 → /handoff → Cmd+V → Session 2
```

1. **Working** - You're deep in a coding session
2. **Save** - Run `/handoff` when context is high or before leaving
3. **Resume** - Paste in new session with `Cmd+V` (or `Ctrl+V`)

**No `/resume` command needed.** Just paste.

---

## What Gets Saved

Handoff captures what matters, scaled to session complexity:

- **Summary** — What happened in 1-3 sentences
- **User Requests** — Original requests verbatim (v2.3)
- **Completed / Pending tasks** — Progress tracking
- **Failed approaches** — Don't repeat mistakes
- **Key decisions** — Why you chose what you chose
- **Modified files** — What changed
- **Constraints** — User-stated constraints as-is (v2.3)
- **Next step** — Concrete next action

Sections with no content are automatically omitted.

---

## Task Size Detection (v2.0)

Handoff now intelligently detects task complexity and adjusts handoff timing accordingly.

### How It Works

1. **Prompt Analysis**
   - Scans your request for keywords like "전체", "리팩토링", "migrate", "entire"
   - Classifies task as Small / Medium / Large / XLarge

2. **File Count Detection**
   - Counts files from Glob/Grep results
   - Automatically upgrades task size when many files involved

3. **Dynamic Thresholds**
   - Suggests handoff earlier for complex tasks
   - Prevents context overflow on large refactors

### Example

```
You: "Refactor all authentication and migrate entire user database"

Large task detected - handoff will trigger at 50% (vs. 85% for small tasks)
```

This means you'll be prompted to create a handoff earlier, reducing the risk of losing progress.

---

## Security

Sensitive data is auto-detected and redacted:

```
API_KEY=sk-1234...  → API_KEY=***REDACTED***
PASSWORD=secret     → PASSWORD=***REDACTED***
Authorization: Bearer eyJ...  → Authorization: Bearer ***REDACTED***
```

**Detection includes:**
- API keys and secrets
- JWT tokens and Base64-encoded credentials
- Bearer tokens in Authorization headers
- Environment variables with sensitive patterns

**GDPR Consideration:** Handoff documents may contain personal data. Review handoffs before sharing with third parties and delete old handoffs regularly.

---

## Auto-Execution Prevention

The clipboard format includes safeguards to prevent Claude from auto-executing tasks:

```
<previous_session context="reference_only" auto_execute="false">
STOP: This is reference material from a previous session.
Do not auto-execute anything below. Wait for user instructions.
</previous_session>
```

---

## Optional: Auto-Handoff Hooks (v2.4)

**New in v2.4:** Context preservation across compaction + unified token tracking!

### 4 Hooks Overview

| Hook | File | Purpose |
|------|------|---------|
| **PrePromptSubmit** | `task-size-estimator.mjs` | Detects task complexity from prompt keywords |
| **PostToolUse** | `auto-handoff.mjs` | Monitors token usage, suggests `/handoff` at dynamic thresholds |
| **PreCompact** | `pre-compact.mjs` | Saves metadata snapshot before context compaction |
| **SessionStart** | `session-restore.mjs` | Restores best available context after compact/resume |

### Smart Context Monitoring

- Unified token tracking with call-level deduplication (no double-counting)
- Dynamic thresholds based on task size:
  - **Small tasks**: 85% / 90% / 95%
  - **Medium tasks**: 70% / 80% / 90%
  - **Large tasks**: 50% / 60% / 70%
  - **XLarge tasks**: 30% / 40% / 50%

### Context Preservation (v2.4)

- **PreCompact** saves git state, modified files, and token count before compaction
- **SessionStart** scores available sources by `score = base × freshness + relevance`
- Selects the single best source (handoff .md > pre-compact snapshot)
- Auto-cleans old snapshots (keeps last 3)

### Installation

```bash
# Clone for hook files
git clone https://github.com/quantsquirrel/claude-handoff-baton.git ~/.claude/skills/handoff

# Install all 4 hooks
cd ~/.claude/skills/handoff && bash hooks/install.sh
```

The installer registers all 4 hooks automatically.

### Debug Mode

```bash
AUTO_HANDOFF_DEBUG=1       # Context monitoring logs
PRE_COMPACT_DEBUG=1        # Pre-compact snapshot logs
SESSION_RESTORE_DEBUG=1    # Session restore scoring logs
```

### Limitations

- **Single-node only**: File locking uses local filesystem locks.

---

## Project Structure

```
claude-handoff-baton/
├── SKILL.md                     # The skill (copy to ~/.claude/commands/)
├── README.md
├── hooks/
│   ├── utils.mjs                # Shared utilities (lock, state I/O, token tracking)
│   ├── constants.mjs            # Shared constants, thresholds, security patterns
│   ├── schema.mjs               # JSON schema for structured handoff output
│   ├── task-size-estimator.mjs  # PrePromptSubmit: Task size detection
│   ├── auto-handoff.mjs         # PostToolUse: Context monitoring
│   ├── auto-checkpoint.mjs      # PostToolUse: Time/token-based checkpoint trigger
│   ├── pre-compact.mjs          # PreCompact: Metadata snapshot before compaction
│   ├── session-restore.mjs      # SessionStart: Context restoration after compact/resume
│   ├── lockfile.mjs             # Lock file management for interrupted handoffs
│   ├── recover.mjs              # Recovery script for interrupted handoffs
│   ├── install.sh               # Easy installation (registers all 4 hooks)
│   └── test-task-size.mjs       # Integration tests
├── plugins/
│   └── handoff/
│       ├── plugin.json          # Plugin manifest (v2.2)
│       └── skills/
│           └── handoff.md       # Skill definition with smart auto-scaling
└── examples/
    └── example-handoff.md
```

---

## License

**MIT License** - See [LICENSE](LICENSE) for details.

---

## Contributing

Issues and PRs welcome at [GitHub](https://github.com/quantsquirrel/claude-handoff-baton).

---

**Ready to pass the baton?** Run `/handoff` — don't pass raw history, pass distilled knowledge.

<div align="right"><a href="#top">Back to Top</a></div>
