# Synod Module: Phase 2 - Critic Round

**Inputs:**
- `${SESSION_DIR}/round-1-solver/` - All Solver responses
- `PROBLEM` - Original problem statement
- `GEMINI_CLI`, `OPENAI_CLI` - CLI executable paths
- `SYNOD_PARSER_CLI` - Parser executable path

**Outputs:**
- `${SESSION_DIR}/round-2-critic/aggregation.md`
- `${SESSION_DIR}/round-2-critic/gemini-critique.md`
- `${SESSION_DIR}/round-2-critic/openai-critique.md`
- `${SESSION_DIR}/round-2-critic/trust-scores.json`
- `${SESSION_DIR}/round-2-critic/contentions.json`
- Updated `status.json` with round 2 complete

**Cross-references:**
- Called after Phase 1 (`synod-phase1-solver.md`)
- Outputs consumed by Phase 3 (`synod-phase3-defense.md`)
- Timeout failures trigger `synod-error-handling.md`

---

```bash
# Emit phase start (v2.1)
synod_progress '{"event":"phase_start","phase":2,"name":"Critic Round"}'
```

## Step 2.1: Claude Aggregation

As the orchestrator, analyze all three Solver responses:

1. **Identify Agreement Points** - Claims supported by 2+ models
2. **Identify Contentions** - Conflicting claims or approaches
3. **Spot Weaknesses** - Unsupported claims, logical gaps, missing considerations

Create a compressed summary (HISTORY_CONTEXT) for external models:
```
## Prior Round

| Agent | Conf | Key Claim |
|-------|------|-----------|
| Claude | {X} | {핵심 주장 1문장, 30단어 이하} |
| Gemini | {Y} | {핵심 주장 1문장, 30단어 이하} |
| OpenAI | {Z} | {핵심 주장 1문장, 30단어 이하} |

**Contentions**: {1-2문장으로 핵심 쟁점만, 최대 2개}
```

## Step 2.1b: Low Confidence Soft Defer Check

Round 1에서 추출한 confidence 점수를 분석:

```bash
CLAUDE_CONF=$(jq -r '.confidence.score // 50' "${SESSION_DIR}/round-1-solver/claude-parsed.json")
GEMINI_CONF=$(jq -r '.confidence.score // 50' "${SESSION_DIR}/round-1-solver/gemini-parsed.json")
OPENAI_CONF=$(jq -r '.confidence.score // 50' "${SESSION_DIR}/round-1-solver/openai-parsed.json")

# Load low confidence threshold from config (v2.1)
LOW_CONF_THRESHOLD=$(python3 "${TOOLS_DIR}/synod_config.py" thresholds low_confidence 2>/dev/null || echo "50")

# Generate soft defer hints
SOFT_DEFER_HINT=""
if [[ $GEMINI_CONF -lt $LOW_CONF_THRESHOLD ]] || [[ $OPENAI_CONF -lt $LOW_CONF_THRESHOLD ]]; then
  SOFT_DEFER_HINT="
## IMPORTANT: Preserve Unique Perspectives
Some agents expressed low confidence (score < 50) in the previous round.
This often indicates genuine uncertainty or novel insights.
Do NOT rush to consensus - maintain your unique analytical perspective.
If you disagree with other agents, articulate WHY with evidence.
"
fi
```

**Claude Confidence 제외 근거**:
- Claude는 orchestrator 역할로서 전체 세션을 조율함
- Claude의 low confidence는 조기 종료 조건(can_exit)에서만 사용됨
- Soft defer 힌트는 외부 모델(Gemini/OpenAI)이 합의를 서두르지 않도록 하는 목적
- Claude 자신은 프롬프트를 받는 대상이 아니므로 힌트 삽입 대상이 아님

## Step 2.2: Gemini Critic Execution

Write to `${TEMP_DIR}/gemini-critic-prompt.txt`:

```
You are a CRITIC in a multi-agent deliberation council (Synod).

{SOFT_DEFER_HINT}

## Your Task
Validate claims from the Solver round. Focus on:
- Are claims backed by evidence?
- Are there logical errors?
- What's missing?

## Prior Round Context
{HISTORY_CONTEXT}

## Original Problem
{PROBLEM}

## REQUIRED Output Format

<critique>
### Validated Claims (with evidence)
{list claims that are well-supported}

### Disputed Claims (with reasons)
{list claims that lack evidence or have issues}

### Missing Considerations
{what did solvers overlook?}
</critique>

<confidence score="[0-100]">
  <evidence>[Evidence quality of your critique]</evidence>
  <logic>[Soundness of your analysis]</logic>
  <expertise>[Your domain confidence]</expertise>
  <can_exit>[true if debate should end]</can_exit>
</confidence>

<semantic_focus>
1. [Most important critique point]
2. [Secondary critique]
3. [Tertiary critique]
</semantic_focus>
```

Execute:
```bash
# Gemini Critic execution (medium thinking for analytical evaluation)
synod_progress '{"event":"model_start","model":"gemini"}'
$GEMINI_CLI --model {GEMINI_MODEL} --thinking {GEMINI_THINKING} --timeout ${MODEL_TIMEOUT:-110} < "${TEMP_DIR}/gemini-critic-prompt.txt" > "${TEMP_DIR}/gemini-critique.txt" 2>&1 &
```

## Step 2.3: OpenAI Critic Execution

Write to `${TEMP_DIR}/openai-critic-prompt.txt`:

```
You are a LOGIC CHECKER in a multi-agent deliberation council (Synod).

{SOFT_DEFER_HINT}

## Your Task
Find counter-examples and logical flaws. Focus on:
- Edge cases that break proposed solutions
- Assumptions that might be wrong
- Alternative interpretations

## Prior Round Context
{HISTORY_CONTEXT}

## Original Problem
{PROBLEM}

## REQUIRED Output Format

<critique>
### Counter-Examples Found
{specific cases that challenge solutions}

### Logical Flaws Detected
{invalid reasoning, false premises}

### Alternative Interpretations
{different ways to view the problem}
</critique>

<confidence score="[0-100]">
  <evidence>[Evidence for your counter-examples]</evidence>
  <logic>[Soundness of your logical analysis]</logic>
  <expertise>[Your domain confidence]</expertise>
  <can_exit>[true if no major issues found]</can_exit>
</confidence>

<semantic_focus>
1. [Most critical counter-example or flaw]
2. [Secondary issue]
3. [Tertiary issue]
</semantic_focus>
```

## Step 2.4: Calculate Trust Scores

For each model's Solver response, calculate Trust Score using this rubric:

### C (Credibility) - Evidence Quality
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Cites specific code, docs, or proven patterns; claims are verifiable |
| 0.7-0.8 | References general knowledge; claims are reasonable but not cited |
| 0.5-0.6 | Makes claims without evidence; relies on "usually" or "typically" |
| 0.3-0.4 | Vague claims; contradicts known facts |
| 0.0-0.2 | Fabricates evidence; demonstrably false statements |

### R (Reliability) - Logical Consistency
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Arguments follow logically; no contradictions; conclusions match premises |
| 0.7-0.8 | Minor logical gaps; mostly coherent reasoning |
| 0.5-0.6 | Some non-sequiturs; conclusions partially supported |
| 0.3-0.4 | Major logical flaws; contradicts own statements |
| 0.0-0.2 | Incoherent reasoning; contradictory conclusions |

### I (Intimacy) - Relevance to Problem
| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Directly addresses the exact problem; solution is immediately applicable |
| 0.7-0.8 | Addresses problem with minor tangents; mostly relevant |
| 0.5-0.6 | Partially relevant; includes significant off-topic content |
| 0.3-0.4 | Mostly off-topic; addresses different problem |
| 0.0-0.2 | Completely irrelevant response |

### S (Self-Orientation) - Bias/Agenda Detection
| Score | Criteria |
|-------|----------|
| 0.1-0.2 | Neutral, balanced perspective; acknowledges limitations and alternatives |
| 0.3-0.4 | Slight preference for own approach but considers others |
| 0.5-0.6 | Noticeable bias; dismisses alternatives without justification |
| 0.7-0.8 | Strong bias; ignores contradicting evidence |
| 0.9-1.0 | Completely one-sided; refuses to consider alternatives |

**v2.1:** Trust cap loaded from config: `python3 "${TOOLS_DIR}/synod_config.py" thresholds trust_cap`

**Trust Calculation:** `T = min((C x R x I) / S, TRUST_CAP)`

The formula is capped at 2.0 to prevent unbounded scores when Self-Orientation (S) is very low:
- S = 0.1 (most neutral) with perfect C/R/I → T = min(10.0, 2.0) = 2.0
- S = 0.5 (moderate bias) with perfect C/R/I → T = min(2.0, 2.0) = 2.0
- S = 1.0 (extreme bias) with perfect C/R/I → T = min(1.0, 2.0) = 1.0

```bash
$SYNOD_PARSER_CLI --trust {C} {R} {I} {S}  # Parser handles capping internally
```

**Thresholds:**
- T < 0.5 = Exclude from synthesis (unless all are low - see `synod-error-handling.md`)
- T >= 1.5 = High trust (consider as primary source)
- T >= 1.0 = Good trust
- T >= 0.5 = Acceptable trust

## Step 2.5: Save Critic Round State

Save to `${SESSION_DIR}/round-2-critic/`:
- `aggregation.md` - Claude's aggregation and summary
- `gemini-critique.md` - Gemini's critique
- `openai-critique.md` - OpenAI's critique
- `trust-scores.json` - All Trust Score calculations
- `contentions.json` - List of disputed points

Update status.json to round 2 complete.

```bash
# Emit model completions and phase end (v2.1)
synod_progress '{"event":"model_complete","model":"gemini"}'
synod_progress '{"event":"model_complete","model":"openai"}'
synod_progress '{"event":"phase_end","phase":2}'
```

**Next Phase:** Proceed to Phase 3 (see `synod-phase3-defense.md`)
