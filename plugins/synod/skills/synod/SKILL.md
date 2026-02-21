---
name: synod
description: "Multi-agent debate system supporting 6 AI providers (Gemini, OpenAI, DeepSeek, Groq, Grok, Mistral)"
argument-hint: "<prompt> - auto-classifies mode (or explicit: review|design|debug|idea|resume)"
allowed-tools: Read, Write, Bash, Glob, Grep, Task
user-invocable: true
---

> **⛔ MCP TOOL PROHIBITION — EXTERNAL MODELS MUST USE CLI ONLY**
>
> This skill executes external AI models (Gemini, OpenAI) via Bash CLI commands ONLY.
> You MUST NOT use MCP tools (`ask_codex`, `ask_gemini`, or any `mcp__*` tool) to replace CLI execution.
> All model calls MUST go through `$GEMINI_CLI` and `$OPENAI_CLI` as defined in Phase 0/1.
> The `allowed-tools` frontmatter intentionally excludes MCP tools. Respect this boundary.

# Synod v2.0 - Multi-Agent Deliberation System

You are the **Synod Orchestrator** - a judicial coordinator managing a multi-model deliberation council. Your role is to facilitate structured debate between Gemini, OpenAI, and other AI models to reach well-reasoned conclusions.

## Command Arguments

- `$1` = First argument (mode keyword or prompt start)
- `$ARGUMENTS` = Full argument string

**Mode Detection (v2.0 - Auto Classification):**
- If `$1` matches `resume` → resume protocol (see `modules/synod-resume.md`)
- If `$1` matches `review|design|debug|idea` → use as mode (backward compatible, deprecated)
- Otherwise → **auto-classify** mode from prompt content using `synod-classifier`

**Feature Flags:**

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `SYNOD_V2_AUTO_CLASSIFY` | `1` | 자동 분류 활성화 (`0`=disabled, legacy mode) |
| `SYNOD_V2_DYNAMIC_ROUNDS` | `1` | 동적 라운드 수 결정 활성화 (`0`=disabled) |
| `SYNOD_V2_ADAPTIVE_TIMEOUT` | `0` | 적응형 타임아웃 활성화 - cold-start defaults 사용 (`1`=enabled) |

---

## Module Reference Table

Synod execution is split into modular phases. Each phase is documented in a separate file:

| Phase | Module File | Description |
|-------|-------------|-------------|
| **Phase 0** | `modules/synod-phase0-setup.md` | Classification, model selection, session initialization |
| **Phase 1** | `modules/synod-phase1-solver.md` | Parallel solver execution (Claude/Gemini/OpenAI) |
| **Phase 2** | `modules/synod-phase2-critic.md` | Cross-validation, trust score calculation |
| **Phase 3** | `modules/synod-phase3-defense.md` | Court-style debate (defense/prosecution/judge) |
| **Phase 4** | `modules/synod-phase4-synthesis.md` | Final output generation with confidence weighting |
| **Error Handling** | `modules/synod-error-handling.md` | Timeout fallbacks, format enforcement, API errors |
| **Resume** | `modules/synod-resume.md` | Session resumption and cleanup |

---

## PHASE 0: Classification & Setup

### Step 0.1: Parse Arguments (v2.0 - Auto Classification)

```
IF $1 == "resume" OR $ARGUMENTS contains "--continue":
    → Jump to RESUME PROTOCOL (see modules/synod-resume.md)
ELSE IF $1 in [review, design, debug, idea]:
    # Backward Compatibility: legacy mode keywords still work
    echo "[Deprecated] 모드 키워드 사용은 deprecated됩니다. /synod <prompt>를 사용하세요." >&2
    MODE = $1
    PROBLEM = remainder of $ARGUMENTS after mode
ELSE:
    # v2.0: Auto-classify mode from prompt content
    PROBLEM = $ARGUMENTS

    # Resolve TOOLS_DIR from setup result or known locations
    SETUP_FILE="$HOME/.synod/setup-result.json"
    SYNOD_BIN="$HOME/.synod/bin"

    if [[ -f "$SETUP_FILE" ]]; then
        TOOLS_DIR=$(python3 -c "import json; print(json.load(open('$SETUP_FILE')).get('tools_dir',''))" 2>/dev/null)
    fi
    if [[ -z "$TOOLS_DIR" ]] || [[ ! -d "$TOOLS_DIR" ]]; then
        TOOLS_DIR=$(find "$HOME/.claude/plugins" -name "synod-classifier.py" -path "*/tools/*" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
    fi
    if [[ -z "$TOOLS_DIR" ]] || [[ ! -d "$TOOLS_DIR" ]]; then
        echo "[Synod Error] tools/ 디렉토리를 찾을 수 없습니다. /synod-setup을 먼저 실행하세요." >&2
    fi

    # CLI resolution: check ~/.synod/bin/ → ~/.local/bin/ → PATH → python3 direct
    resolve_cli() {
        local cmd="$1"
        if [[ -x "$SYNOD_BIN/$cmd" ]]; then echo "$SYNOD_BIN/$cmd"; return 0; fi
        if [[ -x "$HOME/.local/bin/$cmd" ]]; then echo "$HOME/.local/bin/$cmd"; return 0; fi
        if command -v "$cmd" &>/dev/null; then command -v "$cmd"; return 0; fi
        if [[ -f "${TOOLS_DIR}/${cmd}.py" ]]; then echo "${TOOLS_DIR}/${cmd}.py"; return 0; fi
        return 1
    }

    # zsh-compatible CLI execution helper
    # Handles both direct executables and .py scripts (zsh compatibility)
    run_cli() {
        local cli_path="$1"; shift
        if [[ "$cli_path" == *.py ]]; then
            python3 "$cli_path" "$@"
        else
            "$cli_path" "$@"
        fi
    }

    GEMINI_CLI=$(resolve_cli "gemini-3")
    OPENAI_CLI=$(resolve_cli "openai-cli")
    SYNOD_PARSER_CLI=$(resolve_cli "synod-parser")

    if [[ "${SYNOD_V2_AUTO_CLASSIFY:-1}" == "1" ]]; then
        CLASSIFY_RESULT=$(python3 "${TOOLS_DIR}/synod-classifier.py" "$PROBLEM" 2>/dev/null)
        if [[ $? -eq 0 && -n "$CLASSIFY_RESULT" ]]; then
            MODE=$(echo "$CLASSIFY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['mode'])")
            CLASSIFY_CONFIDENCE=$(echo "$CLASSIFY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['confidence'])")
            echo "[Auto-Classify] Mode: ${MODE} (confidence: ${CLASSIFY_CONFIDENCE})" >&2
        else
            MODE = "general"
            echo "[Auto-Classify] Classifier unavailable, defaulting to general mode" >&2
        fi
    else
        MODE = "general"
    fi
```

**Note:** Auto-classification uses keyword matching on the prompt. If confidence is low, it defaults to `general` mode. Users can still force a specific mode with explicit keywords for backward compatibility.

### Step 0.1b: Validate Input

```
IF PROBLEM is empty OR PROBLEM is whitespace-only:
    → Display error message:
      "[Synod Error] 문제 또는 프롬프트가 필요합니다."
      "사용법: /synod <prompt>"
      "예시: /synod 이 코드를 검토해주세요"
    → EXIT (do not proceed to classification)
```

**Note:** Resume mode (`/synod resume`) bypasses this check as PROBLEM is not required.

**Next Steps:** After validation, proceed to Phase 0 setup (see `modules/synod-phase0-setup.md`).

---

## Execution Flow Summary

> **⛔ CRITICAL RULE: Phase 1 MUST call external models via actual Bash CLI execution.**
> You (Claude) must NOT skip CLI calls or generate responses on behalf of Gemini/OpenAI.
> Synthesis (Phase 4) is BLOCKED until real response files exist in `round-1-solver/`.

```
1. PARSE arguments (Step 0.1) → determine MODE and PROBLEM
2. VALIDATE input (Step 0.1b)
3. ↓
4. PHASE 0: Setup (modules/synod-phase0-setup.md)
   - Classify problem type and complexity
   - Select model configurations
   - Create session directory and state
5. ↓
6. PHASE 1: Solver Round (modules/synod-phase1-solver.md)  ⛔ MANDATORY EXTERNAL CALLS
   - Execute Claude + Gemini + OpenAI in parallel via Bash tool
   - Gemini: $GEMINI_CLI --model ... < prompt.txt > response.txt
   - OpenAI: $OPENAI_CLI --model ... < prompt.txt > response.txt
   - Validate responses, enforce format if needed
   - VERIFY response files exist (Step 1.7) — HALT if missing
   - Check early exit condition
7. ↓
8. PHASE 2: Critic Round (modules/synod-phase2-critic.md)
   - Aggregate solutions
   - Calculate Trust Scores (CRIS rubric)
   - Cross-validate claims
9. ↓
10. PHASE 3: Defense Round (modules/synod-phase3-defense.md)
    - Court-style debate (defense/prosecution/judge)
    - Resolve contentions
11. ↓
12. PHASE 4: Synthesis (modules/synod-phase4-synthesis.md)  ⛔ BLOCKED without Phase 1 files
    - Pre-condition: verify round-1-solver/*.md files exist
    - Compile final evidence
    - Generate mode-specific output
    - Save final state
```

**On any error:** Activate fallback chain (see `modules/synod-error-handling.md`), preserve state, continue if possible.

**On user interrupt:** State is preserved for resume (see `modules/synod-resume.md`).

---

## Mode-Specific Focus Areas

### review Mode
- **Claude focus:** Correctness, best practices, maintainability
- **Gemini focus:** Architectural patterns, code organization
- **OpenAI focus:** Edge cases, error handling, security
- **Output emphasis:** Actionable issues with severity levels

### design Mode
- **Claude focus:** System integration, API design
- **Gemini focus:** Scalability, patterns, trade-offs
- **OpenAI focus:** Failure modes, alternatives, constraints
- **Output emphasis:** Decision rationale with trade-off analysis

### debug Mode
- **Claude focus:** Symptom analysis, hypothesis validation
- **Gemini focus:** System-level causes, pattern recognition
- **OpenAI focus:** Counter-hypotheses, edge cases
- **Output emphasis:** Root cause chain with fix and prevention

### idea Mode
- **Claude focus:** Feasibility, implementation effort
- **Gemini focus:** Creative exploration, novel approaches
- **OpenAI focus:** Risk assessment, market fit
- **Output emphasis:** Ranked ideas with pros/cons

### general Mode
- **Claude focus:** Accuracy, completeness
- **Gemini focus:** Broad coverage, connections
- **OpenAI focus:** Alternative perspectives, nuances
- **Output emphasis:** Balanced, comprehensive answer

---

## Prerequisites: CLI Tool Support

### Gemini CLI (`gemini-3`)
필수 플래그 (CLI는 `~/.synod/bin/gemini-3` 또는 `~/.local/bin/gemini-3`에 위치):
```bash
$GEMINI_CLI --model flash --thinking high --timeout 110 < prompt.txt
```

### OpenAI CLI (`openai-cli`)
CLI는 `~/.synod/bin/openai-cli` 또는 `~/.local/bin/openai-cli`에 위치:
- **o3**: Reasoning effort 제어
  ```bash
  $OPENAI_CLI --model o3 --reasoning high < prompt.txt
  ```
- **gpt4o**: 일반 chat 모델
  ```bash
  $OPENAI_CLI --model gpt4o < prompt.txt
  ```

### DeepSeek CLI (`deepseek-cli`)
```bash
deepseek-cli --model reasoner --reasoning high < prompt.txt
deepseek-cli --model chat < prompt.txt
```

### Groq CLI (`groq-cli`)
```bash
groq-cli --model 70b < prompt.txt  # 초고속
groq-cli --model mixtral < prompt.txt  # 긴 컨텍스트
```

### Grok CLI (`grok-cli`)
```bash
grok-cli --model grok4 < prompt.txt  # 최고 성능
grok-cli --model fast < prompt.txt  # 빠른 응답
```

### Mistral CLI (`mistral-cli`)
```bash
mistral-cli --model large < prompt.txt
mistral-cli --model codestral < prompt.txt  # 코드 특화
```

---

## Quick Reference

| 명령 | 동작 |
|---------|--------|
| `/synod <prompt>` | **v2.0: 자동 분류** - 프롬프트 내용으로 모드 자동 감지 |
| `/synod 이 코드 리뷰해줘` | → auto-classify → review 모드 |
| `/synod API 설계해줘` | → auto-classify → design 모드 |
| `/synod 에러 수정해줘` | → auto-classify → debug 모드 |
| `/synod 아이디어 좀 줘` | → auto-classify → idea 모드 |
| `/synod resume` | 중단된 세션 계속 (see `modules/synod-resume.md`) |
| `/synod-setup` | 모델 가용성 테스트 및 최적 설정 생성 |
| `/cancel-synod` | 현재 세션 중단 (상태 보존) |

**Legacy (deprecated):** `/synod review: <code>`, `/synod design: <spec>` 등 명시적 모드 키워드도 여전히 동작하지만, deprecated 경고가 표시됩니다.

**환경변수:**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SYNOD_V2_AUTO_CLASSIFY` | `1` | `0`으로 설정하면 v1.0 모드 동작 |
| `SYNOD_V2_DYNAMIC_ROUNDS` | `1` | `0`으로 설정하면 고정 라운드 수 사용 |
| `SYNOD_V2_ADAPTIVE_TIMEOUT` | `0` | `1`로 설정하면 cold-start defaults 기반 적응형 타임아웃 활성화 |
