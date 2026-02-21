# Synod v3.2 - Agent Architecture

**Project:** Multi-agent deliberation system for Claude Code
**Version:** 3.2.0
**Repository:** https://github.com/quantsquirrel/claude-synod-debate
**License:** MIT

Synod orchestrates Claude, Gemini, and OpenAI in a structured judicial debate (Solver, Critic, Defense, Synthesis) to produce higher-quality decisions than any single model. Implements SID confidence scoring, CortexDebate trust scores, Free-MAD anti-conformity, and ReConcile convergence.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (Entry Point)                 │
│                    /synod [mode] <prompt>                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    SYNOD ORCHESTRATOR                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  VALIDATOR   │  │  ARCHITECT   │  │  EXPLORER    │      │
│  │  (Claude)    │  │  (Gemini)    │  │  (OpenAI)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│    Phase 0: Classification + Setup                          │
│    Phase 1: Solver Round (Parallel)                         │
│    Phase 2: Critic Round (Trust Scores)                     │
│    Phase 3: Defense Round (Court Model)                     │
│    Phase 4: Synthesis (Final Output + Quality Metrics)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Roles

| Agent | Model | Role | Solver Focus | Defense Role |
|-------|-------|------|-------------|-------------|
| Claude | Sonnet | Orchestrator + Judge | Correctness validation | Neutral arbiter |
| Gemini | flash/pro | Architect | Patterns, structure | Defense counsel |
| OpenAI | gpt-4o/o3 | Explorer | Edge cases, alternatives | Prosecution |

Phase flow details: `skills/modules/synod-phase{0-4}-*.md`

---

## Phase Flow

1. **Phase 0 - Setup** (`synod-phase0-setup.md`): Classify problem type (coding/math/creative/general), determine complexity, select models, create session. Confidence-based tier promotion when classifier confidence is low.
2. **Phase 1 - Solver** (`synod-phase1-solver.md`): Parallel execution of all agents. SID format required (confidence + semantic_focus). Early exit if all agents confident (>=90).
3. **Phase 2 - Critic** (`synod-phase2-critic.md`): Cross-validation, trust score calculation (CRIS), contention identification. Free-MAD anti-conformity hints for low-confidence models.
4. **Phase 3 - Defense** (`synod-phase3-defense.md`): Adversarial court model. Gemini defends strongest solution; OpenAI prosecutes. Claude judges.
5. **Phase 4 - Synthesis** (`synod-phase4-synthesis.md`): Weighted confidence calculation, mode-specific output, debate quality metrics summary.

Error handling and fallbacks: `skills/modules/synod-error-handling.md`
Session resume protocol: `skills/modules/synod-resume.md`

---

## Core Algorithms

### CRIS Trust Score (CortexDebate)

```
T = min((C x R x I) / S, 2.0)

C = Credibility (0-1): Evidence quality
R = Reliability (0-1): Logical consistency
I = Intimacy (0-1): Relevance to problem
S = Self-Orientation (0.1-1): Bias detection (lower = better)
```

| Rating | Score Range | Action |
|--------|-----------|--------|
| High | T >= 1.5 | Primary source |
| Good | T >= 1.0 | Include normally |
| Acceptable | T >= 0.5 | Include with caution |
| Low | T < 0.5 | Consider excluding |

Confidence intervals and weighted consensus: `tools/synod-parser.py` (`calculate_confidence_interval`, `weighted_consensus`)

### SID Format (Self-Signals Driven)

```xml
<confidence score="[0-100]">
  <evidence>[What supports this?]</evidence>
  <logic>[Reasoning soundness?]</logic>
  <expertise>[Domain confidence?]</expertise>
  <can_exit>[true if confidence >= 90 AND complete]</can_exit>
</confidence>

<semantic_focus>
1. [PRIMARY claim]
2. [SECONDARY claim]
3. [TERTIARY claim]
</semantic_focus>
```

Malformed responses get defaults (C=50, can_exit=false) via `apply_defaults()`.

### Debate Quality Metrics

`parse_response()` emits per-response metrics: response_length, format_compliance, confidence_score, semantic_focus_count, has_evidence, has_logic, has_code. Aggregated via `collect_round_metrics()` and displayed in Phase 4 via `format_metrics_summary()`.

### Confidence-to-Tier Promotion

`get_tier(complexity, confidence)` promotes queries one tier level when classifier confidence is below the `low_confidence` threshold (default 50%). E.g., simple+low_confidence -> standard tier.

---

## Directory Structure

```
claude-synod-debate/
├── AGENTS.md                        # This file
├── CHANGELOG.md
├── README.md
├── plugin.json                      # Plugin metadata
├── marketplace.json                 # Marketplace listing
├── pyproject.toml                   # Python config + dependencies
├── config/
│   ├── synod-modes.yaml             # 5 modes + keywords + thresholds
│   └── synod-templates.yaml         # Mode output templates
├── skills/
│   ├── synod.md                     # Main /synod orchestrator
│   ├── synod-setup.md               # /synod-setup installer
│   ├── cancel-synod.md              # /cancel-synod command
│   └── modules/                     # Modularized phase instructions
│       ├── synod-phase0-setup.md
│       ├── synod-phase1-solver.md
│       ├── synod-phase2-critic.md
│       ├── synod-phase3-defense.md
│       ├── synod-phase4-synthesis.md
│       ├── synod-error-handling.md
│       └── synod-resume.md
├── tools/                           # Core Python tools
│   ├── base_provider.py             # Abstract CLI provider base class
│   ├── gemini-3.py                  # Gemini API integration
│   ├── openai-cli.py                # OpenAI API integration
│   ├── synod-parser.py              # SID parsing + CRIS trust + metrics
│   ├── synod-classifier.py          # Auto mode/complexity classification
│   ├── synod_config.py              # YAML config loader + tier routing
│   ├── synod_progress.py            # Rich progress visualization
│   ├── synod-setup.py               # CLI tool installer
│   ├── test_security.py             # Security validation tests
│   ├── providers/extended/          # Optional provider integrations
│   │   ├── deepseek-cli.py
│   │   ├── groq-cli.py
│   │   ├── grok-cli.py             # Requires SYNOD_ENABLE_GROK=1
│   │   ├── mistral-cli.py          # Requires SYNOD_ENABLE_MISTRAL=1
│   │   └── openrouter-cli.py
│   └── archived/                    # Disabled features
│       ├── canary.py
│       ├── synod-canary.py
│       └── model_stats.py
├── tests/                           # pytest test suite
│   └── archived/                    # Tests for archived features
└── benchmark/                       # GSM8K evaluation suite
```

---

## Tool Ecosystem

| Tool | Purpose | Key Functions |
|------|---------|---------------|
| `synod-parser.py` | SID signal extraction, trust scores, quality metrics | `parse_response`, `calculate_trust_score`, `weighted_consensus`, `collect_round_metrics`, `format_metrics_summary` |
| `synod-classifier.py` | Auto mode + complexity classification | `classify_mode`, `classify_complexity`, `classify_problem_type` |
| `synod_config.py` | YAML config access + tier routing | `load_config`, `get_tier`, `get_template`, `get_threshold` |
| `synod_progress.py` | Rich terminal progress display | JSON event protocol via FIFO pipe |
| `base_provider.py` | Abstract base for CLI providers | `BaseProvider` with timeout, retry, validation |
| `gemini-3.py` | Gemini API (flash/pro, thinking, temperature) | `GeminiProvider` |
| `openai-cli.py` | OpenAI API (gpt-4o/o3, reasoning levels) | `OpenAIProvider` |

---

## Mode Configuration

Defined in `config/synod-modes.yaml`. Output templates in `config/synod-templates.yaml`.

| Mode | Gemini | OpenAI | Rounds | Focus |
|------|--------|--------|--------|-------|
| review | flash | o3 (medium) | 3 | Code quality, best practices |
| design | pro | o3 (high) | 4 | Architecture, trade-offs |
| debug | flash | o3 (high) | 3 | Root cause analysis |
| idea | pro | gpt-4o | 4 | Brainstorming, feasibility |
| general | flash | gpt-4o | 3 | Balanced comprehensive answer |

---

## Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `SYNOD_V2_AUTO_CLASSIFY` | `1` | Auto mode/complexity classification |
| `SYNOD_V2_DYNAMIC_ROUNDS` | `1` | Dynamic round count based on convergence |
| `SYNOD_V2_ADAPTIVE_TIMEOUT` | `0` | P99-based timeout adjustment |
| `SYNOD_ENABLE_GROK` | required | Enable Grok provider |
| `SYNOD_ENABLE_MISTRAL` | required | Enable Mistral provider |

---

## Development

**Test commands:**
```bash
python3 -m pytest tests/ --tb=short -q          # Full suite
python3 -m pytest tests/ --cov=tools --cov-report=term-missing  # Coverage
```

**Commit format:** `{type}: {subject}` (feat/fix/refactor/test/docs/chore)

**Environment:**
```bash
export GEMINI_API_KEY="..."   # Required
export OPENAI_API_KEY="..."   # Required
```

---

**Last Updated:** 2026-02-21
**Status:** Complete (v3.2.0)
