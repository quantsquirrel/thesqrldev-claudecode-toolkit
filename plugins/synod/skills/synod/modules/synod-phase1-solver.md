# Synod Module: Phase 1 - Solver Round

> **⛔ MANDATORY EXTERNAL EXECUTION — DO NOT SKIP**
>
> This phase MUST execute actual Bash commands to call `$GEMINI_CLI` and `$OPENAI_CLI`.
> You (Claude) MUST NOT generate responses on behalf of Gemini or OpenAI.
> You MUST NOT simulate, summarize, or shortcut external model calls.
> You MUST NOT use `ask_codex`, `ask_gemini`, or any MCP tool as a substitute for CLI execution.
> If CLI execution fails, follow the error-handling module — do NOT substitute your own answer.

**Inputs:**
- `SESSION_DIR` - Session state directory
- `PROBLEM` - User's problem statement
- `MODE` - Deliberation mode
- `GEMINI_MODEL`, `GEMINI_THINKING` - Gemini configuration
- `OPENAI_MODEL`, `OPENAI_REASONING` - OpenAI configuration
- `GEMINI_CLI`, `OPENAI_CLI` - CLI executable paths

**Outputs:**
- `${SESSION_DIR}/round-1-solver/claude-response.md`
- `${SESSION_DIR}/round-1-solver/gemini-response.md`
- `${SESSION_DIR}/round-1-solver/openai-response.md`
- `${SESSION_DIR}/round-1-solver/parsed-signals.json`
- Updated `status.json` with round 1 complete

**Cross-references:**
- Called after Phase 0 (`synod-phase0-setup.md`)
- Outputs consumed by Phase 2 (`synod-phase2-critic.md`)
- Format validation failures trigger `synod-error-handling.md`

---

## Step 1.1: Prepare Prompt Files

Create temp directory for this round:
```bash
TEMP_DIR="${SESSION_DIR}/tmp"
mkdir -p "$TEMP_DIR"
```

### Gemini Prompt (Architect Persona)

Write to `${TEMP_DIR}/gemini-prompt.txt`:

```
You are the ARCHITECT in a multi-agent deliberation council (Synod).

## Your Role
- Focus on structure, patterns, and systematic approaches
- Identify architectural implications and design trade-offs
- Provide evidence-based recommendations

## Problem
{PROBLEM}

## Mode Context
This is a {MODE} request. Focus on {MODE-SPECIFIC-FOCUS}.

## REQUIRED Output Format

Provide your analysis, then END with these EXACT XML blocks:

<confidence score="[0-100]">
  <evidence>[What specific facts, code, or documentation support your solution?]</evidence>
  <logic>[How sound is your reasoning chain? Any assumptions?]</logic>
  <expertise>[Your confidence in this domain - what do you know well vs. uncertain about?]</expertise>
  <can_exit>[true ONLY if score >= 90 AND solution is complete AND no ambiguity remains]</can_exit>
</confidence>

<semantic_focus>
1. [Your PRIMARY point for debate - most important claim]
2. [Your SECONDARY point - supporting argument]
3. [Your TERTIARY point - additional consideration]
</semantic_focus>

CRITICAL: You MUST include both XML blocks. Failure to include them will require re-prompting.
```

### OpenAI Prompt (Explorer Persona)

Write to `${TEMP_DIR}/openai-prompt.txt`:

```
You are the EXPLORER in a multi-agent deliberation council (Synod).

## Your Role
- Challenge assumptions and explore edge cases
- Find counter-examples and potential failures
- Identify what others might miss

## Problem
{PROBLEM}

## Mode Context
This is a {MODE} request. Focus on {MODE-SPECIFIC-FOCUS}.

## REQUIRED Output Format

Provide your analysis, then END with these EXACT XML blocks:

<confidence score="[0-100]">
  <evidence>[What specific facts, code, or documentation support your solution?]</evidence>
  <logic>[How sound is your reasoning chain? Any assumptions?]</logic>
  <expertise>[Your confidence in this domain - what do you know well vs. uncertain about?]</expertise>
  <can_exit>[true ONLY if score >= 90 AND solution is complete AND no ambiguity remains]</can_exit>
</confidence>

<semantic_focus>
1. [Your PRIMARY point for debate - most important claim]
2. [Your SECONDARY point - supporting argument]
3. [Your TERTIARY point - additional consideration]
</semantic_focus>

CRITICAL: You MUST include both XML blocks. Failure to include them will require re-prompting.
```

### Claude Solver (Validator Persona)

As the orchestrator, you (Claude) also provide an initial solution with the VALIDATOR persona:
- Focus on correctness and validation
- Check for logical consistency
- Verify claims against known facts

Generate your solution with the same XML format requirements.

## Step 1.2: Execute External Models in Parallel

**v2.1:** Load timeouts from config and emit progress events:

```bash
# Load timeouts from config (v2.1)
MODEL_TIMEOUT=$(python3 "${TOOLS_DIR}/synod_config.py" timeouts model 2>/dev/null || echo "110")
OUTER_TIMEOUT=$(python3 "${TOOLS_DIR}/synod_config.py" timeouts outer 2>/dev/null || echo "120")

# Emit phase start
synod_progress '{"event":"phase_start","phase":1,"name":"Solver Round"}'
```

Run these commands in parallel using background execution:

```bash
# Create marker files for completion tracking
TEMP_DIR="${SESSION_DIR}/tmp"

# Gemini execution with completion marker
(
  synod_progress '{"event":"model_start","model":"gemini"}'
  run_cli "$GEMINI_CLI" --model {GEMINI_MODEL} --thinking {GEMINI_THINKING} --timeout ${MODEL_TIMEOUT:-110} \
    < "${TEMP_DIR}/gemini-prompt.txt" \
    > "${TEMP_DIR}/gemini-response.txt" 2>&1
  echo $? > "${TEMP_DIR}/gemini-exit-code"
) &
GEMINI_PID=$!

# OpenAI execution with completion marker
(
  synod_progress '{"event":"model_start","model":"openai"}'
  run_cli "$OPENAI_CLI" --model {OPENAI_MODEL} {--reasoning REASONING if o3} --timeout ${MODEL_TIMEOUT:-110} \
    < "${TEMP_DIR}/openai-prompt.txt" \
    > "${TEMP_DIR}/openai-response.txt" 2>&1
  echo $? > "${TEMP_DIR}/openai-exit-code"
) &
OPENAI_PID=$!

# Wait with outer timeout (slightly longer than inner)
# This prevents Claude's bash from timing out before subprocesses complete
WAIT_TIMEOUT=${OUTER_TIMEOUT:-120}
WAIT_START=$(date +%s)

while true; do
  # Check if both processes completed
  GEMINI_DONE=false
  OPENAI_DONE=false

  [[ -f "${TEMP_DIR}/gemini-exit-code" ]] && GEMINI_DONE=true
  [[ -f "${TEMP_DIR}/openai-exit-code" ]] && OPENAI_DONE=true

  if [[ "$GEMINI_DONE" == "true" && "$OPENAI_DONE" == "true" ]]; then
    break
  fi

  # Check timeout
  ELAPSED=$(($(date +%s) - WAIT_START))
  if [[ $ELAPSED -ge $WAIT_TIMEOUT ]]; then
    # Kill any remaining processes
    kill $GEMINI_PID 2>/dev/null || true
    kill $OPENAI_PID 2>/dev/null || true

    # Mark incomplete processes
    [[ "$GEMINI_DONE" != "true" ]] && echo "timeout" > "${TEMP_DIR}/gemini-exit-code"
    [[ "$OPENAI_DONE" != "true" ]] && echo "timeout" > "${TEMP_DIR}/openai-exit-code"
    break
  fi

  sleep 1
done

# Validate completions
# Emit model completion events
[[ -f "${TEMP_DIR}/gemini-exit-code" ]] && \
  synod_progress "{\"event\":\"model_complete\",\"model\":\"gemini\",\"duration_ms\":$(($(date +%s)-WAIT_START))000}"
[[ -f "${TEMP_DIR}/openai-exit-code" ]] && \
  synod_progress "{\"event\":\"model_complete\",\"model\":\"openai\",\"duration_ms\":$(($(date +%s)-WAIT_START))000}"

GEMINI_STATUS=$(cat "${TEMP_DIR}/gemini-exit-code" 2>/dev/null || echo "missing")
OPENAI_STATUS=$(cat "${TEMP_DIR}/openai-exit-code" 2>/dev/null || echo "missing")
```

**Process Status Handling:**
- Exit code `0` = Success, proceed with response
- Exit code `124` = Timeout from `timeout` command → Trigger fallback chain
- Exit code `timeout` = Killed by outer timeout → Trigger fallback chain
- Exit code `missing` = Unknown failure → Trigger fallback chain

## Step 1.3: Read and Validate Responses

Read response files:
- `${TEMP_DIR}/gemini-response.txt`
- `${TEMP_DIR}/openai-response.txt`

For each response, validate SID format:

```bash
# Validate with fallback
if [[ -n "$SYNOD_PARSER_CLI" ]]; then
  run_cli "$SYNOD_PARSER_CLI" --validate "$(cat ${TEMP_DIR}/gemini-response.txt)"
  PARSER_EXIT=$?
else
  echo "[Warning] synod-parser not found - using inline validation"
  # Inline validation fallback
  if grep -q '<confidence' "${TEMP_DIR}/gemini-response.txt" && \
     grep -q '<semantic_focus>' "${TEMP_DIR}/gemini-response.txt"; then
    PARSER_EXIT=0
  else
    PARSER_EXIT=1
  fi
fi
```

**Before reading responses, check process status:**

```bash
if [[ "$GEMINI_STATUS" != "0" ]]; then
  echo "[Warning] Gemini process did not complete normally (status: $GEMINI_STATUS)"
  # Trigger fallback chain (see synod-error-handling.md)
fi

if [[ "$OPENAI_STATUS" != "0" ]]; then
  echo "[Warning] OpenAI process did not complete normally (status: $OPENAI_STATUS)"
  # Trigger fallback chain (see synod-error-handling.md)
fi
```

**If format validation fails (missing XML blocks):**

Execute FORMAT ENFORCEMENT protocol (see `synod-error-handling.md`).

## Step 1.4: Parse SID Signals

For valid responses, extract:
```bash
# Parse with fallback
parse_response() {
  local input_file="$1"
  local output_file="$2"

  if [[ -n "$SYNOD_PARSER_CLI" ]]; then
    run_cli "$SYNOD_PARSER_CLI" "$(cat "$input_file")" > "$output_file"
  else
    # Minimal inline parser
    local content
    content=$(cat "$input_file")
    local score
    # POSIX-compliant extraction (macOS compatible)
    score=$(echo "$content" | sed -n 's/.*score="\([0-9]*\)".*/\1/p' | head -1)
    score=${score:-50}
    local can_exit
    can_exit=$(echo "$content" | sed -n 's/.*<can_exit>\([^<]*\)<.*/\1/p' | head -1)
    can_exit=${can_exit:-false}

    cat > "$output_file" << FALLBACK_JSON
{
  "confidence": {"score": ${score:-50}, "can_exit": ${can_exit:-false}},
  "semantic_focus": [],
  "fallback_mode": true
}
FALLBACK_JSON
  fi
}

parse_response "${TEMP_DIR}/gemini-response.txt" "${SESSION_DIR}/round-1-solver/gemini-parsed.json"
parse_response "${TEMP_DIR}/openai-response.txt" "${SESSION_DIR}/round-1-solver/openai-parsed.json"
```

## Step 1.5: Save Round State

Save to `${SESSION_DIR}/round-1-solver/`:
- `claude-response.md` - Your Validator solution
- `gemini-response.md` - Gemini Architect solution
- `openai-response.md` - OpenAI Explorer solution
- `parsed-signals.json` - Combined SID signals from all three

Update status.json:
```json
{
  "current_round": 1,
  "round_status": {"0": "complete", "1": "complete", "2": "in_progress", ...},
  "resume_point": "phase-2-critic"
}
```

## Step 1.6: Check Early Exit Condition

If ALL models have `can_exit: true` AND confidence scores are all >= 90:
- Skip to PHASE 4: Synthesis (see `synod-phase4-synthesis.md`)
- Note: "조기 합의에 도달했습니다 - 토론 라운드를 건너뜁니다"

```bash
# Emit phase end
synod_progress '{"event":"phase_end","phase":1}'
```

## Step 1.7: Verify External Model Responses (MANDATORY)

> **⛔ HALT CHECK — Do NOT proceed without passing this verification.**

Before moving to Phase 2 or early exit, verify that external models were actually called:

```bash
# MANDATORY verification — responses must exist as real files
VERIFY_PASS=true

for MODEL_NAME in gemini openai; do
  RESP_FILE="${SESSION_DIR}/round-1-solver/${MODEL_NAME}-response.md"
  if [[ ! -f "$RESP_FILE" ]] || [[ ! -s "$RESP_FILE" ]]; then
    echo "[FATAL] ${MODEL_NAME}-response.md is missing or empty." >&2
    echo "[FATAL] External CLI was NOT executed. This is a Synod protocol violation." >&2
    VERIFY_PASS=false
  fi
done

if [[ "$VERIFY_PASS" != "true" ]]; then
  echo "[HALT] Phase 1 verification FAILED. External models were not called." >&2
  echo "[HALT] Re-execute Step 1.2 with actual Bash CLI commands." >&2
  # Update status to reflect failure
  # DO NOT proceed to Phase 2 or early exit
  exit 1
fi
```

**If this check fails, you MUST go back to Step 1.2 and execute the actual Bash commands.** Do not proceed to Phase 2 or Phase 4 without real external model responses saved as files.

**Next Phase:** Proceed to Phase 2 (see `synod-phase2-critic.md`)
