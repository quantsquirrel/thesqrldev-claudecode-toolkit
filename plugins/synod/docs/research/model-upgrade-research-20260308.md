# Synod Model Upgrade Research Report

**Date:** 2026-03-08
**Status:** Complete
**Method:** 5-stage parallel scientist research (sciomc)

---

## Executive Summary

Synod에서 사용 중인 모델 대부분이 1~2세대 뒤처져 있습니다. 특히 **`gemini-3-pro-preview`가 내일(3/9) 종료**되어 긴급 조치가 필요하고, OpenAI는 GPT-5.x 시대로 진입했으며, Groq의 `mixtral` 모델은 이미 deprecated 상태입니다.

**핵심 권고:**
1. **긴급** — Gemini `pro` → `gemini-3.1-pro-preview` 마이그레이션 (3/9 종료)
2. **높음** — OpenAI `gpt-4o` → `gpt-5.4`, `o3` 유지, `o4-mini` → `gpt-5-mini`
3. **높음** — Groq `mixtral` 제거, `70b` → `llama-3.3-70b-versatile`, Llama 4 Scout 추가
4. **중간** — Mistral 슬러그 업데이트 + Magistral 추론 모델 추가
5. **중간** — Grok `grok-4-1-fast-reasoning` 추가
6. **낮음** — DeepSeek는 엔드포인트 동일 (V3.2로 자동 업그레이드됨), 문서만 수정

---

## 1. Provider별 현황 및 권고

### 1.1 Google Gemini (긴급)

| Synod Key | 현재 | 권고 | 긴급도 |
|-----------|------|------|--------|
| `flash` | `gemini-3-flash-preview` | 유지 | - |
| `pro` | `gemini-3-pro-preview` | **`gemini-3.1-pro-preview`** | **긴급 (3/9 종료)** |
| `3.1-flash-lite` | `gemini-3.1-flash-lite-preview` | 유지 | - |
| `3.1-pro` | `gemini-3.1-pro-preview` | 유지 | - |
| `2.5-flash` | `gemini-2.5-flash` | 유지 (GA) | - |
| `2.5-pro` | `gemini-2.5-pro` | 유지 (GA) | - |
| (신규) `2.5-flash-lite` | - | `gemini-2.5-flash-lite` | 낮음 (예산 티어) |

**핵심:** Gemini 3.1 Pro는 GPQA Diamond 94.3% (현재 SOTA), SWE-Bench 80.8%로 최상위권. 가격 $1.25/$5.00으로 가성비 최고의 프론티어 모델.

### 1.2 OpenAI (높음)

| Synod Key | 현재 | 권고 | 이유 |
|-----------|------|------|------|
| `gpt4o` | `gpt-4o` ($5/$20) | **`gpt-5.4`** ($2.50/$15) | 성능 대폭 향상 + 가격 인하 |
| `o3` | `o3` ($10/$40) | 유지 또는 `gpt-5.4` (reasoning.effort=high) | o3 API 계속 제공 |
| `o4mini` | `o4-mini` (~$1.1/$4.4) | **`gpt-5-mini`** ($0.25/$2) | 공식 후계자, 가격 대폭 인하 |

**신규 추가 후보:**
- `gpt54` → `gpt-5.4` — 현재 플래그십 (AIME 100%, OSWorld 73%, SWE-Bench ~83%)
- `gpt5mini` → `gpt-5-mini` — 가성비 모델 ($0.25/$2.00)
- `o3pro` → `o3-pro` — 최고급 추론 ($20/$80, 선택적)

**핵심:** GPT-5.4는 `reasoning.effort` 파라미터로 o-series를 통합. OSWorld 75%, GPQA 92.8%, ARC-AGI-2 73.3%.

### 1.3 DeepSeek (낮음 — 자동 업그레이드)

| Synod Key | 현재 | 권고 | 이유 |
|-----------|------|------|------|
| `chat` | `deepseek-chat` | 유지 (엔드포인트 동일) | 백엔드가 V3 → V3.2로 자동 업그레이드 |
| `reasoner` | `deepseek-reasoner` | 유지 (엔드포인트 동일) | V3.2 thinking mode로 자동 전환 |

- DeepSeek R2는 취소됨, V4는 미출시 (Huawei 이전 지연)
- 가격: $0.28/$0.42 per 1M — 오픈소스 최저가 수준
- SWE-Bench 73.1% (오픈소스 SOTA)

### 1.4 Groq (높음 — deprecated 모델 있음)

| Synod Key | 현재 | 권고 | 이유 |
|-----------|------|------|------|
| `8b` | `llama-3.1-8b-instant` | 유지 | 840 T/s, 활성 |
| `70b` | `llama-3.1-70b-versatile` | **`llama-3.3-70b-versatile`** | 3.1 비활성화됨 |
| `mixtral` | `mixtral-8x7b-32768` | **제거** | 2025-03-20 deprecated |

**신규 추가 후보:**
- `scout` → `meta-llama/llama-4-scout-17b-16e-instruct` — 750 T/s, 멀티모달, 131K ctx
- `gpt-oss` → `openai/gpt-oss-120b` — 500 T/s, 고성능 추론
- `qwen3` → `qwen/qwen3-32b` — 400 T/s, 코딩/추론 강점

### 1.5 Grok / xAI (중간)

| Synod Key | 현재 | 권고 | 이유 |
|-----------|------|------|------|
| `fast` | `grok-4-fast` | 유지 | - |
| `grok4` | `grok-4` | 유지 | - |
| `mini` | `grok-3-mini` | 유지 | - |
| `vision` | `grok-2-vision-1212` | 유지 | - |

**신규 추가 후보:**
- `reasoning` → `grok-4-1-fast-reasoning` — 추론 포함, 2M 컨텍스트, $0.20/1M 입력
- `heavy` → `grok-4-heavy` — 멀티에이전트 강화

**참고:** Grok 4.20 (멀티에이전트), Grok 5 (6T params)는 API 미출시 (Q2 2026 예정)

### 1.6 Mistral (중간)

| Synod Key | 현재 | 권고 | 이유 |
|-----------|------|------|------|
| `large` | `mistral-large-latest` | 유지 (Large 3에 해당) | - |
| `medium` | `mistral-medium-3` | **`mistral-medium-latest`** | 슬러그 표준화 |
| `small` | `mistral-small-latest` | 유지 | - |
| `codestral` | `codestral-latest` | 유지 | - |
| `devstral` | `devstral-2` | **`devstral-latest`** | 슬러그 표준화 |

**신규 추가 후보:**
- `magistral` → `magistral-medium-latest` — 추론 전용 (chain-of-thought)
- `magistral-small` → `magistral-small-latest` — 오픈소스 추론 (24B, Apache 2.0)

---

## 2. Benchmark 비교 (2026년 3월 기준)

### 2.1 코딩 (SWE-Bench Verified)

| 모델 | 점수 | 비고 |
|------|------|------|
| Claude Opus 4.5 | 80.9% | 최고 |
| Gemini 3.1 Pro | 80.8% | 통계적 동률 |
| GPT-5.2 | 80.0% | - |
| Claude Sonnet 4.6 / GPT-5.4 | 77.2% | 동률 |
| DeepSeek V3.2 | 73.1% | 오픈소스 SOTA |

### 2.2 추론 (GPQA Diamond)

| 모델 | 점수 |
|------|------|
| Gemini 3.1 Pro | **94.3%** (SOTA) |
| GPT-5.2 Pro | 93.2% |
| GPT-5 (High) | 92.4% |
| GPT-5.4 | 92.8% |
| Claude Opus 4.6 | ~91% |

### 2.3 수학 (AIME 2025/2026)

| 모델 | AIME 2025 | 비고 |
|------|-----------|------|
| GPT-5.2 | **100%** | 도구 없이 달성 (유일) |
| GPT-5.4 | 100% (AIME 2026) | - |
| Gemini 3 Pro | 100% | 코드 실행 필요 |

### 2.4 에이전트 (OSWorld)

| 모델 | 점수 |
|------|------|
| GPT-5.4 | 75.0% (인간 72.4% 초과) |
| Claude Opus 4.6 | 72.7% |
| Claude Sonnet 4.6 | 72.5% |
| GPT-5.2 | 38.2% (대폭 하락) |

### 2.5 가성비 (성능 대비 비용)

| 모델 | 입력/출력 ($/1M) | SWE-Bench | 가성비 등급 |
|------|-------------------|-----------|------------|
| DeepSeek V3.2 | $0.28/$0.42 | 73.1% | S (최고) |
| Gemini 3.1 Pro | $1.25/$5.00 | 80.8% | A |
| GPT-5-mini | $0.25/$2.00 | - | A (추정) |
| GPT-5.4 | $2.50/$15.00 | ~83% | B+ |
| Claude Sonnet 4.6 | $3.00/$15.00 | 77.2% | B |
| Claude Opus 4.6 | $15.00/$75.00 | 80.9% | C (프리미엄) |

---

## 3. 권고 구현 우선순위

### Phase 1: 긴급 (즉시, 3/9 전)
1. `gemini-3.py`: `pro` → `gemini-3.1-pro-preview`

### Phase 2: 높음 (1주 내)
2. `openai-cli.py`: MODEL_MAP에 `gpt54`, `gpt5mini` 추가, DEFAULT_MODEL을 `gpt54`로 변경
3. `groq-cli.py`: `mixtral` 제거, `70b` → `llama-3.3-70b-versatile`, `scout` 추가
4. `config/synod-modes.yaml`: 새 모델 반영하여 모드/티어 라우팅 업데이트

### Phase 3: 중간 (2주 내)
5. `mistral-cli.py`: 슬러그 업데이트 + `magistral` 추가
6. `grok-cli.py`: `reasoning` 모델 추가
7. `base_provider.py`: COLD_START_DEFAULTS에 신규 모델 추가
8. `config/synod-modes.yaml`: 신규 모델에 대한 tier 매핑 추가

### Phase 4: 낮음 (v4.0 고려)
9. DeepSeek 문서 업데이트 (V3.2 반영)
10. `gemini-3.py`: `2.5-flash-lite` 예산 티어 추가
11. OpenRouter MODEL_MAP 최신화 (현재 모델 구식)

---

## 4. synod-modes.yaml 권고 변경안

```yaml
# Phase 2 적용 후 예상 구성
modes:
  review:
    models:
      gemini:
        model: "flash"           # gemini-3-flash-preview (유지)
        thinking: "high"
      openai:
        model: "gpt54"           # gpt-5.4 (신규)
        reasoning: "medium"

  design:
    models:
      gemini:
        model: "3.1-pro"         # gemini-3.1-pro-preview
        thinking: "high"
      openai:
        model: "gpt54"           # gpt-5.4
        reasoning: "high"

  debug:
    models:
      gemini:
        model: "flash"
        thinking: "high"
      openai:
        model: "o3"              # 추론 특화 유지
        reasoning: "high"

  idea:
    models:
      gemini:
        model: "3.1-pro"
        thinking: "high"
      openai:
        model: "gpt54"
        reasoning: null           # reasoning.effort=none

  general:
    models:
      gemini:
        model: "flash"
        thinking: "medium"
      openai:
        model: "gpt54"
        reasoning: null

tiers:
  fast:
    gemini:
      model: "flash"
      thinking: "medium"
    openai:
      model: "gpt5mini"          # gpt-5-mini (신규, 최저가)
      reasoning: null

  deep:
    gemini:
      model: "3.1-pro"
      thinking: "high"
    openai:
      model: "o3"               # 최고 추론 유지
      reasoning: "high"
```

---

## 5. 리서치 신뢰도

| 항목 | 신뢰도 | 근거 |
|------|--------|------|
| Gemini 3-pro-preview 종료 (3/9) | HIGH | Google 공식 문서 직접 확인 |
| OpenAI GPT-5.x 시리즈 출시 | HIGH | platform.openai.com + 다수 매체 교차 검증 |
| Groq mixtral deprecated | HIGH | console.groq.com/docs/deprecations |
| 벤치마크 순위 | HIGH (코딩/추론), MEDIUM (에이전트) | vals.ai, Scale AI SEAL 등 12+ 소스 |
| 가격 정보 | MEDIUM | 빠르게 변동, 교차 검증했으나 변경 가능 |
| DeepSeek V4 미출시 | HIGH | 다수 매체 확인 (Huawei 이전 지연) |

---

## Appendix: 연구 방법론

- 5개 병렬 scientist 에이전트 (Gemini, OpenAI, DeepSeek/Groq, Grok/Mistral/신규, 벤치마크)
- 각 에이전트가 공식 문서 + 기술 매체를 웹 검색으로 교차 검증
- 총 70+ 웹 소스 참조, 2026년 2~3월 데이터 기준
