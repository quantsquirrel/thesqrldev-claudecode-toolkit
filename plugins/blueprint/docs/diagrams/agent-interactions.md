# Agent Interaction Patterns

## 1. Agent Catalog Overview

```mermaid
mindmap
    root((Blueprint Agents))
        Analysis
            analyst
                opus model
                Requirements analysis
            gap-detector
                opus model
                Read-only
                Gap identification
        Architecture
            architect
                opus model
                Read-only
                System design
        Implementation
            executor
                sonnet model
                Code changes
            design-writer
                sonnet model
                Documentation
        Testing
            tester
                sonnet model
                Test engineering
        Quality
            reviewer
                sonnet model
                Read-only
                Code review
            verifier
                sonnet model
                Read-only
                Verification
        Orchestration
            pdca-iterator
                sonnet model
                Cycle coordination
```

## 2. Agent Communication Pattern

```mermaid
sequenceDiagram
    participant Skill as Skill Orchestrator
    participant A1 as analyst (opus)
    participant A2 as architect (opus)
    participant A3 as executor (sonnet)
    participant A4 as verifier (sonnet)
    participant State as State Manager

    Skill->>State: Initialize Workflow
    State-->>Skill: Workflow ID

    Skill->>A1: Analyze Requirements
    activate A1
    A1->>A1: Read Files
    A1->>A1: Generate Requirements
    A1-->>Skill: Requirements Doc
    deactivate A1

    Skill->>State: Save Requirements

    Skill->>A2: Design Architecture
    activate A2
    A2->>State: Read Requirements
    A2->>A2: Create Design
    A2-->>Skill: Architecture Doc
    deactivate A2

    Skill->>State: Save Architecture

    Skill->>A3: Implement Code
    activate A3
    A3->>State: Read Design
    A3->>A3: Write Code
    A3->>A3: Run Tests
    A3-->>Skill: Implementation Done
    deactivate A3

    Skill->>State: Save Implementation

    Skill->>A4: Verify Results
    activate A4
    A4->>State: Read All Context
    A4->>A4: Run Checks
    A4-->>Skill: Verification Report
    deactivate A4

    Skill->>State: Update Final State
```

## 3. Read-Only vs Write Agents

```mermaid
flowchart LR
    subgraph "Write Agents (Code Modification)"
        W1[executor<br/>sonnet]
        W2[design-writer<br/>sonnet]
        W3[tester<br/>sonnet]
    end

    subgraph "Read-Only Agents (Analysis)"
        R1[architect<br/>opus]
        R2[reviewer<br/>sonnet]
        R3[verifier<br/>sonnet]
        R4[gap-detector<br/>opus]
    end

    subgraph "Hybrid Agents"
        H1[analyst<br/>opus]
        H2[pdca-iterator<br/>sonnet]
    end

    Codebase[(Codebase)]
    State[(State Files)]

    W1 -->|Write| Codebase
    W2 -->|Write| Codebase
    W3 -->|Write| Codebase

    R1 -->|Read| Codebase
    R2 -->|Read| Codebase
    R3 -->|Read| Codebase
    R4 -->|Read| Codebase

    H1 -->|Read/Write| Codebase
    H2 -->|Read/Write| State

    style W1 fill:#4caf50,color:#fff
    style W2 fill:#4caf50,color:#fff
    style W3 fill:#4caf50,color:#fff
    style R1 fill:#2196f3,color:#fff
    style R2 fill:#2196f3,color:#fff
    style R3 fill:#2196f3,color:#fff
    style R4 fill:#2196f3,color:#fff
    style H1 fill:#ff9800,color:#fff
    style H2 fill:#ff9800,color:#fff
```

## 4. Agent Selection by Phase

```mermaid
graph TB
    Phase[Pipeline Phase] --> Decision{Which Phase?}

    Decision -->|requirements| Requirements[analyst opus]
    Decision -->|architecture| Architecture[architect opus]
    Decision -->|design| Design[design-writer sonnet]
    Decision -->|implementation| Implementation[executor sonnet]
    Decision -->|unit-test| UnitTest[tester sonnet]
    Decision -->|integration-test| IntTest[tester sonnet]
    Decision -->|code-review| Review[reviewer sonnet]
    Decision -->|gap-analysis| Gap[gap-detector opus]
    Decision -->|verification| Verify[verifier sonnet]

    Requirements --> Tools1[Read, Grep, Glob]
    Architecture --> Tools2[Read only]
    Design --> Tools3[Write, Read]
    Implementation --> Tools4[Edit, Write, Bash]
    UnitTest --> Tools5[Write, Bash]
    IntTest --> Tools6[Write, Bash]
    Review --> Tools7[Read only]
    Gap --> Tools8[Read, Grep]
    Verify --> Tools9[Read, Bash]

    style Requirements fill:#9c27b0,color:#fff
    style Architecture fill:#9c27b0,color:#fff
    style Design fill:#2196f3,color:#fff
    style Implementation fill:#4caf50,color:#fff
    style UnitTest fill:#ff9800,color:#fff
    style IntTest fill:#ff9800,color:#fff
    style Review fill:#00bcd4,color:#fff
    style Gap fill:#f44336,color:#fff
    style Verify fill:#009688,color:#fff
```

## 5. Model Cost Optimization

```mermaid
graph LR
    Task[Task Complexity] --> Route{Routing Decision}

    Route -->|Simple<br/>Quick checks| Haiku[Haiku<br/>Fastest, Cheapest]
    Route -->|Standard<br/>Implementation| Sonnet[Sonnet<br/>Balanced]
    Route -->|Complex<br/>Architecture| Opus[Opus<br/>Most Capable]

    Haiku --> H1[gap-detector<br/>for quick scans]
    Haiku --> H2[reviewer<br/>for style checks]

    Sonnet --> S1[executor<br/>implementation]
    Sonnet --> S2[tester<br/>test writing]
    Sonnet --> S3[verifier<br/>validation]
    Sonnet --> S4[pdca-iterator<br/>orchestration]

    Opus --> O1[analyst<br/>requirements]
    Opus --> O2[architect<br/>design]
    Opus --> O3[gap-detector<br/>deep analysis]

    style Haiku fill:#4caf50,color:#fff
    style Sonnet fill:#2196f3,color:#fff
    style Opus fill:#9c27b0,color:#fff
```

## 6. MCP Server Integration

```mermaid
sequenceDiagram
    participant User
    participant Hook as Blueprint Hook
    participant MCP as MCP Server
    participant State as State Files
    participant Agent

    User->>Hook: Query Status
    Hook->>MCP: pdca_status(cycle_id)

    activate MCP
    MCP->>State: Read State File
    State-->>MCP: Cycle State
    MCP->>MCP: Format Response
    MCP-->>Hook: Status Report
    deactivate MCP

    Hook-->>User: Display Status

    User->>Hook: Measure Gap
    Hook->>MCP: gap_measure(gap_id)

    activate MCP
    MCP->>State: Read Gap State
    State-->>MCP: Gap Data
    MCP->>MCP: Calculate Metrics
    MCP-->>Hook: Gap Metrics
    deactivate MCP

    Hook-->>User: Display Metrics

    User->>Hook: Check Pipeline
    Hook->>MCP: pipeline_progress(pipeline_id)

    activate MCP
    MCP->>State: Read Pipeline State
    State-->>MCP: Pipeline Data
    MCP->>MCP: Compute Progress
    MCP-->>Hook: Progress Report
    deactivate MCP

    Hook-->>User: Display Progress

    Note over User,Agent: MCP = Read-only external access to state
```

## 7. Agent Dependency Graph

```mermaid
graph TD
    Start[Workflow Start] --> A1[analyst]

    A1 --> A2[architect]
    A2 --> A3[design-writer]

    A3 --> Branch{Parallel Execution}

    Branch --> E1[executor - Module A]
    Branch --> E2[executor - Module B]
    Branch --> E3[executor - Module C]

    E1 --> T1[tester - Unit Tests]
    E2 --> T2[tester - Unit Tests]
    E3 --> T3[tester - Unit Tests]

    T1 --> Merge[Integration Point]
    T2 --> Merge
    T3 --> Merge

    Merge --> T4[tester - Integration Tests]

    T4 --> Review{Review Phase}

    Review --> R1[reviewer - Code Quality]
    Review --> R2[gap-detector - Gap Analysis]

    R1 --> Final[verifier]
    R2 --> Final

    Final --> End[Workflow Complete]

    style A1 fill:#9c27b0,color:#fff
    style A2 fill:#9c27b0,color:#fff
    style E1 fill:#4caf50,color:#fff
    style E2 fill:#4caf50,color:#fff
    style E3 fill:#4caf50,color:#fff
    style T1 fill:#ff9800,color:#fff
    style T2 fill:#ff9800,color:#fff
    style T3 fill:#ff9800,color:#fff
    style T4 fill:#ff9800,color:#fff
    style R1 fill:#2196f3,color:#fff
    style R2 fill:#f44336,color:#fff
    style Final fill:#009688,color:#fff
```

## 8. Agent Context Sharing

```mermaid
flowchart TD
    subgraph "Phase 1: Requirements"
        A1[analyst] --> Doc1[requirements.md]
    end

    subgraph "Phase 2: Architecture"
        A2[architect] --> Doc2[architecture.md]
        Doc1 -.->|Context| A2
    end

    subgraph "Phase 3: Design"
        A3[design-writer] --> Doc3[design.md]
        Doc1 -.->|Context| A3
        Doc2 -.->|Context| A3
    end

    subgraph "Phase 4: Implementation"
        A4[executor] --> Code[Source Code]
        Doc1 -.->|Context| A4
        Doc2 -.->|Context| A4
        Doc3 -.->|Context| A4
    end

    subgraph "Phase 5: Testing"
        A5[tester] --> Tests[Test Files]
        Code -.->|Context| A5
        Doc3 -.->|Context| A5
    end

    subgraph "Phase 6: Review"
        A6[reviewer] --> Review[Review Report]
        Code -.->|Context| A6
        Tests -.->|Context| A6
        Doc1 -.->|Context| A6
    end

    subgraph "Phase 7: Verification"
        A7[verifier] --> Final[Verification Report]
        Code -.->|Context| A7
        Tests -.->|Context| A7
        Review -.->|Context| A7
    end

    style Doc1 fill:#e1bee7
    style Doc2 fill:#e1bee7
    style Doc3 fill:#e1bee7
    style Code fill:#c8e6c9
    style Tests fill:#ffecb3
    style Review fill:#b3e5fc
    style Final fill:#b2dfdb
```

## 9. Error Handling and Retries

```mermaid
stateDiagram-v2
    [*] --> AgentStart

    AgentStart --> Executing: Spawn Agent

    Executing --> Success: Task Complete
    Executing --> Failure: Error Occurred

    Failure --> Analyze: Check Error Type

    state Analyze <<choice>>
    Analyze --> Retry: Transient Error
    Analyze --> Skip: Non-Critical
    Analyze --> Abort: Critical Error

    Retry --> Executing: Attempt < Max
    Retry --> Abort: Attempt >= Max

    Success --> GateCheck: Validate Output

    state GateCheck <<choice>>
    GateCheck --> NextPhase: Pass
    GateCheck --> Retry: Fail (Retry < 3)
    GateCheck --> Abort: Fail (Retry >= 3)

    Skip --> PartialSuccess
    NextPhase --> [*]
    PartialSuccess --> [*]
    Abort --> [*]

    note right of Retry
        Max 3 retries per agent
        Exponential backoff
    end note

    note right of GateCheck
        Validates gate conditions:
        - Files exist
        - Tests pass
        - No errors
    end note
```

## 10. Agent Resource Usage

```mermaid
gantt
    title Agent Execution and Resource Usage
    dateFormat X
    axisFormat %M:%S

    section opus (High Cost)
    analyst           :0, 180s
    architect         :180, 270s
    gap-detector      :450, 120s

    section sonnet (Medium Cost)
    design-writer     :450, 150s
    executor Task 1   :600, 120s
    executor Task 2   :600, 120s
    executor Task 3   :600, 120s
    tester Unit       :720, 90s
    tester Integration:810, 90s
    reviewer          :900, 120s
    verifier          :1020, 60s
    pdca-iterator     :0, 1080s

    section Cost Optimization
    Parallel Execution :crit, 600, 720s

```

## 11. Orchestrator (pdca-iterator) Role

```mermaid
flowchart TD
    Iterator[pdca-iterator] --> Monitor{Monitor Cycle}

    Monitor --> Plan[Coordinate Plan Phase]
    Plan --> SpawnP[Spawn analyst]
    SpawnP --> WaitP[Wait for Completion]

    WaitP --> Do[Coordinate Do Phase]
    Do --> SpawnD[Spawn executor]
    SpawnD --> WaitD[Wait for Completion]

    WaitD --> Check[Coordinate Check Phase]
    Check --> SpawnC[Spawn verifier]
    SpawnC --> WaitC[Wait for Completion]

    WaitC --> Decide{Evaluate Results}

    Decide -->|Goals Met| Complete[Mark Complete]
    Decide -->|Continue| Act[Coordinate Act Phase]
    Decide -->|Failed| Fail[Mark Failed]

    Act --> Update[Update State]
    Update --> Monitor

    Complete --> Final[Generate Report]
    Fail --> Final
    Final --> End[End Cycle]

    style Iterator fill:#9c27b0,color:#fff
    style Decide fill:#ff9800,color:#fff
    style Complete fill:#4caf50,color:#fff
    style Fail fill:#f44336,color:#fff
```
