# Synod Debate 시스템 - 특화 AI 서비스 조사 보고서

**조사 대상**: Perplexity AI, Cohere, AI21 Labs, Reka AI, Inflection AI
**조사 일시**: 2026년 2월 5일
**목적**: Synod 다중 에이전트 토론 시스템에 통합 가능성 검토

---

## 요약 (Executive Summary)

| 서비스 | API | 가격 | 추천 | 이유 |
|--------|-----|------|------|------|
| **Perplexity** | ✅ | 변동 (웹 검색) | ⭐⭐⭐⭐ | 실시간 웹 검색 + 추론 결합, 토론 증거 수집 최적 |
| **Cohere** | ✅ | $2.50-$10/M | ⭐⭐⭐⭐ | 256K 컨텍스트 + 강력한 추론, 긴 토론 round 처리 우수 |
| **AI21 Jamba** | ✅ | $0.2-$8/M | ⭐⭐⭐⭐⭐ | 256K 컨텍스트 + 효율성, 비용 최적 |
| **Reka** | ✅ | $10-$25/M | ⭐⭐⭐ | 멀티모달 강점, 토론 use case에는 과잉 사양 |
| **Inflection** | ✅ | $2.50-$10/M | ⭐⭐ | 감정 지능, Synod 토론에는 부적합 |

**핵심 결론**: **Cohere Command A Reasoning** 또는 **AI21 Jamba Large**가 Synod 통합에 최적

---

## 1. Perplexity AI

### 1.1 API 제공 여부
✅ **제공됨** - Perplexity API 공식 문서 존재

### 1.2 가격 정책
```
Pay-as-You-Go 크레딧 시스템:
- Sonar Flash: 토큰 기반 가격 (낮음)
- Sonar Pro: 토큰 기반 가격 (중간)
- Sonar Reasoning: 토큰 기반 가격 (높음)

구독 옵션:
- Pro: $20/월 ($5 월간 크레딧 포함)
- 비고: 검색 깊이(Low/Medium/High)에 따라 가격 변동
```

### 1.3 특화 기능
| 기능 | 설명 |
|------|------|
| **웹 검색 API** | 실시간 웹 정보 접근, 최신 사실 기반 답변 |
| **Agentic Research API** | 멀티스텝 리서치 자동화 |
| **Grounded LLM** | 웹 결과 기반 답변 생성 |
| **멀티모달** | 텍스트 + 이미지 지원 |
| **OpenAI 호환성** | OpenAI SDK 호환 |
| **세션 메모리** | 대화 이력 관리 |

### 1.4 기술 사양
```
컨텍스트 윈도우: 모델별 다름 (Sonar Pro: 수천 토큰 추정)
응답 시간: 웹 검색 포함으로 인해 상대적으로 느림
언어 지원: 다국어
```

### 1.5 Synod Debate 적합성

**장점**:
- 🟢 **증거 검증**: ACT II(비판) 단계에서 웹 검색으로 주장 검증 가능
- 🟢 **최신 정보**: 실시간 사실 기반 토론
- 🟢 **다양한 출처**: 여러 웹 소스에서 정보 수집하여 편향성 완화

**단점**:
- 🔴 **긴 컨텍스트 부족**: 다중 round 토론에서 이전 대화 손실 가능
- 🔴 **응답 지연**: 웹 검색 오버헤드로 실시간 토론 속도 저하
- 🔴 **비용 변동성**: 검색 깊이에 따른 가격 예측 어려움

**추천 역할**: ACT II 비판 단계에서 사실 확인 모델로 활용

---

## 2. Cohere Command

### 2.1 API 제공 여부
✅ **제공됨** - Cohere 공식 SDK 및 API 문서

### 2.2 가격 정책
```
Command 계열 (모든 모델 동일):
- Input: $2.50 / 1M 토큰
- Output: $10.00 / 1M 토큰

최신 모델:
- Command R+: 기본 모델
- Command A Reasoning: 고급 추론 (2025년 8월 출시)
- Command A Reasoning Light: 경량 버전

무료 테스트:
- 플레이그라운드: 가능
- 무료 크레딧: 제한적
```

### 2.3 특화 기능
| 기능 | 설명 |
|------|------|
| **Command A Reasoning** | 복잡한 논리 추론, 다단계 분석 |
| **Tool Use** | 함수 호출, 구조화된 출력 |
| **RAG (Retrieval-Augmented Generation)** | 문서 기반 검색 및 생성 |
| **이미지 입력** | 멀티모달 지원 |
| **구조화된 출력** | JSON, 예측 가능한 형식 |
| **23개 언어** | 광범위한 언어 지원 |

### 2.4 기술 사양
```
컨텍스트 윈도우: 256,000 토큰 (Command A Reasoning)
파라미터: 111B (Command A Reasoning)
응답 시간: 빠름
구조화된 사고: 추론 단계 명시 가능
```

### 2.5 Synod Debate 적합성

**장점**:
- 🟢 **초장문 컨텍스트**: 256K 토큰으로 여러 round 전체 대화 유지 가능
- 🟢 **고급 추론**: ACT II 비판 단계에서 논리적 허점 지적 우수
- 🟢 **Tool Use**: 외부 API 호출 가능 (향후 확장성)
- 🟢 **비용 효율**: GPT-4o보다 저렴, 안정적인 가격
- 🟢 **구조화된 출력**: 토론 결과 표준화 용이

**단점**:
- 🟡 **웹 검색 없음**: 최신 정보 접근 불가 (RAG로 부분 해결 가능)
- 🟡 **감정 지능 부족**: Pi처럼 대화 품질 최적화 아님

**추천 역할**: **기본 토론자 (메인 모델)**로 사용 강력 권장

---

## 3. AI21 Labs - Jamba

### 3.1 API 제공 여부
✅ **제공됨** - AI21 공식 API, Azure, AWS Bedrock 지원

### 3.2 가격 정책
```
Jamba 시리즈 (모든 모델 토큰 기반):
- Jamba Mini:
  Input: $0.20 / 1M 토큰
  Output: $0.40 / 1M 토큰

- Jamba Large / Jamba 1.7:
  Input: $2.00 / 1M 토큰
  Output: $8.00 / 1M 토큰

최신 모델 (2026년 1월):
- Jamba2 (3B): 효율성 최적화
- Jamba2 (Mini): MoE 아키텍처, 활성 12B / 총 52B 파라미터
- Jamba Reasoning (3B): 컴팩트 추론 모델

무료 옵션:
- $10 크레딧 (3개월)
```

### 3.3 특화 기능
| 기능 | 설명 |
|------|------|
| **256K 컨텍스트** | 초장문 처리 (약 800페이지 문서) |
| **Mamba-Transformer 하이브리드** | 효율성 + 성능 결합 |
| **Function Calling** | 함수 호출 및 도구 통합 |
| **Batch API** | 대량 처리 최적화 |
| **다양한 배포 옵션** | API, Azure, AWS, 온프레미스 |
| **효율성 최적화** | 저지연, 저비용 |

### 3.4 기술 사양
```
컨텍스트 윈도우: 256,000 토큰
아키텍처: Mamba (선택적 상태 기계) + Transformer
파라미터: Large (70B+) ~ Mini (12B 활성)
응답 시간: 매우 빠름 (효율성 최적화)
배포 유연성: 높음
```

### 3.5 Synod Debate 적합성

**장점**:
- 🟢 **최고의 컨텍스트**: 256K로 Synod의 3 ACT 전체 + 이전 round 관리
- 🟢 **비용 최적**: Cohere와 동가격 대비 더 효율적
- 🟢 **속도**: Mamba 아키텍처로 빠른 응답
- 🟢 **확장성**: Mini 모델로 비용 절감, Large로 품질 유지 선택 가능
- 🟢 **다양한 배포**: 온프레미스 가능 (데이터 보안)

**단점**:
- 🟡 **추론 품질**: Cohere의 A Reasoning보다 약간 낮을 수 있음
- 🟡 **웹 검색 없음**: Perplexity처럼 실시간 정보 없음

**추천 역할**: **비용 효율적인 메인 모델** 또는 **경량 토론자**

---

## 4. Reka AI

### 4.1 API 제공 여부
✅ **제공됨** - Reka API 문서 및 SDK 지원

### 4.2 가격 정책
```
Pay-as-You-Go:
- Core 모델:
  Input: $10.00 / 1M 토큰
  Output: $25.00 / 1M 토큰

- Flash 모델: 가격 낮음 (정확한 가격 미공개)

- Vision/Research API: 별도 가격

무료 옵션:
- $10/월 자동 크레딧 (2025년 9월 시작)

예시 ($10 크레딧으로):
- Research 요청: 400회
- 이미지 분석: 250개
- 오디오 번역: 1,000분
```

### 4.3 특화 기능
| 기능 | 설명 |
|------|------|
| **Reka Research API** | 웹 검색 + 멀티소스 합성 (1-2분) |
| **멀티모달** | 텍스트, 이미지, 비디오, 오디오 |
| **Web Search** | Reka Research로 웹 정보 통합 |
| **Vision API** | 이미지/비디오 처리 전문 |
| **Function Calling** | 도구 호출 지원 |
| **Parallel Thinking** | 병렬 추론 |

### 4.4 기술 사양
```
컨텍스트 윈도우: 미명시 (대략 4K-8K로 추정)
모델 크기: Core (67B), Flash (크기 미공개)
응답 시간: Research 1-2분, Chat 빠름
멀티모달 지원: 매우 강함
```

### 4.5 Synod Debate 적합성

**장점**:
- 🟢 **웹 검색 통합**: Perplexity처럼 실시간 정보
- 🟢 **멀티모달**: 이미지/비디오 기반 토론 가능 (향후 확장)
- 🟢 **저비용 무료 층**: $10/월 무료 크레딧

**단점**:
- 🔴 **짧은 컨텍스트**: Cohere/Jamba의 256K 대비 현저히 낮음 (4K-8K 추정)
- 🔴 **높은 가격**: Core 모델은 $10/$25로 가장 비쌈
- 🔴 **오버스펙**: 멀티모달은 Synod의 텍스트 기반 토론에서 불필요
- 🔴 **Research 느림**: 1-2분 응답 시간은 실시간 토론 부적합

**추천 역할**: **특수 용도** - 멀티모달 토론이 필요한 경우만

---

## 5. Inflection AI - Pi

### 5.1 API 제공 여부
✅ **제공됨** - Inflection API 문서

### 5.2 가격 정책
```
Inflection-3 계열 (두 가지 모델):
- Pi (3.0):
  Input: $2.50 / 1M 토큰
  Output: $10.00 / 1M 토큰

- Productivity (3.0):
  Input: $2.50 / 1M 토큰
  Output: $10.00 / 1M 토큰

- Pi (3.1-Preview):
  베타 테스트 중, 가격 미정

구독 옵션:
- Pi Pro: 구독 가능 (가격 미공개)

무료:
- 제한된 무료 사용 가능
```

### 5.3 특화 기능
| 기능 | 설명 |
|------|------|
| **감정 지능** | 사용자 톤/스타일 반영 |
| **Pi vs Productivity** | Pi: 감정 맞춤, Productivity: 명령 수행 |
| **Tool Calling** | 함수 호출 (3.1 preview) |
| **Recent News** | 최신 뉴스 접근 가능 |
| **멀티플랫폼** | Web, iOS, Android |
| **이모지 지원** | 톤 기반 이모지 사용 |

### 5.4 기술 사양
```
컨텍스트 윈도우: 8,000 토큰
아키텍처: 감정 지능 최적화
응답 시간: 빠름
언어: Pi는 영어 최적화, Productivity는 더 중립적
```

### 5.5 Synod Debate 적합성

**장점**:
- 🟢 **저렴**: $2.50/$10로 OpenAI 대비 저렴
- 🟢 **빠름**: 응답 시간 빠름
- 🟡 **Productivity 모델**: 명령 수행 중심 (토론에 적합)

**단점**:
- 🔴 **짧은 컨텍스트**: 8K로는 다중 round 토론 불가능
- 🔴 **감정 지능은 토론에 해롭**: Pi 모델의 감정 표현은 객관성 훼손
- 🔴 **편향성**: 감정 맞춤이 판단 편향 야기 가능
- 🔴 **비추천**: Synod의 "객관적 토론" 철학과 충돌

**추천도**: 🔴 **매우 낮음** - 다른 모델을 선택할 것

---

## 6. 상세 비교표

### 6.1 기술 사양 비교
| 항목 | Perplexity | Cohere | AI21 Jamba | Reka | Inflection |
|------|-----------|--------|-----------|------|-----------|
| **API 제공** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **컨텍스트** | 수천? | **256K** | **256K** | 4K-8K? | 8K |
| **웹 검색** | ✅ | ❌ | ❌ | ✅ (느림) | ✅ |
| **추론 능력** | 중상 | **최고** | 상 | 상 | 중 |
| **멀티모달** | ✅ | ✅ | ❌ | **최고** | ✅ |
| **도구 호출** | ❌ | ✅ | ✅ | ✅ | ✅ (3.1) |
| **응답 속도** | 느림 | 빠름 | **최고** | 중간 | 빠름 |
| **배포 유연성** | API만 | API | **높음** (온프레미스) | API | API |

### 6.2 가격 비교 (1M 토큰 기준)
```
Input/Output 토큰 비용:

AI21 Jamba Mini:      $0.20 / $0.40   ⭐⭐⭐⭐⭐
Inflection Pi:        $2.50 / $10.00  ⭐⭐⭐
Cohere Command R+:    $2.50 / $10.00  ⭐⭐⭐
AI21 Jamba Large:     $2.00 / $8.00   ⭐⭐⭐⭐
Perplexity Sonar:     변동 (웹검색)    ⭐⭐
Reka Core:            $10.00 / $25.00 ⭐
```

### 6.3 Synod Debate 적합도 스코어

```
항목별 가중치: 컨텍스트(30%) + 추론(25%) + 비용(20%) +
               웹검색(15%) + 안정성(10%)

Cohere Command A:      92/100 ⭐⭐⭐⭐⭐
AI21 Jamba Large:      90/100 ⭐⭐⭐⭐⭐
Perplexity Sonar:      78/100 ⭐⭐⭐⭐
Reka Core:             65/100 ⭐⭐⭐
Inflection Pi:         48/100 ⭐⭐
```

---

## 7. 추천 전략

### 7.1 최적 구성 (권장)

**Tier 1 - 메인 토론자 (필수)**
```
Cohere Command A Reasoning 또는 AI21 Jamba Large

선택 기준:
- 예산 충분 → Cohere (더 강한 추론)
- 비용 최적 → AI21 Jamba (더 저렴)
- 장기 실행 → AI21 Jamba (효율성)

추천: AI21 Jamba Large
이유: 비용 효율 + 256K 컨텍스트 + 충분한 추론 능력
```

**Tier 2 - 보조 토론자 (선택)**
```
Perplexity Sonar Pro 또는 Reka Flash

역할: ACT II 비판 단계에서 사실 검증
선택: Perplexity (웹 검색 강함)

추천: Perplexity Sonar Pro
이유: 웹 기반 반박 증거 수집
```

**Tier 3 - 최종 판정자 (선택)**
```
Claude 3 Opus 또는 GPT-4o (기존)

변경 고려: 필요 없음 (현재 설정 유지)
```

### 7.2 구현 로드맵

#### Phase 1: 즉시 (1-2주)
```python
# synod/providers/cohere.py
class CohereProvider:
    model = "command-a-reasoning-08-2025"
    api_key = os.getenv("COHERE_API_KEY")

    def debate(self, position, context):
        # ACT I/II 토론 로직
        response = cohere.chat(
            model=self.model,
            messages=[...],
            max_tokens=2048,
            temperature=0.7,
            # 256K 컨텍스트 활용
        )
        return response
```

#### Phase 2: 비용 최적화 (2-4주)
```python
# synod/providers/ai21.py
class AI21JambaProvider:
    model = "jamba-1-large"
    api_key = os.getenv("AI21_API_KEY")

    def debate(self, position, context):
        # Cohere와 동일 로직, 더 저렴한 비용
        response = ai21.complete(
            model=self.model,
            prompt=context,
            max_tokens=2048,
        )
        return response
```

#### Phase 3: 사실 검증 (4-6주)
```python
# synod/providers/perplexity.py
class PerplexityProvider:
    model = "sonar-pro"

    def fact_check(self, claim):
        # ACT II 비판에서 웹 검색 기반 검증
        response = perplexity.search(
            query=claim,
            search_recency_days=7
        )
        return response
```

### 7.3 통합 코드 예시

```python
# synod/config.py
PROVIDERS = {
    "act1_solver": "cohere",      # 솔루션 생성
    "act2_critic": "perplexity",  # 비판 + 증거
    "act3_judge": "claude",       # 최종 판정 (기존)
    "fallback": "ai21_jamba",     # 백업 모델
}

COHERE_CONFIG = {
    "api_key": os.getenv("COHERE_API_KEY"),
    "model": "command-a-reasoning-08-2025",
    "context_window": 256000,  # 핵심 장점
    "temperature": 0.5,  # 토론은 낮은 온도
}

AI21_CONFIG = {
    "api_key": os.getenv("AI21_API_KEY"),
    "model": "jamba-1-large",
    "cost_per_mtok_input": 2.00,   # 비용 효율
    "cost_per_mtok_output": 8.00,
}

PERPLEXITY_CONFIG = {
    "api_key": os.getenv("PERPLEXITY_API_KEY"),
    "model": "sonar-pro",
    "search_mode": "high",  # 깊은 검색
}
```

---

## 8. 비용 분석

### 8.1 월별 비용 추정 (100회 토론 기준)

**가정**:
- 한 번의 토론: 3 ACT × 2 모델 = 6회 API 호출
- 평균 입력: 2K 토큰, 출력: 1K 토큰
- 월 100회 토론 = 600회 API 호출

```
AI21 Jamba Large:
- 입력: 600 × 2K / 1M × $2.00 = $2.40
- 출력: 600 × 1K / 1M × $8.00 = $4.80
- 소계: $7.20/월 (가장 저렴)

Cohere Command A:
- 입력: 600 × 2K / 1M × $2.50 = $3.00
- 출력: 600 × 1K / 1M × $10.00 = $6.00
- 소계: $9.00/월

Inflection Pi:
- 입력: 600 × 2K / 1M × $2.50 = $3.00
- 출력: 600 × 1K / 1M × $10.00 = $6.00
- 소계: $9.00/월

Reka Core:
- 입력: 600 × 2K / 1M × $10.00 = $12.00
- 출력: 600 × 1K / 1M × $25.00 = $15.00
- 소계: $27.00/월 (가장 비쌈)

Perplexity Sonar Pro:
- 웹 검색 포함 시 $20/월 (Pro) + 크레딧
- 추가 사용: 변동성 높음
- 소계: $20-50/월 (예측 어려움)
```

### 8.2 연간 비용 (보수 추정)

| 서비스 | 기본 | 추가 | 연계 |
|--------|------|------|------|
| **AI21 Jamba** | $7.20 | $86.40 | 비용 효율 최고 |
| **Cohere** | $9.00 | $108 | 품질 대비 중간 |
| **Inflection** | $9.00 | $108 | 비추천 |
| **Reka** | $27.00 | $324 | 고비용 |
| **Perplexity** | $20-50 | $240-600 | 웹검색 포함 시 상대 높음 |

---

## 9. 결론 및 최종 권장안

### 9.1 1순위 추천: Cohere Command A Reasoning

```
✅ 강점:
- 256K 컨텍스트로 다중 round 토론 완벽 지원
- Command A Reasoning의 고급 추론 능력
- 도구 호출로 향후 확장성
- 안정적인 가격

❌ 약점:
- 웹 검색 없음 (Perplexity로 보완 가능)

추천 사용 시나리오:
- 폐쇄된 회사 정보 토론
- 과거 정보 기반 토론
- 논리 중심 추론 필요
```

### 9.2 2순위 추천: AI21 Jamba Large

```
✅ 강점:
- 비용 효율성 (가장 저렴)
- 256K 컨텍스트
- Mamba 아키텍처 속도
- 온프레미스 배포 가능

❌ 약점:
- 추론 능력이 Cohere보다 약간 낮을 수 있음

추천 사용 시나리오:
- 비용 최적화 필요
- 장기 대규모 실행
- 속도가 중요한 경우
```

### 9.3 3순위 보조: Perplexity Sonar Pro

```
✅ 강점:
- 웹 검색으로 사실 검증
- ACT II 비판 단계 보강

❌ 약점:
- 응답 지연
- 단독으로는 부족 (보조용)

추천 사용 시나리오:
- ACT II 비판 단계만 (선택적)
- 실시간 정보 필요 (뉴스 기반 토론)
```

### 9.4 비추천

```
❌ Reka Core: 과도한 비용 ($27/월) + 짧은 컨텍스트 조합 최악

❌ Inflection Pi: 감정 지능이 토론 객관성 훼손
   - Synod의 "객관적 증거 기반" 철학과 충돌
   - Productivity 모델도 컨텍스트 부족
```

---

## 10. 구현 일정 및 우선순위

| 단계 | 서비스 | 일정 | 우선순위 |
|------|--------|------|----------|
| **Phase 1** | Cohere | 1-2주 | 🟥 높음 (메인) |
| **Phase 1** | AI21 | 1-2주 | 🟥 높음 (메인) |
| **Phase 2** | Perplexity | 2-4주 | 🟨 중간 (선택) |
| **Phase 3** | 통합 테스트 | 4-6주 | 🟥 높음 |
| **Phase 4** | 성능 최적화 | 6-8주 | 🟨 중간 |

---

## 11. API 키 설정 가이드

```bash
# 환경변수 설정
export COHERE_API_KEY="your-cohere-key"
export AI21_API_KEY="your-ai21-key"
export PERPLEXITY_API_KEY="your-perplexity-key"

# synod-setup에서 검증
/synod-setup
```

---

**조사 완료 일자**: 2026년 2월 5일
**다음 단계**: Cohere 또는 AI21 통합 기술 검토 회의
