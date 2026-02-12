# Skill Orchestration Flow

## 1. Skill Invocation Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant Hook as UserPromptSubmit Hook
    participant Skill as Skill Handler
    participant State as State Manager
    participant Agent as Agent System

    User->>Hook: /blueprint:pdca "목표"
    Hook->>Hook: Keyword Detection
    Hook->>Skill: Route to PDCA Skill

    Skill->>State: Initialize Cycle State
    State-->>Skill: Cycle ID

    loop PDCA Iteration
        Skill->>Agent: Spawn Plan Agents
        Agent-->>Skill: Plan Complete

        Skill->>Agent: Spawn Do Agents
        Agent-->>Skill: Implementation Done

        Skill->>Agent: Spawn Check Agents
        Agent-->>Skill: Verification Report

        Skill->>State: Update Iteration State
        Skill->>Skill: Decide Act

        alt Continue
            Skill->>Agent: Spawn Act Agents
        else Complete
            Skill->>State: Mark Complete
        end
    end

    Skill->>User: Final Report
    Skill->>State: Cleanup
```

## 2. Pipeline Stage Progression

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> Requirements: /blueprint:pipeline

    state "Full Preset (9 stages)" as Full {
        Requirements --> Architecture
        Architecture --> Design
        Design --> Implementation
        Implementation --> UnitTest
        UnitTest --> IntegrationTest
        IntegrationTest --> CodeReview
        CodeReview --> GapAnalysis
        GapAnalysis --> Verification
    }

    state "Standard Preset (6 stages)" as Standard {
        Requirements --> Design
        Design --> Implementation
        Implementation --> UnitTest
        UnitTest --> CodeReview
        CodeReview --> Verification
    }

    state "Minimal Preset (3 stages)" as Minimal {
        Design --> Implementation
        Implementation --> Verification
    }

    Verification --> [*]: Success

    note right of Full
        Critical features
        New modules
    end note

    note right of Standard
        Most dev tasks
        Default preset
    end note

    note right of Minimal
        Quick fixes
        Small changes
    end note
```

## 3. Agent Selection and Execution

```mermaid
flowchart TD
    Start[Skill Invoked] --> Phase{Phase Type}

    Phase -->|requirements| Req[analyst<br/>opus]
    Phase -->|architecture| Arch[architect<br/>opus, read-only]
    Phase -->|design| Design[design-writer<br/>sonnet]
    Phase -->|implementation| Impl[executor<br/>sonnet]
    Phase -->|unit-test| Unit[tester<br/>sonnet]
    Phase -->|integration-test| Int[tester<br/>sonnet]
    Phase -->|code-review| Review[reviewer<br/>sonnet, read-only]
    Phase -->|gap-analysis| Gap[gap-detector<br/>opus, read-only]
    Phase -->|verification| Verify[verifier<br/>sonnet, read-only]

    Req --> Execute[Execute Agent]
    Arch --> Execute
    Design --> Execute
    Impl --> Execute
    Unit --> Execute
    Int --> Execute
    Review --> Execute
    Gap --> Execute
    Verify --> Execute

    Execute --> Gate{Pass Gate?}
    Gate -->|Yes| NextPhase[Next Phase]
    Gate -->|No| Retry[Retry Phase]
    Gate -->|Critical Fail| Stop[Stop Pipeline]

    Retry --> Execute
    NextPhase --> Phase
    Stop --> Report[Generate Report]

    style Req fill:#ab47bc,color:#fff
    style Arch fill:#ab47bc,color:#fff
    style Design fill:#42a5f5,color:#fff
    style Impl fill:#66bb6a,color:#fff
    style Unit fill:#ffa726,color:#fff
    style Int fill:#ffa726,color:#fff
    style Review fill:#26c6da,color:#fff
    style Gap fill:#ef5350,color:#fff
    style Verify fill:#26a69a,color:#fff
```

## 4. Hook Integration Flow

```mermaid
graph TB
    subgraph "User Interaction"
        UI1[User Input]
        UI2[Tool Execution]
        UI3[Session Events]
    end

    subgraph "Hook Layer"
        H1[UserPromptSubmit]
        H2[PostToolUse]
        H3[SessionStart]
        H4[PreCompact]
        H5[Stop]
        H6[SessionEnd]
    end

    subgraph "State Persistence"
        S1[.blueprint/pdca/]
        S2[.blueprint/pipeline/]
        S3[.blueprint/gap/]
    end

    UI1 --> H1
    H1 -->|Keyword Match| Skill1[Invoke Skill]
    H1 -->|Pass Through| UI1

    UI2 --> H2
    H2 --> S1
    H2 --> S2

    UI3 --> H3
    H3 --> S1
    H3 --> S2

    H4 --> S1
    H4 --> S2
    H4 --> S3

    H5 --> Cleanup[Graceful Shutdown]
    H6 --> Final[Final Cleanup]

    Cleanup --> S1
    Cleanup --> S2
    Final --> S3

    style H1 fill:#4caf50,color:#fff
    style H2 fill:#2196f3,color:#fff
    style H3 fill:#ff9800,color:#fff
    style H4 fill:#9c27b0,color:#fff
    style H5 fill:#f44336,color:#fff
    style H6 fill:#607d8b,color:#fff
```

## 5. Parallel Agent Execution

```mermaid
gantt
    title Pipeline Stage Execution Timeline
    dateFormat X
    axisFormat %s

    section Requirements
    analyst (opus)           :0, 30s

    section Architecture
    architect (opus)         :30, 45s

    section Design
    design-writer (sonnet)   :75, 25s

    section Implementation
    executor (sonnet) - Task 1   :100, 20s
    executor (sonnet) - Task 2   :100, 20s
    executor (sonnet) - Task 3   :100, 20s

    section Testing
    tester (sonnet) - Unit       :120, 15s
    tester (sonnet) - Integration :135, 15s

    section Review
    reviewer (sonnet)        :150, 20s
    gap-detector (opus)      :150, 20s

    section Verification
    verifier (sonnet)        :170, 10s
```

## 6. Cancel/Cleanup Flow

```mermaid
flowchart TD
    Cancel["/blueprint:cancel"] --> Type{Cancel Type}

    Type -->|--all| All[Cancel All Workflows]
    Type -->|--cycle-id ID| Cycle[Cancel Specific PDCA]
    Type -->|--pipeline-id ID| Pipeline[Cancel Specific Pipeline]

    All --> Stop1[Stop All Agents]
    Cycle --> Stop2[Stop Cycle Agents]
    Pipeline --> Stop3[Stop Pipeline Agents]

    Stop1 --> Save1[Save State]
    Stop2 --> Save2[Save State]
    Stop3 --> Save3[Save State]

    Save1 --> Lock1[Acquire Lock]
    Save2 --> Lock2[Acquire Lock]
    Save3 --> Lock3[Acquire Lock]

    Lock1 --> Write1[Write Cancel Marker]
    Lock2 --> Write2[Write Cancel Marker]
    Lock3 --> Write3[Write Cancel Marker]

    Write1 --> Release1[Release Lock]
    Write2 --> Release2[Release Lock]
    Write3 --> Release3[Release Lock]

    Release1 --> Report[Generate Cancel Report]
    Release2 --> Report
    Release3 --> Report

    Report --> Cleanup[Cleanup Resources]

    style Cancel fill:#f44336,color:#fff
    style Report fill:#4caf50,color:#fff
```

## 7. Multi-Cycle Concurrency

```mermaid
graph TB
    subgraph "Cycle 1 - Auth Feature"
        C1P[Plan: analyst]
        C1D[Do: executor]
        C1C[Check: verifier]
        C1A[Act: pdca-iterator]
        C1P --> C1D --> C1C --> C1A
    end

    subgraph "Cycle 2 - API Refactor"
        C2P[Plan: analyst]
        C2D[Do: executor]
        C2C[Check: verifier]
        C2A[Act: pdca-iterator]
        C2P --> C2D --> C2C --> C2A
    end

    subgraph "Pipeline - Payment"
        PP1[requirements]
        PP2[design]
        PP3[implementation]
        PP1 --> PP2 --> PP3
    end

    subgraph "State Files"
        S1[".blueprint/pdca/cycle-1.json"]
        S2[".blueprint/pdca/cycle-2.json"]
        S3[".blueprint/pipeline/pipe-1.json"]
    end

    C1A -.-> S1
    C2A -.-> S2
    PP3 -.-> S3

    style C1A fill:#4caf50,color:#fff
    style C2A fill:#2196f3,color:#fff
    style PP3 fill:#ff9800,color:#fff
```
