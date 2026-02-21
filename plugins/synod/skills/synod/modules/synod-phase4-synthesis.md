# Synod Module: Phase 4 - Synthesis

**Inputs:**
- All previous round outputs from `${SESSION_DIR}/`
- `trust-scores.json` - Trust scores from Phase 2
- `preliminary-ruling.md` - Judge's ruling from Phase 3
- `MODE` - Deliberation mode

**Outputs:**
- `${SESSION_DIR}/round-4-synthesis.md` - Final output
- Updated `status.json` with session complete

**Cross-references:**
- Called after Phase 3 (`synod-phase3-defense.md`) or Phase 1 (early exit)
- Final phase - no further processing

---

## Pre-condition: Verify Phase 1 Outputs Exist

> **⛔ MANDATORY CHECK — Synthesis MUST NOT run without real external model responses.**

```bash
# Verify Phase 1 produced actual external model responses
PHASE1_DIR="${SESSION_DIR}/round-1-solver"
MISSING_RESPONSES=""

for MODEL_NAME in gemini openai claude; do
  if [[ ! -f "${PHASE1_DIR}/${MODEL_NAME}-response.md" ]] || \
     [[ ! -s "${PHASE1_DIR}/${MODEL_NAME}-response.md" ]]; then
    MISSING_RESPONSES="${MISSING_RESPONSES} ${MODEL_NAME}"
  fi
done

if [[ -n "$MISSING_RESPONSES" ]]; then
  echo "[FATAL] Phase 4 cannot proceed — Phase 1 responses missing:${MISSING_RESPONSES}" >&2
  echo "[FATAL] Go back to Phase 1 and execute actual CLI commands." >&2
  exit 1
fi
```

**If this check fails:** Return to Phase 1 (Step 1.2) and run the actual Bash commands. Do NOT generate synthesis from Claude-only analysis.

```bash
# Emit phase start (v2.1)
synod_progress '{"event":"phase_start","phase":4,"name":"Synthesis"}'
synod_progress '{"event":"model_start","model":"claude"}'
```

## Step 4.1: Compile Final Evidence

Gather from all rounds:
- Validated claims (from Critic round)
- Trust Scores (filter T < 0.5 unless all low - see `synod-error-handling.md`)
- Defense/Prosecution strongest arguments
- Judge's preliminary ruling

## Step 4.2: Calculate Final Confidence

Weighted average based on Trust Scores:
```
FINAL_CONFIDENCE = (T_claude * C_claude + T_gemini * C_gemini + T_openai * C_openai) / (T_claude + T_gemini + T_openai)
```

Where T = Trust Score, C = Confidence Score

## Step 4.3: Generate Mode-Specific Output

```bash
# Load output template from config (v2.1)
OUTPUT_TEMPLATE=$(python3 -c "
import sys; sys.path.insert(0,'${TOOLS_DIR}')
from synod_config import get_template
print(get_template('$MODE'))
" 2>/dev/null)
```

### Fallback Reference (if config unavailable)

<details>
<summary>Mode-specific templates</summary>

#### Mode: review
```markdown
## 코드 리뷰 결과

### 발견된 문제
- **[ERROR]** {critical issue} - {explanation}
- **[WARNING]** {moderate issue} - {explanation}
- **[INFO]** {suggestion} - {explanation}

### 권장 사항
{prioritized list of fixes}

### 신뢰도: {FINAL_CONFIDENCE}%
{brief note on agreement/disagreement between models}
```

#### Mode: design
```markdown
## 아키텍처 결정

### 권장 접근법
{description of chosen architecture}

### 트레이드오프
| Aspect | Chosen Approach | Alternative | Rationale |
|--------|-----------------|-------------|-----------|
| ... | ... | ... | ... |

### 구현 단계
1. {step}
2. {step}
...

### 신뢰도: {FINAL_CONFIDENCE}%
{note on design certainty}
```

#### Mode: debug
```markdown
## 디버그 분석

### 근본 원인
{identified cause with evidence}

### 증거 체인
1. {symptom} -> {cause}
2. {trace} -> {conclusion}

### 권장 수정
{code or steps to fix}

### 예방책
{how to avoid in future}

### 신뢰도: {FINAL_CONFIDENCE}%
```

#### Mode: idea
```markdown
## 아이디어 평가

### 순위별 아이디어

#### 1. {Top Idea}
**장점:** {list}
**단점:** {list}
**실현 가능성:** {high/medium/low}

#### 2. {Second Idea}
...

### 권장 사항
{which idea to pursue and why}

### 신뢰도: {FINAL_CONFIDENCE}%
```

#### Mode: general
```markdown
## 답변

{comprehensive response}

### 핵심 포인트
- {point 1}
- {point 2}
- {point 3}

### 고려 사항
{nuances, edge cases, caveats}

### 신뢰도: {FINAL_CONFIDENCE}%
```

</details>

## Step 4.4: Include Decision Rationale

Add a collapsible section showing deliberation process:

```markdown
<details>
<summary>숙의 과정</summary>

### 모델 기여
- **Claude (Validator):** {key contribution}
- **Gemini (Architect):** {key contribution}
- **OpenAI (Explorer):** {key contribution}

### 해결된 주요 쟁점
1. {contention} -> {resolution}
2. {contention} -> {resolution}

### 신뢰 점수
- Claude: {score} ({rating})
- Gemini: {score} ({rating})
- OpenAI: {score} ({rating})

</details>
```

## Step 4.4b: Append Debate Quality Metrics (v3.2)

After the decision rationale, append a quality metrics summary line to the final output:

```bash
# Collect metrics from all Phase 1 parsed responses
METRICS_SUMMARY=$(python3 -c "
import sys, json; sys.path.insert(0,'${TOOLS_DIR}')
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location('synod_parser', '${TOOLS_DIR}/synod-parser.py')
sp = module_from_spec(spec); spec.loader.exec_module(sp)
results = []
for f in ['gemini','openai','claude']:
    path = '${SESSION_DIR}/round-1-solver/' + f + '-parsed.json'
    try:
        with open(path) as fh: results.append(json.load(fh))
    except: pass
if results:
    agg = sp.collect_round_metrics(results)
    print(sp.format_metrics_summary(agg))
" 2>/dev/null)

# Append to synthesis output if metrics available
if [[ -n "$METRICS_SUMMARY" ]]; then
    echo "" >> "${SESSION_DIR}/round-4-synthesis.md"
    echo "$METRICS_SUMMARY" >> "${SESSION_DIR}/round-4-synthesis.md"
fi
```

## Step 4.5: Save Final State

Save `${SESSION_DIR}/round-4-synthesis.md` with full output.

Update status.json:
```json
{
  "current_round": 4,
  "round_status": {"0": "complete", "1": "complete", "2": "complete", "3": "complete", "4": "complete"},
  "status": "complete",
  "final_confidence": {FINAL_CONFIDENCE},
  "completed_at": "{ISO_TIMESTAMP}"
}
```

```bash
# Emit synthesis complete (v2.1)
synod_progress '{"event":"model_complete","model":"claude"}'
synod_progress '{"event":"phase_end","phase":4}'

# Cleanup progress display
kill $PROGRESS_PID 2>/dev/null; rm -f "$PROGRESS_FIFO"
```

**Session Complete:** Present final synthesis to user.
