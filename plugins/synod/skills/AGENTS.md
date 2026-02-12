<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31T00:00:00Z -->

# Skills Directory - Synod Multi-Agent Deliberation System

This directory contains Claude Code skill definitions for the Synod v1.0 multi-agent deliberation plugin. Skills are executable commands that users invoke via the Claude Code CLI to trigger structured multi-model debate.

**Directory:** `/Users/ahnjundaram_g/dev/tools/synod-plugin/skills/`

---

## Overview

Synod provides two primary skills:

| Skill | Command | Purpose |
|-------|---------|---------|
| **synod** | `/synod [mode] <prompt>` | Main multi-agent deliberation system with 5 specialized modes |
| **cancel-synod** | `/cancel-synod` | Cancel active Synod session and preserve state |

---

## Skill Definitions

### 1. synod.md - Multi-Agent Deliberation Orchestrator

**Description:** Multi-agent debate system with Gemini and OpenAI integration (Synod v1.0)

**File:** `synod.md`

**Metadata:**
```yaml
description: Multi-agent debate system with Gemini and OpenAI integration (Synod v1.0)
argument-hint: [mode] [prompt] - modes: review|design|debug|idea|resume
allowed-tools: [Read, Write, Bash, Glob, Grep, Task]
```

**Invocation:**
```bash
/synod [mode] <prompt>
/synod <prompt>                    # general mode (default)
/synod resume                      # resume previous session
```

#### Modes

| Mode | Use Case | Gemini Model | OpenAI Model | Rounds | Temperature |
|------|----------|--------------|--------------|--------|-------------|
| `review` | Code review and static analysis | Flash (high thinking) | o3 (medium reasoning) | 3 | 0.7 / 0.5 |
| `design` | Architecture and system design decisions | Pro (high thinking) | o3 (high reasoning) | 4 | 0.7 / 0.5 |
| `debug` | Debugging, troubleshooting, root cause analysis | Flash (high thinking) | o3 (high reasoning) | 3 | 0.7 / 0.5 |
| `idea` | Brainstorming, ideation, concept exploration | Pro (high thinking) | gpt4o (standard) | 4 | 0.7 |
| `general` | General questions, explanations, comparisons | Flash (medium thinking) | gpt4o (standard) | 3 | 0.7 |

#### Model Personas

Each model assumes a specific analytical perspective:

- **Claude (Validator):** Focuses on correctness, best practices, and system integration. Validates claims against known facts.
- **Gemini (Architect):** Explores structure, patterns, and systematic approaches. Identifies architectural implications and trade-offs.
- **OpenAI (Explorer):** Challenges assumptions, explores edge cases, and finds counter-examples. Identifies what others might miss.

#### Execution Flow

**Phase 0: Classification & Setup**
- Parse command arguments and determine mode
- Classify problem type (coding, math, creative, general)
- Determine complexity (simple, medium, complex)
- Select model configurations based on mode
- Create session directory and initialize state

**Phase 1: Solver Round (Parallel)**
- Generate three independent solutions simultaneously
- Claude as Validator
- Gemini as Architect
- OpenAI as Explorer
- Each provides confidence scores and semantic focus points
- Early exit if all models reach high consensus (score >= 90, can_exit: true)

**Phase 2: Critic Round (Cross-Validation)**
- Identify agreement points between models
- Identify contentions and conflicts
- Calculate Trust Scores using CortexDebate formula
- Soft defer for low-confidence models to prevent premature consensus

**Phase 3: Defense Round (Court Model)**
- Assign roles: Judge (Claude), Defense Lawyer (Gemini), Prosecutor (OpenAI)
- Select solution with highest Trust Score as defendant
- Structured adversarial debate
- Anti-conformity instructions prevent consensus-seeking

**Phase 4: Synthesis**
- Compile final evidence from all rounds
- Calculate final confidence (weighted by Trust Scores)
- Generate mode-specific output
- Include deliberation process visualization
- Save complete session state

#### Output Format

All agents output structured XML with:

```xml
<confidence score="[0-100]">
  <evidence>[Supporting facts and documentation]</evidence>
  <logic>[Reasoning chain and assumptions]</logic>
  <expertise>[Domain confidence assessment]</expertise>
  <can_exit>[true if discussion can close]</can_exit>
</confidence>

<semantic_focus>
1. [PRIMARY point for debate]
2. [SECONDARY point - supporting argument]
3. [TERTIARY point - additional consideration]
</semantic_focus>
```

#### Confidence Score Interpretation

| Score | Interpretation | Action |
|-------|-----------------|--------|
| 80-100 | High confidence, consensus-ready | Consider closing debate |
| 60-79 | Moderate confidence, needs refinement | Continue deliberation |
| 40-59 | Low confidence, significant uncertainty | Extend analysis |
| 0-39 | Very low confidence, major doubts | Reassess problem framing |

#### Trust Score Calculation (CortexDebate)

Trust Score formula: `T = min((C × R × I) / S, 2.0)`

Where:
- **C (Credibility):** Evidence quality (0-1) - are claims verifiable?
- **R (Reliability):** Logical consistency (0-1) - do arguments follow logically?
- **I (Informativeness):** Relevance to problem (0-1) - does solution address the issue?
- **S (Self-Orientation):** Bias/agenda (0.1-1.0) - is perspective neutral?

**Trust Score Thresholds:**
- T < 0.5 = Exclude from synthesis (unless all are low)
- T >= 0.5 = Acceptable
- T >= 1.0 = Good trust
- T >= 1.5 = High trust (primary source)
- T >= 2.0 = Maximum confidence (capped at 2.0)

#### Session Management

Sessions stored in `~/.synod/sessions/` (configurable via `SYNOD_SESSION_DIR`):

```
synod-YYYYMMDD-HHMMSS-xxx/
├── meta.json                    # Session metadata
├── status.json                  # Current session status
├── round-1-solver/              # Solver outputs
│   ├── claude-response.md
│   ├── claude-parsed.json
│   ├── gemini-response.md
│   ├── gemini-parsed.json
│   ├── openai-response.md
│   ├── openai-parsed.json
│   └── parsed-signals.json
├── round-2-critic/              # Critic outputs
│   ├── aggregation.md
│   ├── gemini-critique.md
│   ├── openai-critique.md
│   ├── trust-scores.json
│   └── contentions.json
├── round-3-defense/             # Defense/Prosecution outputs
│   ├── judge-deliberation.md
│   ├── defense-args.md
│   ├── prosecution-args.md
│   └── preliminary-ruling.md
└── round-4-synthesis.md         # Final output
```

#### Resume Capability

Continue interrupted sessions:

```bash
/synod resume                          # Resume most recent session
/synod resume synod-20260124-143022-a1b  # Resume specific session
```

Resume preserves:
- All completed round outputs
- Trust Score calculations
- Model configurations
- Debate context and contentions
- Session state tracking

#### Error Handling & Fallbacks

**Timeout Fallback Chain:**
1. Retry with downgraded thinking/reasoning level
2. Retry with lower model tier (flash instead of pro, gpt4o instead of o3)
3. Continue without model if retries exhausted (note in synthesis)

**Format Enforcement:**
- If response lacks required XML blocks, send re-prompt with format reminder
- Max 2 retries per model per round
- Apply defaults if all retries fail (confidence score 50, format_warning flag)

**Low Trust Score Fallback:**
- Never exclude all agents even if all Trust Scores < 0.5
- Keep agent with highest score
- Add warning note to synthesis
- Cap final confidence at 60%

**API Error Handling:**
- Rate limit detected → wait 30 seconds, retry
- Auth error → report and halt
- Network error → apply fallback chain

#### Configuration Requirements

**Required Environment Variables:**
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

**Optional:**
```bash
export SYNOD_SESSION_DIR="~/.synod/sessions"  # Default: ~/.synod/sessions
```

**System Dependencies:**
- Python 3.9+
- jq (JSON processor)
- openssl (random session ID generation)
- Bash 4.0+

#### CLI Tools Required

| Tool | Purpose | Fallback |
|------|---------|----------|
| `gemini-3` | Gemini API wrapper with temperature/thinking support | Auto-downgrade to flash |
| `openai-cli` | OpenAI API wrapper with reasoning support | Auto-switch to gpt4o |
| `synod-parser` | Parse confidence scores and semantic focus | Inline parser fallback |

#### Examples

**Code Review Mode:**
```bash
/synod review Analyze the performance of this function: def fibonacci(n): return fibonacci(n-1) + fibonacci(n-2)
```

**Architecture Design:**
```bash
/synod design Design a JWT authentication system for a microservices architecture
```

**Debugging:**
```bash
/synod debug Why is my async/await code hanging? [shows code snippet]
```

**Brainstorming Ideas:**
```bash
/synod idea How can we improve user onboarding flow for our SaaS product?
```

**General Question:**
```bash
/synod What are the trade-offs between SQL and NoSQL databases?
```

#### Performance Characteristics

- **Debate Duration:** Typically 2-5 minutes per session (depends on model response times)
- **Token Usage:** ~5,000-15,000 tokens per 3-round debate (varies by prompt length)
- **Parallel Execution:** Solver and Critic rounds execute models in parallel within timeout window
- **Timeout Limits:** 110s per model per round, 120s outer timeout per round
- **Session Retention:** Sessions preserved indefinitely (manual cleanup recommended after 30 days)

---

### 2. cancel-synod.md - Session Cancellation

**Description:** Cancel active Synod deliberation session

**File:** `cancel-synod.md`

**Metadata:**
```yaml
description: Cancel active Synod deliberation session
allowed-tools: [Read, Write, Bash, Glob]
```

**Invocation:**
```bash
/cancel-synod
```

#### Functionality

Cancels the currently active Synod session:

1. **Find Active Session:** Searches `${SYNOD_SESSION_DIR:-~/.synod/sessions}` for sessions with status != "complete"
2. **Kill Processes:** Terminates any background processes (gemini-3, openai-cli)
3. **Update Status:** Marks session status as "cancelled" in status.json
4. **Preserve State:** All completed round data retained for audit/resumption

#### Output

```
Session synod-20260124-143022-a1b cancelled at round 2.
Partial results preserved in ~/.synod/sessions/synod-20260124-143022-a1b/
```

#### Special Cases

- **No Active Session:** Reports "No active Synod session found."
- **Session Already Complete:** Reports "Session is already complete. Start a new session." (user should use new `/synod` command)
- **Multiple Active Sessions:** Cancels the most recent one (highest mtime)

#### State Preservation

Cancelled sessions can be analyzed:
- Inspect partial outputs in session directory
- Review Trust Scores and contentions up to cancellation point
- Extract any completed analyses or suggestions

---

## Skill Architecture

### File Structure

Each skill is a self-contained markdown file with:

**YAML Frontmatter:**
- `description`: Brief description for CLI help text
- `argument-hint`: Usage hints and valid arguments
- `allowed-tools`: List of tools the skill can invoke

**Content Sections:**
- Overview and purpose
- Configuration requirements
- Execution logic (often pseudo-code with comments)
- Error handling strategies
- Output format specifications

### Tool Access

Skills have restricted tool access:

| Tool | synod | cancel-synod |
|------|:-----:|:--------:|
| Read | ✓ | ✓ |
| Write | ✓ | ✓ |
| Bash | ✓ | ✓ |
| Glob | ✓ | ✓ |
| Grep | ✓ | - |
| Task | ✓ | - |

### State Management

Both skills manage persistent state in `${SYNOD_SESSION_DIR}`:

- **meta.json:** Session metadata, mode, problem summary, model configurations
- **status.json:** Current round, resume point, completion status
- **Round directories:** Structured outputs from each debate phase
- **Timestamp tracking:** ISO 8601 timestamps for all state changes

---

## Integration Points

### Parent Directory Dependencies

Skills depend on tools in `../tools/`:

| Tool | Location | Purpose |
|------|----------|---------|
| `synod-parser.py` | `../tools/synod-parser.py` | Parse confidence scores, calculate Trust Scores |
| `gemini-3.py` | `../tools/gemini-3.py` | Gemini API integration wrapper |
| `openai-cli.py` | `../tools/openai-cli.py` | OpenAI API integration wrapper |

### Plugin Configuration

Defined in `../plugin.json`:

```json
{
  "skills": ["synod", "cancel-synod"],
  "tools": ["synod-parser.py", "gemini-3.py", "openai-cli.py"],
  "config": {
    "GEMINI_API_KEY": {"required": true},
    "OPENAI_API_KEY": {"required": true},
    "SYNOD_SESSION_DIR": {"required": false, "default": "~/.synod/sessions"}
  }
}
```

---

## Testing Checklist

### Synod Skill Testing

- [ ] **Mode Testing:**
  - [ ] `/synod review` with code snippet
  - [ ] `/synod design` with architectural requirements
  - [ ] `/synod debug` with error/bug description
  - [ ] `/synod idea` with brainstorming prompt
  - [ ] `/synod general` with general question
  - [ ] `/synod <prompt>` (implicit general mode)

- [ ] **Resume Testing:**
  - [ ] `/synod resume` resumes most recent session
  - [ ] `/synod resume synod-XXXXX` resumes specific session
  - [ ] Partial outputs are preserved
  - [ ] Session state is correctly restored

- [ ] **Error Handling:**
  - [ ] Timeout gracefully downgrades models
  - [ ] Missing API keys are reported
  - [ ] Session directory creation works
  - [ ] Format enforcement re-prompting works
  - [ ] Fallback parsers activate without synod-parser

- [ ] **Output Validation:**
  - [ ] XML confidence blocks are valid
  - [ ] Semantic focus has 3 points
  - [ ] Trust Scores are calculated correctly
  - [ ] Final synthesis includes all required sections
  - [ ] Mode-specific output format matches specification

### Cancel-Synod Skill Testing

- [ ] **Cancellation:**
  - [ ] `/cancel-synod` cancels active session
  - [ ] Status is marked as "cancelled"
  - [ ] Background processes are killed
  - [ ] Partial state is preserved

- [ ] **Special Cases:**
  - [ ] Correctly reports when no active session exists
  - [ ] Correctly handles multiple active sessions
  - [ ] Correctly handles already-completed sessions

### Session Management Testing

- [ ] **Directory Creation:**
  - [ ] Session directory structure created correctly
  - [ ] meta.json contains all required fields
  - [ ] status.json initializes properly

- [ ] **State Persistence:**
  - [ ] Round outputs saved to correct directories
  - [ ] JSON state files are valid
  - [ ] File permissions allow read/write

- [ ] **Cleanup:**
  - [ ] Old sessions can be manually deleted
  - [ ] Cleanup doesn't affect active sessions
  - [ ] Session archival works correctly

---

## Debugging Guide

### Enable Verbose Logging

Set environment variable for detailed output:
```bash
export SYNOD_DEBUG=1
```

This enables:
- Full API request/response logging
- Model selection rationale
- Trust Score calculation details
- Timeout and retry information

### Inspect Session State

View session details:
```bash
# List all sessions
ls -la ~/.synod/sessions/

# Inspect specific session
cat ~/.synod/sessions/synod-YYYYMMDD-HHMMSS-xxx/meta.json
cat ~/.synod/sessions/synod-YYYYMMDD-HHMMSS-xxx/status.json

# View solver outputs
cat ~/.synod/sessions/synod-YYYYMMDD-HHMMSS-xxx/round-1-solver/parsed-signals.json

# View trust scores
cat ~/.synod/sessions/synod-YYYYMMDD-HHMMSS-xxx/round-2-critic/trust-scores.json
```

### Common Issues

**"[Synod Error] 문제 또는 프롬프트가 필요합니다"**
- Cause: Empty or whitespace-only prompt
- Fix: Provide actual content to `/synod` command

**"API key not found"**
- Cause: Missing GEMINI_API_KEY or OPENAI_API_KEY
- Fix: `export GEMINI_API_KEY="..."; export OPENAI_API_KEY="..."`

**"Timeout after 3 retries"**
- Cause: Model API not responding
- Fix: Check network, verify API status, increase timeout if needed

**"synod-parser not found"**
- Cause: Tool not in PATH
- Fix: Use inline fallback (automatic) or add to PATH

**"Permission denied: ~/.synod/sessions"**
- Cause: Directory not writable
- Fix: `mkdir -p ~/.synod/sessions && chmod 755 ~/.synod/sessions`

---

## Related Documentation

- **Parent Directory:** See `../AGENTS.md` for project-level architecture
- **Plugin Configuration:** See `../plugin.json` for requirements and settings
- **Main README:** See `../README.md` for overview and examples
- **Tools Directory:** See `../tools/AGENTS.md` for tool specifications
- **Benchmark Directory:** See `../benchmark/AGENTS.md` for performance data

---

## Quick Reference Table

| Command | Mode | Use | Output |
|---------|------|-----|--------|
| `/synod review <code>` | review | Static analysis, code quality | Issues ranked by severity |
| `/synod design <spec>` | design | Architecture decisions | Recommendations with trade-offs |
| `/synod debug <error>` | debug | Troubleshooting | Root cause + fix + prevention |
| `/synod idea <topic>` | idea | Brainstorming | Ranked ideas with pros/cons |
| `/synod <question>` | general | General questions | Balanced comprehensive answer |
| `/synod resume` | - | Continue session | Restores from checkpoint |
| `/cancel-synod` | - | Stop session | Cancels and preserves state |

---

**Generated:** 2026-01-31
**Version:** Synod v1.0
**Skills:** 2 (synod, cancel-synod)
**Status:** Complete
