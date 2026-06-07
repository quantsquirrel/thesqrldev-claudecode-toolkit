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

**Default CLI wiring:** `$GEMINI_CLI` resolves to `agy-cli` (Antigravity Gemini
3.5 Flash family). `$OPENAI_CLI` resolves to `cliproxy-cli` (CLIProxyAPI on
localhost:8317). Historical `--model`, `--thinking`, and `--reasoning` flags
are still passed for compatibility; the wrappers normalize them to the current
runtime defaults.

**Cross-references:**
- Called after Phase 0 (`synod-phase0-setup.md`)
- Outputs consumed by Phase 2 (`synod-phase2-critic.md`)
- Format validation failures trigger `synod-error-handling.md`

---

## Step 1.0: Deliberation Anonymization Setup (SYNOD_ANONYMIZE=1 only)

> **Flag-gated — skip entirely when `SYNOD_ANONYMIZE` is unset or `"0"` (default).**
> When the flag is off, all branding and labelling behaves exactly as in v3.6 — no change.

When `SYNOD_ANONYMIZE=1`:

```bash
if [[ "${SYNOD_ANONYMIZE:-0}" == "1" ]]; then
  # Build a real->alias map for the active roster so no phase sees which
  # provider authored which claim (arXiv:2510.07517 — identity cues drive
  # sycophantic premature consensus).
  ANON_MAP=$(python3 -c "
import sys; sys.path.insert(0,'${TOOLS_DIR}')
import model_branding, json
roster = ['claude', 'gemini', 'openai']
print(json.dumps(model_branding.build_anon_map(roster)))
")
  # Export the map for use in Steps 1.1–1.5; Phase 4 imports it to deanonymize.
  export SYNOD_ANON_MAP="$ANON_MAP"

  # Derive aliases for template substitution below.
  ALIAS_CLAUDE=$(echo "$ANON_MAP" | python3 -c "import json,sys; print(json.load(sys.stdin)['claude'])")
  ALIAS_GEMINI=$(echo "$ANON_MAP" | python3 -c "import json,sys; print(json.load(sys.stdin)['gemini'])")
  ALIAS_OPENAI=$(echo "$ANON_MAP" | python3 -c "import json,sys; print(json.load(sys.stdin)['openai'])")

  echo "[Phase 1] Anonymization ON — aliases: claude=$ALIAS_CLAUDE gemini=$ALIAS_GEMINI openai=$ALIAS_OPENAI" >&2
else
  # Flag off: aliases equal real names so every subsequent reference is a no-op.
  ALIAS_CLAUDE="Claude"
  ALIAS_GEMINI="Gemini"
  ALIAS_OPENAI="OpenAI"
fi
```

**When anonymization is active**, replace every occurrence of real model names
(Claude / Gemini / OpenAI) in the prompts written in Steps 1.1–1.3 and in the
`HISTORY_CONTEXT` tables assembled for external models with the corresponding
alias (`$ALIAS_CLAUDE`, `$ALIAS_GEMINI`, `$ALIAS_OPENAI`).  The solver
personas (ARCHITECT, EXPLORER, VALIDATOR) are role labels, not provider names,
so they may be kept as-is.

The `SYNOD_ANON_MAP` export is consumed by Phases 2–4 to maintain the same
alias substitution throughout the debate.

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

> **⚠️ BASH TIMEOUT:** When executing the Bash command for this step, you MUST set
> `timeout: ${BASH_TIMEOUT_MS}` (milliseconds) on the Bash tool call.
> Default Bash tool timeout (120s) is shorter than model execution time and will kill the process.

**v2.1 / v3.3 / v3.5:** Load model overrides from Phase 0.5 (if set), then load
tier-aware timeouts and emit progress events:

```bash
# --- v3.6.2: Consume SYNOD_MODEL_OVERRIDES from Phase 0.5 (evidence-first tier roster) ---
# tier_matrix.py emits {tier, backend, models:[{provider,cli,model,thinking|reasoning}]}.
# The roster is ALREADY backend-resolved by provider_backend (bridge identity, or
# direct with cli/model rewritten e.g. 3.5-flash->flash-latest), so model/thinking/
# reasoning here are runtime-ready and need no further translation.
_ov() { echo "$SYNOD_MODEL_OVERRIDES" | python3 -c "$1" 2>/dev/null || true; }
if [[ -n "${SYNOD_MODEL_OVERRIDES:-}" ]]; then
  _G="import json,sys;by={m.get('provider'):m for m in json.load(sys.stdin).get('models',[])};print(by.get('gemini',{}).get"
  _O="import json,sys;by={m.get('provider'):m for m in json.load(sys.stdin).get('models',[])};print(by.get('openai',{}).get"
  _TIER_NAME=$(_ov "import json,sys;print(json.load(sys.stdin).get('tier',''))")
  _TIER_BACKEND=$(_ov "import json,sys;print(json.load(sys.stdin).get('backend',''))")
  _TIER_GEMINI_MODEL=$(_ov "${_G}('model') or '')")
  _TIER_GEMINI_THINKING=$(_ov "${_G}('thinking') or '')")
  _TIER_OPENAI_MODEL=$(_ov "${_O}('model') or '')")
  _TIER_OPENAI_REASONING=$(_ov "${_O}('reasoning') or '')")

  [[ -n "$_TIER_GEMINI_MODEL"    ]] && GEMINI_MODEL="$_TIER_GEMINI_MODEL"
  [[ -n "$_TIER_GEMINI_THINKING" ]] && GEMINI_THINKING="$_TIER_GEMINI_THINKING"
  [[ -n "$_TIER_OPENAI_MODEL"    ]] && OPENAI_MODEL="$_TIER_OPENAI_MODEL"
  [[ -n "$_TIER_OPENAI_REASONING" ]] && OPENAI_REASONING="$_TIER_OPENAI_REASONING"

  echo "[Phase 1] SYNOD_MODEL_OVERRIDES applied: tier=${_TIER_NAME:-unknown} backend=${_TIER_BACKEND:-bridge}" >&2
else
  # No tier roster (default /synod path). When the direct backend is active, the
  # mode-default model strings are bridge vocabulary (e.g. 3.5-flash, gpt55fast)
  # that the direct CLIs (gemini-3/openai-cli) cannot parse -- translate them to
  # direct model keys. Bridge backend leaves them unchanged.
  if [[ "${SYNOD_PROVIDER_BACKEND:-bridge}" == "direct" ]]; then
    _PB="${TOOLS_DIR}/provider_backend.py"
    _G2=$(python3 "$_PB" --backend direct --provider gemini --translate-model "$GEMINI_MODEL" 2>/dev/null || true)
    _O2=$(python3 "$_PB" --backend direct --provider openai --translate-model "$OPENAI_MODEL" 2>/dev/null || true)
    [[ -n "$_G2" ]] && GEMINI_MODEL="$_G2"
    [[ -n "$_O2" ]] && OPENAI_MODEL="$_O2"
    echo "[Phase 1] direct backend -- translated models: gemini=$GEMINI_MODEL openai=$OPENAI_MODEL" >&2
  else
    echo "[Phase 1] SYNOD_MODEL_OVERRIDES not set -- using mode-based model defaults" >&2
  fi
fi

# --- v2.1 / v3.3: Load tier-aware timeouts, then emit phase start ---
# TIER is sourced from meta.json (written by Phase 0 classifier) when available.
# Falls back to 'standard' if not present, preserving v2.1 behavior.
_META_TIER=$(python3 -c \
  "import json,os; f='${SESSION_DIR}/meta.json'; \
   d=json.load(open(f)) if os.path.exists(f) else {}; \
   print(d.get('tier','standard'))" 2>/dev/null || echo "standard")

MODEL_TIMEOUT=$(python3 "${TOOLS_DIR}/synod_config.py" timeouts model --tier "$_META_TIER" 2>/dev/null || echo "180")
OUTER_TIMEOUT=$(python3 "${TOOLS_DIR}/synod_config.py" timeouts outer --tier "$_META_TIER" 2>/dev/null || echo "240")
BASH_TIMEOUT=$(python3 "${TOOLS_DIR}/synod_config.py" timeouts bash  --tier "$_META_TIER" 2>/dev/null || echo "300")
BASH_TIMEOUT_MS=$((BASH_TIMEOUT * 1000))

# Emit phase start
synod_progress '{"event":"phase_start","phase":1,"name":"Solver Round"}'
```

Run these commands in parallel using background execution.
**Bash tool timeout MUST be set to `${BASH_TIMEOUT_MS:-300000}` ms for this command block.**

```bash
# Create marker files for completion tracking
TEMP_DIR="${SESSION_DIR}/tmp"

# Gemini execution with completion marker
(
  synod_progress '{"event":"model_start","model":"gemini"}'
  run_cli "$GEMINI_CLI" --model {GEMINI_MODEL} --thinking {GEMINI_THINKING} --timeout ${MODEL_TIMEOUT:-180} \
    < "${TEMP_DIR}/gemini-prompt.txt" \
    > "${TEMP_DIR}/gemini-response.txt" 2>&1
  echo $? > "${TEMP_DIR}/gemini-exit-code"
) &
GEMINI_PID=$!

# OpenAI execution with completion marker
(
  synod_progress '{"event":"model_start","model":"openai"}'
  run_cli "$OPENAI_CLI" --model {OPENAI_MODEL} {--reasoning REASONING if non-empty} --timeout ${MODEL_TIMEOUT:-180} \
    < "${TEMP_DIR}/openai-prompt.txt" \
    > "${TEMP_DIR}/openai-response.txt" 2>&1
  echo $? > "${TEMP_DIR}/openai-exit-code"
) &
OPENAI_PID=$!

# Wait with outer timeout (must be < bash tool timeout)
# bash > outer > model timeout hierarchy prevents premature kills
WAIT_TIMEOUT=${OUTER_TIMEOUT:-240}
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

## Step 1.5b: Promote Solver Responses to round-1-solver/

Ensure the output directory exists, then write/copy each model's response as a
`.md` file so the HALT gate (Step 1.7) and downstream phases can find them.
Claude's own Validator response (generated inline in Step 1.2/1.3) must be
written here; external-model responses are copied from TEMP_DIR only when the
source file exists and is non-empty (a missing external model is a skipped/
failed run — do not hard-fail here; the HALT gate handles the enforcement).

```bash
# Ensure output directory exists
mkdir -p "${SESSION_DIR}/round-1-solver"

# --- Claude (Validator) ---
# Write the Validator solution produced in Step 1.2/1.3 to claude-response.md.
# CLAUDE_SOLVER_RESPONSE must hold the raw text Claude generated above.
# If the variable is unset (shouldn't happen), write a placeholder so the
# HALT gate can flag it rather than silently skipping.
if [[ -n "${CLAUDE_SOLVER_RESPONSE:-}" ]]; then
  printf '%s\n' "$CLAUDE_SOLVER_RESPONSE" > "${SESSION_DIR}/round-1-solver/claude-response.md"
else
  echo "[Warning] CLAUDE_SOLVER_RESPONSE is unset — writing empty placeholder" >&2
  : > "${SESSION_DIR}/round-1-solver/claude-response.md"
fi

# Parse Claude's response into claude-parsed.json
parse_response "${SESSION_DIR}/round-1-solver/claude-response.md" \
               "${SESSION_DIR}/round-1-solver/claude-parsed.json"

# --- Gemini (Architect) ---
if [[ -s "${TEMP_DIR}/gemini-response.txt" ]]; then
  cp "${TEMP_DIR}/gemini-response.txt" "${SESSION_DIR}/round-1-solver/gemini-response.md"
else
  echo "[Warning] ${TEMP_DIR}/gemini-response.txt missing or empty — skipping gemini-response.md" >&2
fi

# --- OpenAI (Explorer) ---
if [[ -s "${TEMP_DIR}/openai-response.txt" ]]; then
  cp "${TEMP_DIR}/openai-response.txt" "${SESSION_DIR}/round-1-solver/openai-response.md"
else
  echo "[Warning] ${TEMP_DIR}/openai-response.txt missing or empty — skipping openai-response.md" >&2
fi
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
