# Synod v1.0 - Agent Architecture Documentation

**Project:** Multi-agent deliberation system for Claude Code
**Version:** 1.0.0
**Generated:** 2026-01-31
**License:** MIT
**Repository:** https://github.com/quantsquirrel/claude-synod-debate

---

## Executive Summary

Synod v3.0 is a structured deliberation framework that orchestrates multiple LLM models (Claude, Gemini, OpenAI) in a multi-round debate to produce higher-quality decisions than any single model. The system implements state-of-the-art multi-agent research methodologies:

- **SID (Self-Signals Driven)**: Confidence scoring with semantic focus
- **CortexDebate**: Trust score calculation with evidence weighting
- **Free-MAD (Majority Aversion Debate)**: Anti-conformity instructions
- **ReConcile**: 3-4 round convergence pattern

The orchestrator (Claude) manages the entire deliberation process, coordinating specialized agent roles across phases: Solver → Critic → Defense/Prosecution → Synthesis.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Agent Roles and Responsibilities](#agent-roles-and-responsibilities)
3. [Data Flow and Orchestration](#data-flow-and-orchestration)
4. [Core Algorithms](#core-algorithms)
5. [Directory Structure](#directory-structure)
6. [Tool Ecosystem](#tool-ecosystem)
7. [Session Management](#session-management)
8. [Mode-Specific Configurations](#mode-specific-configurations)
9. [Error Handling and Fallbacks](#error-handling-and-fallbacks)
10. [Development Guidelines](#development-guidelines)
11. [Integration Points](#integration-points)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (Entry Point)                 │
│                    /synod [mode] <prompt>                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    SYNOD ORCHESTRATOR                        │
│                   (Claude v3 Haiku)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  VALIDATOR   │  │  ARCHITECT   │  │  EXPLORER    │      │
│  │  (Claude)    │  │  (Gemini)    │  │  (OpenAI)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│    Phase 0: Classification, Setup, State Creation            │
│    Phase 1: Solver Round (Parallel Execution)               │
│    Phase 2: Critic Round (Cross-Validation, Trust Scores)   │
│    Phase 3: Defense Round (Court Model - Adversarial)       │
│    Phase 4: Synthesis (Final Output Generation)             │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               SESSION STATE MANAGEMENT                       │
│           (~/.synod/sessions/synod-YYYYMMDD-HHMMSS-xxx/)    │
│  ├── meta.json (configuration & mode)                       │
│  ├── status.json (progress tracking)                        │
│  ├── round-1-solver/ (initial solutions)                    │
│  ├── round-2-critic/ (validations & trust scores)           │
│  ├── round-3-defense/ (court arguments)                     │
│  └── round-4-synthesis.md (final output)                    │
└─────────────────────────────────────────────────────────────┘
```

### Core Concept: Structured Debate

Synod implements a **judicial deliberation model** where:

1. **Solver Round**: Each agent independently solves the problem
2. **Critic Round**: Each agent validates claims and identifies issues
3. **Defense Round**: Strongest solution defended vs. attacked (court model)
4. **Synthesis**: Judge (Claude) weighs evidence and produces final answer

This structure prevents groupthink through:
- **Anti-conformity instructions** (Free-MAD): Agents instructed to maintain independent perspectives
- **Adversarial roles**: Defense vs. Prosecution creates productive tension
- **Trust scoring**: Weighted by evidence quality, not majority vote

---

## Agent Roles and Responsibilities

### Primary Agents

#### 1. Claude Validator (Orchestrator & Judge)

**Role:** Central coordinator managing entire deliberation workflow

**Responsibilities:**
- Parse and validate user input
- Classify problem type (coding, math, creative, general)
- Determine complexity (simple, medium, complex)
- Create and manage session state
- Execute Phase 0 (Classification) setup
- Run Solver pass with validator persona
- Aggregate Solver round responses
- Execute Critic analysis and aggregation
- Assign court roles and make preliminary rulings
- Generate final synthesized output with confidence weighting
- Handle resume capability

**Key Personas:**
- **VALIDATOR (Solver Phase)**: Correctness-focused analysis
- **JUDGE (Defense Phase)**: Neutral arbiter weighing evidence
- **ORCHESTRATOR (All Phases)**: Coordinates external models

**Model:** Claude 3.5 Sonnet (or specified override)
**Thinking:** Enabled for complex reasoning
**Temperature:** Varies by phase (0.5-0.7)

---

#### 2. Gemini Architect (Creative Solver & Defender)

**Role:** Structural and architectural problem solver

**Responsibilities (Solver Phase):**
- Focus on patterns, structure, systematic approaches
- Identify architectural implications and trade-offs
- Provide evidence-based recommendations
- Generate SID confidence scores with semantic focus

**Responsibilities (Critic Phase):**
- Validate architectural claims
- Assess design trade-offs
- Identify missing considerations
- Lower temperature (0.5) for analytical evaluation

**Responsibilities (Defense Phase):**
- Defend strongest solution against attack
- Strengthen weak arguments with evidence
- Address counter-examples from prosecution
- Explain why alternatives are inferior
- Maintain independent perspective (Free-MAD)

**Model Options:**
- `gemini-2.0-flash`: Fast, suitable for review/debug modes (default)
- `gemini-2.0-pro`: Advanced reasoning for design/idea modes

**Temperature:**
- Solver: 0.7 (balance creativity + accuracy)
- Critic: 0.5 (analytical evaluation)
- Defense: 0.7 (argumentative strength)

**Thinking:** High or Medium (configurable per mode)

---

#### 3. OpenAI Explorer (Edge Case Finder & Prosecutor)

**Role:** Alternative approaches and counter-arguments

**Responsibilities (Solver Phase):**
- Challenge assumptions and explore edge cases
- Find counter-examples and potential failures
- Identify what architects might miss
- Alternative interpretations of the problem

**Responsibilities (Critic Phase):**
- Find counter-examples that break solutions
- Identify logical flaws and false premises
- Suggest alternative interpretations
- High temperature for exploratory thinking

**Responsibilities (Defense Phase):**
- Attack proposed solution with evidence
- Find fatal flaws and failure modes
- Propose superior alternatives with justification
- Maintain independent perspective (Free-MAD)

**Model Options:**
- `gpt-4o`: General queries and idea mode (fast)
- `o3`: Complex reasoning (review/debug/design modes)
- `o3-mini`: Cost-efficient alternative

**Temperature:**
- Solver (gpt4o): 0.7
- Critic (gpt4o): 0.7
- Prosecution (o3): **Fixed at 1.0** (o3 doesn't support temperature adjustment)

**Reasoning Effort (o3 only):**
- review: medium (balanced analysis)
- design: high (deep architectural reasoning)
- debug: high (root cause analysis)
- idea: medium (creative exploration)
- general: low (fast response)

---

### Agent Interaction Patterns

```
Round 1 (Solver) - Parallel Execution:
  Claude ────────────┐
  Gemini ────────────┼──► SID Signals (confidence scores)
  OpenAI ────────────┘    └─ Semantic focus points

Round 2 (Critic) - Cross-Validation:
  Claude (aggregates) ──────┐
                             ├──► Trust Scores (C×R×I/S)
  Gemini (validates) ────────┼──► Contentions identified
  OpenAI (attacks) ──────────┘    └─ Claims disputed

Round 3 (Defense) - Adversarial Court:
  Claude (judge) ──────────────────┐
  Gemini (defense, strongest sol) ─┼──► Preliminary Ruling
  OpenAI (prosecution, attacks) ───┘    └─ Winner determined

Round 4 (Synthesis):
  Claude (integrates all rounds) ──► Final Answer
    with confidence weighting
    based on trust scores
```

---

## Data Flow and Orchestration

### Phase 0: Classification & Setup

**Input:** User prompt and optional mode selector
**Output:** Session state initialized, configuration loaded

**Steps:**
1. Parse arguments: Extract mode (review/design/debug/idea/general) and problem
2. Validate input: Ensure problem is non-empty (except for resume)
3. Classify problem type: coding|math|creative|general
4. Determine complexity: simple|medium|complex
5. Select model configuration: Based on mode and complexity
6. Generate session ID: `synod-YYYYMMDD-HHMMSS-{random}`
7. Create session directory structure
8. Initialize `meta.json` and `status.json`

**Error Handling:**
- Empty problem without resume mode → Display usage and exit
- Invalid mode → Fallback to general mode
- Directory creation failure → Fall back to temp directory

---

### Phase 1: Solver Round

**Objective:** Gather independent solutions from all agents

**Execution Model:** Parallel (Gemini and OpenAI run concurrently)

**Process:**

1. **Prepare Prompts**
   - Generate Claude prompt (validator persona)
   - Generate Gemini prompt (architect persona)
   - Generate OpenAI prompt (explorer persona)
   - All include problem context and mode-specific focus

2. **Execute External Models (Parallel)**
   ```bash
   # Gemini execution
   timeout 110 gemini-3 --model {MODEL} --thinking {LEVEL} \
     --temperature 0.7 < prompt.txt > response.txt 2>&1 &

   # OpenAI execution
   timeout 110 openai-cli --model {MODEL} {--reasoning LEVEL} \
     < prompt.txt > response.txt 2>&1 &

   # Wait for both with outer timeout
   ```

3. **Validate Responses**
   - Check exit codes (0 = success, 124/timeout = retry)
   - Validate SID format (confidence + semantic_focus blocks required)
   - Apply format enforcement protocol if XML missing

4. **Parse SID Signals**
   - Extract confidence scores (0-100)
   - Extract semantic focus points (3 key claims)
   - Fall back to inline parser if `synod-parser` unavailable

5. **Save Round State**
   - Store responses as Markdown
   - Store parsed signals as JSON
   - Update status.json: `round_status[1] = "complete"`

**Timeout Handling:**
- First timeout: Retry with downgraded thinking/reasoning
- Second timeout: Fall back to alternative model
- Third timeout: Continue without model, note in synthesis

**SID Format Requirement:**
```xml
<confidence score="[0-100]">
  <evidence>[What supports this?]</evidence>
  <logic>[Reasoning soundness?]</logic>
  <expertise>[Domain confidence?]</expertise>
  <can_exit>[true if confidence ≥90 AND complete]</can_exit>
</confidence>

<semantic_focus>
1. [PRIMARY claim]
2. [SECONDARY claim]
3. [TERTIARY claim]
</semantic_focus>
```

**Early Exit Condition:**
- If all three agents have `can_exit: true` AND confidence ≥90
- Skip to Phase 4 (Synthesis)
- Announce: "조기 합의에 도달했습니다"

---

### Phase 2: Critic Round

**Objective:** Validate claims, calculate Trust Scores, identify contentions

**Process:**

1. **Claude Aggregation**
   - Identify agreement points (claimed by 2+ models)
   - Identify contentions (conflicting claims)
   - Spot weaknesses (unsupported claims, logical gaps)
   - Generate HISTORY_CONTEXT for external models

2. **Soft Defer Detection** (Free-MAD)
   - If any external model confidence < 50:
     - Insert anti-conformity hint in critic prompts
     - Instructs to maintain independent perspective
     - Prevents premature consensus

3. **Execute Gemini Critic**
   - Validate architectural claims
   - Assess evidence quality and trade-offs
   - Temperature: 0.5 (analytical)

4. **Execute OpenAI Critic**
   - Find counter-examples and logical flaws
   - Alternative interpretations
   - Temperature: 0.7 (exploratory)

5. **Calculate Trust Scores** (CortexDebate)
   ```
   T = min((C × R × I) / S, 2.0)

   where:
   C = Credibility (0-1): Evidence quality
   R = Reliability (0-1): Logical consistency
   I = Intimacy (0-1): Relevance to problem
   S = Self-Orientation (0.1-1): Bias detection
   ```

   **Thresholds:**
   - T ≥ 1.5: High trust (primary source)
   - T ≥ 1.0: Good trust
   - T ≥ 0.5: Acceptable trust
   - T < 0.5: Low trust (consider excluding)

6. **Save Critic State**
   - `aggregation.md`: Summary of prior round
   - `gemini-critique.md`: Architectural validation
   - `openai-critique.md`: Counter-examples and flaws
   - `trust-scores.json`: All scores and ratings
   - `contentions.json`: Disputed points

---

### Phase 3: Defense Round (Court Model)

**Objective:** Structured adversarial debate to resolve contentions

**Roles:**
- **Judge (Claude)**: Neutral arbiter analyzing both arguments
- **Defense (Gemini)**: Defends strongest solution
- **Prosecution (OpenAI)**: Attacks with alternatives

**Process:**

1. **Identify Defense Target**
   - Select solution with highest Trust Score
   - This becomes the "defendant"

2. **Craft Defense Prompt (Gemini)**
   - Argument: Strengthen weak points with evidence
   - Refute criticisms raised by prosecutor
   - Explain why alternatives fail
   - Anti-conformity instruction: Only concede genuinely indefensible points

3. **Craft Prosecution Prompt (OpenAI)**
   - Identify fatal flaws in defended solution
   - Present evidence for failure scenarios
   - Propose superior alternatives
   - Anti-conformity instruction: Attack vigorously, don't just agree

4. **Claude Judge Deliberation**
   - Evaluate defense strength
   - Evaluate prosecution strength
   - Make preliminary ruling
   - Assess which side has stronger case

5. **Save Defense State**
   - `judge-deliberation.md`: Analysis of arguments
   - `defense-args.md`: Strongest defense points
   - `prosecution-args.md`: Strongest attacks
   - `preliminary-ruling.md`: Judge's decision

---

### Phase 4: Synthesis

**Objective:** Produce final, actionable output with confidence weighting

**Process:**

1. **Compile Evidence**
   - Validated claims from Critic round
   - Trust scores for all solutions
   - Defense/Prosecution arguments
   - Judge's preliminary ruling

2. **Calculate Final Confidence**
   ```
   FC = (T_claude × C_claude + T_gemini × C_gemini + T_openai × C_openai)
        ─────────────────────────────────────────────────────────
        (T_claude + T_gemini + T_openai)

   where T = Trust Score, C = Confidence Score
   ```

3. **Generate Mode-Specific Output**
   - **review**: Issues by severity + fixes
   - **design**: Chosen architecture + trade-offs
   - **debug**: Root cause + fix + prevention
   - **idea**: Ranked ideas + pros/cons
   - **general**: Balanced comprehensive answer

4. **Include Deliberation Transparency**
   - Model contributions (key points from each)
   - Resolved contentions (how disputes settled)
   - Trust scores (with ratings)
   - Confidence percentage

5. **Save Final State**
   - `round-4-synthesis.md`: Final output
   - Update `status.json`:
     - `status: "complete"`
     - `final_confidence: {FC}`
     - `completed_at: {ISO_TIMESTAMP}`

---

## Core Algorithms

### 1. Trust Score Calculation (CortexDebate)

**Formula:** `T = min((C × R × I) / S, 2.0)`

**Components:**

#### Credibility (C): Evidence Quality
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Cites specific code, docs, or proven patterns |
| 0.7-0.8 | References general knowledge |
| 0.5-0.6 | Claims without evidence |
| 0.3-0.4 | Contradicts known facts |
| 0.0-0.2 | Fabricates evidence |

#### Reliability (R): Logical Consistency
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Coherent reasoning, no contradictions |
| 0.7-0.8 | Minor logical gaps |
| 0.5-0.6 | Some non-sequiturs |
| 0.3-0.4 | Major logical flaws |
| 0.0-0.2 | Incoherent |

#### Intimacy (I): Relevance to Problem
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Directly addresses exact problem |
| 0.7-0.8 | Mostly relevant with minor tangents |
| 0.5-0.6 | Partially relevant |
| 0.3-0.4 | Mostly off-topic |
| 0.0-0.2 | Completely irrelevant |

#### Self-Orientation (S): Bias Detection
| Score | Criteria |
|-------|----------|
| 0.1-0.2 | Neutral, balanced perspective |
| 0.3-0.4 | Slight preference |
| 0.5-0.6 | Noticeable bias |
| 0.7-0.8 | Strong bias |
| 0.9-1.0 | Completely one-sided |

**Capping Mechanism:**
- Denominator S ranges 0.1-1.0
- Numerator C×R×I ranges 0-1
- Raw formula can yield 0-10
- Capped at 2.0 to prevent unbounded scores
- Higher neutrality (lower S) → higher trust (up to cap)

**Example:**
```
Perfect evidence (C=1.0), perfect reasoning (R=1.0),
perfect relevance (I=1.0), neutral perspective (S=0.1):
T = min((1.0 × 1.0 × 1.0) / 0.1, 2.0) = min(10, 2.0) = 2.0

Same solution with bias (S=0.5):
T = min((1.0 × 1.0 × 1.0) / 0.5, 2.0) = min(2.0, 2.0) = 2.0

With poor evidence (C=0.7), perfect other factors, neutral (S=0.1):
T = min((0.7 × 1.0 × 1.0) / 0.1, 2.0) = min(7.0, 2.0) = 2.0
```

---

### 2. Free-MAD (Majority Aversion Debate)

**Principle:** Prevent premature consensus through anti-conformity instructions

**Implementation:**

1. **Soft Defer Detection**
   - After Solver round, check external model confidence
   - If Gemini < 50 OR OpenAI < 50:
     - Flag as "low confidence" situation

2. **Anti-Conformity Hints**
   - Insert into Critic and Defense prompts:
     ```
     Some agents expressed low confidence in the previous round.
     This often indicates genuine uncertainty or novel insights.
     Do NOT rush to consensus - maintain your unique analytical perspective.
     If you disagree with other agents, articulate WHY with evidence.
     ```

3. **Claude Aggregation**
   - Claude explicitly identifies contentions
   - Does NOT try to find agreement where it doesn't exist
   - Passes contentions to subsequent rounds

4. **Defense Enforcement**
   - Defense prompt: "Only concede points that are GENUINELY indefensible"
   - Prosecution prompt: "Attack vigorously and propose alternatives"
   - Both sides instructed against groupthink

---

### 3. SID (Self-Signals Driven) Confidence

**Components:**

1. **Confidence Score (0-100)**
   - Agent's assessment of answer quality
   - Scale: 0-50 (low/uncertain), 50-80 (moderate), 80-100 (high/certain)
   - Used in final confidence calculation

2. **Semantic Focus (3-point hierarchy)**
   - Primary claim: Most important assertion
   - Secondary claim: Supporting argument
   - Tertiary claim: Additional consideration
   - Enables targeted debate in subsequent rounds

3. **Can Exit Flag (boolean)**
   - True if: confidence ≥ 90 AND solution complete AND no ambiguity
   - Used for early exit detection
   - Claude aggregates: early exit if ALL true

**Parsing Logic:**
- Extract from XML blocks (primary method)
- Fallback to inline parser if external tool unavailable
- Apply defaults if XML missing (C=50, can_exit=false)

---

### 4. Mode-Specific Configuration

Each mode has different model selections, thinking levels, and round counts:

| Mode | Gemini | Thinking | OpenAI | Reasoning | Rounds |
|------|--------|----------|--------|-----------|--------|
| **review** | flash | high | o3 | medium | 3 |
| **design** | pro | high | o3 | high | 4 |
| **debug** | flash | high | o3 | high | 3 |
| **idea** | pro | high | gpt4o | - | 4 |
| **general** | flash | medium | gpt4o | - | 3 |

**Rationale:**
- **Flash vs. Pro**: Pro for creative tasks (design/idea), flash for analytical (review/debug)
- **Thinking Level**: High for modes requiring reasoning, medium for general
- **o3 for complex reasoning**: Design/debug need deep analysis; gpt4o for creative/general
- **Rounds**: Design/idea add exploration round; review/debug/general use 3-round core

---

## Directory Structure

### Root Structure
```
synod-plugin/
├── AGENTS.md                    # This file - architecture documentation
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Version history
├── SECURITY.md                  # Security policies
├── LICENSE                      # MIT license
├── README.md                    # User-facing documentation
├── plugin.json                  # Plugin metadata and configuration
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── skills/                      # Claude Code skill definitions
│   ├── synod.md                # Main /synod command (detailed instruction set)
│   └── cancel-synod.md         # /cancel-synod command
├── tools/                       # CLI integration tools
│   ├── synod-parser.py         # SID signal extraction & parsing
│   ├── gemini-3.py             # Gemini API integration
│   └── openai-cli.py           # OpenAI API integration
├── benchmark/                   # Performance evaluation suite
│   ├── README.md               # Benchmark documentation
│   ├── config.yaml             # Benchmark configuration
│   ├── requirements.txt        # Benchmark dependencies
│   ├── __init__.py             # Package initialization
│   ├── run_gsm8k.py            # GSM8K benchmark runner
│   ├── analyze.py              # Results analysis tools
│   ├── evaluator.py            # Evaluation harness
│   ├── baselines.py            # Baseline implementations
│   ├── data/                   # Dataset cache
│   ├── results/                # Output directory
│   └── scripts/                # Utility scripts
├── docs/                        # Documentation (planned)
└── examples/                    # Example usage & demos (planned)
```

### Session Directory Structure
```
~/.synod/sessions/
└── synod-YYYYMMDD-HHMMSS-{hex3}/    # Session directory
    ├── meta.json                    # Session metadata
    │   ├── session_id
    │   ├── created_at
    │   ├── mode
    │   ├── problem_type
    │   ├── complexity
    │   ├── problem_summary
    │   ├── model_config (Gemini & OpenAI models/thinking)
    │   └── total_rounds
    ├── status.json                  # Progress tracking
    │   ├── current_round
    │   ├── round_status (0-4)
    │   ├── resume_point
    │   ├── can_resume
    │   ├── status (in_progress|complete|cancelled)
    │   ├── final_confidence (if complete)
    │   └── completed_at (if complete)
    ├── round-1-solver/
    │   ├── claude-response.md
    │   ├── gemini-response.md
    │   ├── openai-response.md
    │   ├── claude-parsed.json
    │   ├── gemini-parsed.json
    │   └── openai-parsed.json
    ├── round-2-critic/
    │   ├── aggregation.md
    │   ├── gemini-critique.md
    │   ├── openai-critique.md
    │   ├── trust-scores.json
    │   └── contentions.json
    ├── round-3-defense/
    │   ├── judge-deliberation.md
    │   ├── defense-args.md
    │   ├── prosecution-args.md
    │   └── preliminary-ruling.md
    └── round-4-synthesis.md         # Final output
```

### File Locations for Agents

**When working in this project, find:**
- **Skill implementation**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/skills/synod.md`
- **Cancel skill**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/skills/cancel-synod.md`
- **Parser tool**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/synod-parser.py`
- **Configuration**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/plugin.json`
- **Python config**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/pyproject.toml`
- **Benchmarks**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/benchmark/`
- **Documentation**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/README.md`
- **This file**: `/Users/ahnjundaram_g/dev/tools/synod-plugin/AGENTS.md`

---

## Tool Ecosystem

### 1. synod-parser.py

**Purpose:** Extract and parse SID signals from model responses

**Location:** `/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/synod-parser.py`

**Interface:**
```bash
# Full parse
echo "response" | synod-parser
synod-parser "response string"

# Validation only
synod-parser --validate "response"

# Trust score calculation
synod-parser --trust 0.9 0.8 0.85 0.2
```

**Output Format:**
```json
{
  "confidence": {
    "score": 85,
    "evidence": "...",
    "logic": "...",
    "expertise": "...",
    "can_exit": true
  },
  "semantic_focus": ["Primary point", "Secondary point", "Tertiary point"],
  "validation": {
    "has_confidence": true,
    "has_score": true,
    "has_semantic_focus": true,
    "is_valid": true
  },
  "can_exit_early": true,
  "high_confidence": true
}
```

**Functions:**
- `validate_format(text)`: Check XML structure
- `extract_confidence(text)`: Parse confidence block
- `extract_semantic_focus(text)`: Parse focus points
- `extract_key_sentences(text)`: Fallback if focus missing
- `calculate_trust_score(c, r, i, s)`: CortexDebate formula
- `apply_defaults(text)`: Default values for malformed responses
- `parse_response(text)`: Full parsing pipeline

**Error Handling:**
- Missing XML blocks → Apply defaults, mark with `format_warning`
- Invalid trust scores → Clamp to valid ranges (0-1)
- Malformed JSON → Return with validation details

---

### 2. gemini-3.py

**Purpose:** Google Gemini integration with adaptive thinking

**Location:** `/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/gemini-3.py`

**Interface:**
```bash
gemini-3 --model flash|pro \
         --thinking low|medium|high \
         --temperature 0.0-2.0 \
         < prompt.txt
```

**Capabilities:**
- Model selection: flash (fast), pro (advanced reasoning)
- Adaptive thinking: Toggle depth of analysis
- Temperature control: Creativity vs. precision
- Timeout handling: 110-second deadline with graceful fallback
- Retry logic: Automatic downgrade on timeout

**Error Handling:**
- API timeout → Retry with downgraded thinking
- Rate limit → Exponential backoff
- Auth error → Exit with clear message
- Format error → Return raw response with warning

---

### 3. openai-cli.py

**Purpose:** OpenAI API integration with reasoning support

**Location:** `/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/openai-cli.py`

**Interface:**
```bash
openai-cli --model gpt4o|o3|o3-mini \
           --reasoning low|medium|high \
           --temperature 0.0-2.0 \
           < prompt.txt
```

**Capabilities:**
- Model selection: gpt4o (fast), o3 (deep reasoning)
- Reasoning levels: Controls inference effort
- Temperature control: gpt4o only (o3 fixed at 1.0)
- Timeout handling: 110-second deadline
- Graceful fallback: Automatic model downgrade

**Critical Constraints:**
- **o3 temperature**: Fixed at 1.0 (no adjustment possible)
- **o3 reasoning**: Parameter affects computational budget, not temperature
- **gpt4o**: Standard temperature control supported

**Error Handling:**
- o3 API timeout → Fall back to gpt4o
- Temperature adjustment on o3 → Warning, proceed with fixed temp
- Reasoning parameter unsupported → Use defaults
- API errors → Structured retry with exponential backoff

---

## Session Management

### Session Lifecycle

```
Creation:
  ├─ Generate session ID: synod-YYYYMMDD-HHMMSS-{random}
  ├─ Create directory structure
  ├─ Write meta.json (immutable config)
  └─ Write status.json (mutable progress)

Execution:
  ├─ Phase 0 → status.json: round_status[0] = "complete"
  ├─ Phase 1 → status.json: round_status[1] = "complete"
  ├─ Phase 2 → status.json: round_status[2] = "complete"
  ├─ Phase 3 → status.json: round_status[3] = "complete"
  └─ Phase 4 → status.json: round_status[4] = "complete"

Completion:
  └─ Update status.json:
     ├─ status: "complete"
     ├─ final_confidence: {score}
     └─ completed_at: {ISO_TIMESTAMP}

Resume:
  ├─ Read latest session or specified session_id
  ├─ Check status.json: can_resume flag
  ├─ Load all completed round data
  └─ Continue from resume_point

Cancellation:
  └─ Update status.json:
     ├─ status: "cancelled"
     ├─ cancelled_at: {ISO_TIMESTAMP}
     └─ Preserve all partial results
```

### Resume Protocol

**Trigger:** `/synod resume` or `/synod resume {session-id}`

**Process:**
1. Find latest session (if no ID specified)
2. Read `status.json` to determine progress
3. Load all completed round data
4. Continue from next incomplete phase
5. Announce: `[Synod] {SESSION_ID} 세션을 단계 {N}부터 재개합니다`

**Resume Points:**
- Phase 0 incomplete → Re-run classification
- Phase 1 incomplete → Re-run solver (may have partial responses)
- Phase 2 incomplete → Re-run critic
- Phase 3 incomplete → Re-run defense
- Phase 4 incomplete → Re-run synthesis
- Session complete → Display existing results

---

### State Persistence

**Session Retention:**
- Default: Indefinite (preserved for debugging and audits)
- Configurable: Set `SYNOD_RETENTION_DAYS` to auto-clean
- Manual cleanup: Find sessions older than N days

**State Format:**
- `meta.json`: JSON (immutable after creation)
- `status.json`: JSON (updated after each phase)
- Responses: Markdown (human-readable + preservation)
- Parsed signals: JSON (machine-readable for analysis)

**Context Loading (Resume):**
- Load meta.json to re-establish configuration
- Load round outputs to rebuild context
- Load parsed signals to continue debate
- Load trust scores to inform synthesis

---

## Mode-Specific Configurations

### review Mode

**Purpose:** Code review and analysis
**Gemini Model:** flash
**OpenAI Model:** o3 (medium reasoning)
**Rounds:** 3
**Temperature:** 0.7 (Gemini), 1.0 (o3)

**Agent Focus:**
- **Claude**: Correctness, best practices, maintainability
- **Gemini**: Code organization, architectural patterns
- **OpenAI**: Edge cases, error handling, security

**Output Structure:**
```markdown
## 코드 리뷰 결과

### 발견된 문제
- **[ERROR]** {critical issue}
- **[WARNING]** {moderate issue}
- **[INFO]** {suggestion}

### 권장 사항
{prioritized fixes}

### 신뢰도: {FINAL_CONFIDENCE}%
```

---

### design Mode

**Purpose:** Architecture and system design
**Gemini Model:** pro
**OpenAI Model:** o3 (high reasoning)
**Rounds:** 4 (extra exploration round)
**Temperature:** 0.7 (Gemini), 1.0 (o3)

**Agent Focus:**
- **Claude**: System integration, API design
- **Gemini**: Scalability, patterns, trade-offs
- **OpenAI**: Failure modes, alternatives, constraints

**Output Structure:**
```markdown
## 아키텍처 결정

### 권장 접근법
{chosen architecture description}

### 트레이드오프
| Aspect | Chosen | Alternative | Rationale |

### 구현 단계
1. {step}
2. {step}
```

---

### debug Mode

**Purpose:** Debugging and troubleshooting
**Gemini Model:** flash
**OpenAI Model:** o3 (high reasoning)
**Rounds:** 3
**Temperature:** 0.7 (Gemini), 1.0 (o3)

**Agent Focus:**
- **Claude**: Symptom analysis, hypothesis validation
- **Gemini**: System-level causes, pattern recognition
- **OpenAI**: Counter-hypotheses, edge cases

**Output Structure:**
```markdown
## 디버그 분석

### 근본 원인
{identified cause with evidence}

### 증거 체인
1. {symptom} → {cause}
2. {trace} → {conclusion}

### 권장 수정
{code or steps to fix}

### 예방책
{prevention in future}
```

---

### idea Mode

**Purpose:** Brainstorming and ideation
**Gemini Model:** pro
**OpenAI Model:** gpt4o (no reasoning)
**Rounds:** 4 (extra exploration round)
**Temperature:** 0.7 (both models)

**Agent Focus:**
- **Claude**: Feasibility, implementation effort
- **Gemini**: Creative exploration, novel approaches
- **OpenAI**: Risk assessment, market fit

**Output Structure:**
```markdown
## 아이디어 평가

### 순위별 아이디어

#### 1. {Top Idea}
**장점:** {list}
**단점:** {list}
**실현 가능성:** {rating}

#### 2. {Second Idea}
...

### 권장 사항
{which to pursue and why}
```

---

### general Mode

**Purpose:** General questions and balanced discussion
**Gemini Model:** flash
**OpenAI Model:** gpt4o (no reasoning)
**Rounds:** 3
**Temperature:** 0.7 (both models)

**Agent Focus:**
- **Claude**: Accuracy, completeness
- **Gemini**: Broad coverage, connections
- **OpenAI**: Alternative perspectives, nuances

**Output Structure:**
```markdown
## 답변

{comprehensive response}

### 핵심 포인트
- {point 1}
- {point 2}
- {point 3}

### 고려 사항
{nuances and caveats}
```

---

## Error Handling and Fallbacks

### Timeout Fallback Chain

**Gemini Timeout (>110s):**
1. Retry: `gemini-3 --model flash --thinking medium` (downgrade)
2. Retry: `gemini-3 --model flash --thinking low`
3. Final: Continue without Gemini, note in synthesis

**OpenAI Timeout (>110s):**
1. Retry: `openai-cli --model o3 --reasoning medium` (downgrade)
2. Retry: `openai-cli --model gpt4o` (fallback model)
3. Final: Continue without OpenAI, note in synthesis

**Both Models Timeout:**
- Activate low-trust fallback
- Use Claude solo reasoning
- Cap final_confidence at 60%
- Include warning in output

---

### Format Enforcement Protocol

**If SID format missing:**
1. Send re-prompt requesting XML blocks
2. Max 2 retries per model per round
3. If still malformed: Apply defaults via parser
   - confidence: 50
   - can_exit: false
   - semantic_focus: extracted key sentences

**Default Response Template:**
```json
{
  "confidence": {
    "score": 50,
    "evidence": null,
    "logic": null,
    "expertise": null,
    "can_exit": false
  },
  "semantic_focus": ["extracted", "key", "sentences"],
  "format_warning": "Model did not comply with SID format"
}
```

---

### Low Trust Score Fallback

**If ALL models Trust Score < 0.5:**
1. Do NOT exclude all agents
2. Keep agent with highest score
3. Add warning: `[낮은 신뢰도 상황]`
4. Cap final_confidence at 60%
5. Recommend user review carefully

---

### API Error Handling

**Rate Limit (429):**
- Wait 30 seconds
- Retry with same parameters
- Max 3 retries

**Auth Error (401):**
- Report: `API key invalid or expired`
- Terminate gracefully
- Cannot retry

**Network Error (timeout, connection reset):**
- Activate timeout fallback chain
- Preserve state for resume

**Other API Errors:**
- Log error details
- Continue with available models
- Note in synthesis

---

## Development Guidelines

### Code Organization

**Python Tools:**
- Location: `/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/`
- Make executable: `chmod +x tools/*.py`
- Add to PATH: `export PATH="$PATH:$(pwd)/tools"`

**Skills (Markdown):**
- Location: `/Users/ahnjundaram_g/dev/tools/synod-plugin/skills/`
- Frontmatter: description, argument-hint, allowed-tools
- Commands must be shell-executable

**Configuration:**
- Plugin config: `plugin.json`
- Python config: `pyproject.toml`
- Environment: API keys and session directory

---

### Adding New Features

**New Skill:**
1. Create `skills/{skill-name}.md`
2. Add to `plugin.json` skills array
3. Document usage in skill file
4. Update README.md

**New Tool:**
1. Create `tools/{tool-name}.py`
2. Make executable and POSIX-compliant
3. Add to `plugin.json` tools array
4. Document CLI interface

**New Mode:**
1. Add to MODE_CONFIG in synod.md
2. Define model selections and round count
3. Specify agent focus areas
4. Add output template to Synthesis section

**Database or Persistence:**
1. Store in `~/.synod/` (user-local)
2. Or in session directory (session-specific)
3. Use JSON for portability
4. Document schema in AGENTS.md

---

### Testing

**Unit Tests:**
- Location: `tests/` (per pyproject.toml)
- Command: `pytest tests/`
- Coverage: `pytest --cov=tools`

**Integration Tests:**
- Test /synod command with sample prompts
- Verify session state creation
- Test resume capability
- Verify output formats

**Benchmark Tests:**
- Location: `benchmark/`
- Command: `python benchmark/run_gsm8k.py`
- Validates Synod vs. baselines

---

### Code Style

**Python:**
- Target: Python 3.9+
- Linter: ruff
- Type checking: mypy
- Line length: 100 characters

**Configuration:**
```toml
[tool.ruff]
target-version = "py39"
line-length = 100
select = ["E", "W", "F", "I", "B", "C4", "UP"]
```

**Markdown (Skills & Docs):**
- H1 for section titles
- H2 for subsections
- Code blocks with language specifier
- Links for references
- Tables for structured data

---

### Documentation Standards

**Docstrings (Python):**
```python
def function_name(param1: str, param2: int) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        param1: Description
        param2: Description

    Returns:
        Description of return value

    Raises:
        ValueError: When this occurs
    """
```

**CLI Tool Help:**
- Usage examples at top
- Argument descriptions
- Output format documentation
- Error message examples

**Skill Documentation:**
- Purpose and use case
- Argument syntax and examples
- Expected output format
- Error handling

---

### Commit Message Conventions

**Format:** `{type}: {subject}`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code reorganization
- `perf`: Performance improvement
- `test`: Test additions/fixes
- `docs`: Documentation updates
- `chore`: Build, dependencies, configuration

**Examples:**
```
feat: Add TruthfulQA benchmark support
fix: Handle o3 temperature constraint correctly
refactor: Extract parser into separate module
docs: Document Free-MAD anti-conformity protocol
```

---

## Integration Points

### Claude Code Integration

**Skill Entry Points:**
- `/synod [mode] <prompt>` → Executes main deliberation
- `/cancel-synod` → Cancels active session

**Allowed Tools in Skills:**
- Read: Access files for context
- Write: Save responses and state
- Bash: Execute CLI tools
- Glob: Pattern matching
- Grep: Content search
- Task: Multi-agent delegation

---

### External APIs

**Gemini (google-genai)**
- Models: `gemini-2.0-flash`, `gemini-2.0-pro`
- Authentication: `GEMINI_API_KEY`
- Timeout: 110 seconds
- Features: Thinking, temperature, streaming

**OpenAI (openai)**
- Models: `gpt-4o`, `o3`, `o3-mini`
- Authentication: `OPENAI_API_KEY`
- Timeout: 110 seconds
- Features: Reasoning (o3 only), temperature (gpt4o only)

**Claude (anthropic)**
- Internal to Claude Code
- No separate API call needed
- Uses built-in Claude 3.5 Sonnet

---

### Configuration Management

**Environment Variables:**
```bash
export GEMINI_API_KEY="..."         # Required
export OPENAI_API_KEY="..."         # Required
export SYNOD_SESSION_DIR="~/.synod" # Optional
```

**Plugin Configuration (plugin.json):**
- Model versions
- API endpoints
- Dependency specifications
- Claude Code minimum version

**Python Configuration (pyproject.toml):**
- Package metadata
- Dependencies (production + dev)
- Tool configurations (ruff, mypy, pytest)
- Test settings

---

### Benchmark Integration

**Suite Location:** `/Users/ahnjundaram_g/dev/tools/synod-plugin/benchmark/`

**Components:**
- **run_gsm8k.py**: Main benchmark runner
- **evaluator.py**: Evaluation harness
- **baselines.py**: Baseline implementations
- **analyze.py**: Results analysis
- **config.yaml**: Configuration

**Metrics:**
- Accuracy: % correct answers
- Confidence: Average model certainty
- Deliberation quality: Consensus vs. disagreement
- Cost: API usage expenses

**Success Criteria (Phase 1):**
- Synod accuracy > max(single-model baselines)
- Synod accuracy ≥ majority vote baseline
- Cost per question < $0.50

---

## Support and Troubleshooting

### Common Issues

**Missing API Key:**
```bash
echo $GEMINI_API_KEY  # Should print key
echo $OPENAI_API_KEY  # Should print key
```

**Session Directory Permission Error:**
```bash
mkdir -p ~/.synod/sessions
chmod 700 ~/.synod  # User-only access
```

**Tool Not Found:**
```bash
which synod-parser.py  # Should show path
export PATH="$PATH:$(pwd)/tools"
chmod +x tools/*.py
```

**Model Timeout:**
- Check network connectivity
- Verify API service status
- Check rate limits
- Increase timeout if needed

---

### Getting Help

**GitHub Issues:** https://github.com/quantsquirrel/claude-synod-debate/issues
**GitHub Discussions:** https://github.com/quantsquirrel/claude-synod-debate/discussions
**Local Testing:** Run benchmark suite for validation

---

## Summary

Synod v3.0 is a sophisticated multi-agent system that:

1. **Orchestrates expertise** from three LLM models with distinct personas
2. **Structures debate** through phases that build knowledge progressively
3. **Quantifies trust** using evidence-based scoring (CortexDebate formula)
4. **Prevents groupthink** through anti-conformity instructions (Free-MAD)
5. **Enables transparency** by tracking all deliberation steps
6. **Supports resumption** by preserving complete session state

The system is extensible, well-documented, and production-ready for integration with Claude Code as a sophisticated decision-making tool.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-31
**Status:** Complete and verified
