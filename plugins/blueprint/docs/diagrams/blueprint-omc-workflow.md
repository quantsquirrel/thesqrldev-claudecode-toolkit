# Blueprint + OMC Workflow Architecture

## 1. B-O-B-O Cycle (Blueprint-OMC Integration)

```mermaid
graph TB
    subgraph "Strategic Layer - Blueprint"
        B1[Blueprint:gap<br/>갭 분석]
        B2[Blueprint:pdca check<br/>검증]
        B3[Blueprint:pdca act<br/>의사결정]
    end

    subgraph "Tactical Layer - OMC"
        O1[OMC:실행<br/>ultrawork/team/autopilot]
        O2[OMC:교정<br/>code-review/tdd]
    end

    B1 -->|갭 보고서, WBS| O1
    O1 -->|구현 코드| B2
    B2 -->|검증 리포트| O2
    O2 -->|수정 완료| B3
    B3 -->|다음 사이클| B1

    style B1 fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style B2 fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style B3 fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style O1 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style O2 fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

## 2. PDCA Cycle Integration

```mermaid
stateDiagram-v2
    [*] --> Plan

    state "Plan (전략)" as Plan {
        [*] --> Blueprint_Gap
        Blueprint_Gap --> OMC_Research
        OMC_Research --> OMC_DeepSearch
        OMC_DeepSearch --> [*]
    }

    state "Do (전술)" as Do {
        [*] --> OMC_Ultrawork
        OMC_Ultrawork --> OMC_Team
        OMC_Team --> OMC_TDD
        OMC_TDD --> OMC_Autopilot
        OMC_Autopilot --> [*]
    }

    state "Check (전략)" as Check {
        [*] --> Blueprint_PDCA_Check
        Blueprint_PDCA_Check --> OMC_CodeReview
        OMC_CodeReview --> OMC_SecurityReview
        OMC_SecurityReview --> [*]
    }

    state "Act (양쪽 협업)" as Act {
        [*] --> Blueprint_Decision
        Blueprint_Decision --> OMC_GitMaster
        OMC_GitMaster --> OMC_Release
        OMC_Release --> [*]
    }

    Plan --> Do
    Do --> Check
    Check --> Act
    Act --> Plan: 다음 사이클
    Act --> [*]: 완료
```

## 3. Complexity-Based Routing

```mermaid
flowchart LR
    Request[개발 요청]

    Request --> Assess{복잡도 평가}

    Assess -->|긴급 핫픽스<br/>단순 버그| Direct[OMC 직접 실행]
    Assess -->|3-10 파일<br/>기능 추가| Standard[Blueprint Standard]
    Assess -->|아키텍처<br/>리팩토링| Full[Blueprint Full]
    Assess -->|탐색적<br/>개발| Explore[OMC 탐색]

    Direct --> DirectCmd["/build-fix<br/>/autopilot"]
    Standard --> StandardCmd["/blueprint:pipeline<br/>--preset=standard"]
    Full --> FullCmd["/blueprint:pipeline<br/>--preset=full"]
    Explore --> ExploreCmd["/plan<br/>/deepinit"]

    DirectCmd --> Result[코드 산출]
    StandardCmd --> Result
    FullCmd --> Result
    ExploreCmd --> Result

    style Direct fill:#4caf50,color:#fff
    style Standard fill:#2196f3,color:#fff
    style Full fill:#9c27b0,color:#fff
    style Explore fill:#ff9800,color:#fff
```

## 4. Layer Responsibility Matrix

```mermaid
graph TB
    subgraph "Blueprint Layer - 전략 (무엇을/왜)"
        BP1[프로세스 관리]
        BP2[품질 보증]
        BP3[상태 추적]
        BP4[게이트 검증]
    end

    subgraph "OMC Layer - 전술 (어떻게)"
        OMC1[코드 실행]
        OMC2[병렬 처리]
        OMC3[전문 에이전트]
        OMC4[도구 통합]
    end

    BP1 -.->|위임| OMC1
    BP2 -.->|요청| OMC3
    BP3 -.->|쿼리| OMC4
    BP4 -.->|검증 위임| OMC3

    OMC1 -.->|진행 보고| BP3
    OMC2 -.->|완료 알림| BP1
    OMC3 -.->|결과 제출| BP2
    OMC4 -.->|상태 업데이트| BP3

    style BP1 fill:#1976d2,color:#fff
    style BP2 fill:#1976d2,color:#fff
    style BP3 fill:#1976d2,color:#fff
    style BP4 fill:#1976d2,color:#fff
    style OMC1 fill:#f57c00,color:#fff
    style OMC2 fill:#f57c00,color:#fff
    style OMC3 fill:#f57c00,color:#fff
    style OMC4 fill:#f57c00,color:#fff
```

## 5. Feature Overlap Resolution

```mermaid
flowchart TD
    subgraph Pipeline
        BP_Pipeline["/blueprint:pipeline<br/>스테이지-게이트 관리"]
        OMC_Pipeline["/pipeline<br/>태스크 체이닝"]
        Rule1["Blueprint = 결정권<br/>OMC = 내부 실행"]
    end

    subgraph Planning
        BP_Gap["/blueprint:gap<br/>갭 분석"]
        OMC_Plan["/plan<br/>실행 계획"]
        Rule2["보완적 사용<br/>gap 진단 → plan 실행"]
    end

    subgraph Cancellation
        BP_Cancel["/blueprint:cancel<br/>PDCA 사이클 취소"]
        OMC_Cancel["/cancel<br/>OMC 모드 취소"]
        Rule3["각자 자기 것만 취소"]
    end

    BP_Pipeline -.->|위임| OMC_Pipeline
    OMC_Pipeline -.->|보고| BP_Pipeline

    BP_Gap -->|진단 결과| OMC_Plan
    OMC_Plan -.->|실행 중| BP_Gap

    BP_Cancel -.-> BP_Cancel
    OMC_Cancel -.-> OMC_Cancel

    style Rule1 fill:#fff9c4
    style Rule2 fill:#fff9c4
    style Rule3 fill:#fff9c4
```

## Anti-Patterns to Avoid

```mermaid
graph TD
    AP1[❌ 재귀 메타 사이클]
    AP2[❌ 파이프라인 이중 중첩]
    AP3[❌ 인지 부하 폭발]

    AP1_Desc["PDCA Check/Act에서<br/>OMC 재귀 호출 금지"]
    AP2_Desc["Blueprint 파이프라인이 메인<br/>OMC는 단일 단계 실행용"]
    AP3_Desc["치트시트 8개만 기억<br/>Blueprint 3개 + OMC 5개"]

    AP1 --> AP1_Desc
    AP2 --> AP2_Desc
    AP3 --> AP3_Desc

    style AP1 fill:#f44336,color:#fff
    style AP2 fill:#f44336,color:#fff
    style AP3 fill:#f44336,color:#fff
```

## Cheat Sheet Quick Reference

```mermaid
mindmap
    root((Blueprint + OMC))
        Blueprint Commands
            /blueprint:gap
                갭 분석
                현재 vs 목표
            /blueprint:pdca
                PDCA 사이클
                반복적 개선
            /blueprint:pipeline
                개발 파이프라인
                3/6/9 단계
        OMC Commands
            /ultrawork
                최대 병렬
                에이전트 오케스트레이션
            /tdd
                테스트 주도
                Red-Green-Refactor
            /code-review
                코드 리뷰
                품질 검증
            /autopilot
                자율 실행
                완전 자동화
            /git-master
                Git 전략
                커밋 관리
```
