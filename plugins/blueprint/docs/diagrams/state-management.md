# State Management Architecture

## 1. State Directory Structure

```mermaid
graph TB
    Root[".blueprint/"] --> PDCA["pdca/"]
    Root --> Pipeline["pipeline/"]
    Root --> Gap["gap/"]
    Root --> Locks["locks/"]

    PDCA --> P1["cycle-{id}.json"]
    PDCA --> P2["cycle-{id}.json"]

    Pipeline --> PL1["pipeline-{id}.json"]
    Pipeline --> PL2["pipeline-{id}.json"]

    Gap --> G1["gap-{id}.json"]
    Gap --> G2["gap-{id}.json"]

    Locks --> L1["{workflow-id}.lock"]
    Locks --> L2["{workflow-id}.lock"]

    style Root fill:#1976d2,color:#fff
    style PDCA fill:#4caf50,color:#fff
    style Pipeline fill:#ff9800,color:#fff
    style Gap fill:#9c27b0,color:#fff
    style Locks fill:#f44336,color:#fff
```

## 2. State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: Initialize

    Created --> Active: Start Execution
    Active --> Active: Update Progress
    Active --> Paused: Hook:PreCompact
    Active --> Cancelled: /blueprint:cancel

    Paused --> Active: Hook:SessionStart
    Paused --> Cancelled: /blueprint:cancel

    Active --> Completed: Success
    Active --> Failed: Error/Gate Fail

    Cancelled --> [*]: Cleanup
    Completed --> [*]: Cleanup
    Failed --> [*]: Cleanup

    note right of Created
        cycle-{id}.json created
        Initial state saved
    end note

    note right of Active
        Progress tracked
        Iteration counters
    end note

    note right of Paused
        State preserved
        Session interrupted
    end note

    note right of Completed
        Final report
        Metrics recorded
    end note
```

## 3. Lock Protocol

```mermaid
sequenceDiagram
    participant Hook as Hook/Skill
    participant FS as File System
    participant State as State File

    Hook->>FS: Check Lock Exists

    alt Lock Exists
        FS-->>Hook: Lock Found
        Hook->>Hook: Wait 100ms
        Hook->>FS: Retry Check Lock
    else No Lock
        FS-->>Hook: No Lock
        Hook->>FS: Create Lock File
        FS-->>Hook: Lock Acquired

        Hook->>State: Read State
        State-->>Hook: Current State

        Hook->>Hook: Modify State

        Hook->>State: Write State
        State-->>Hook: Write Complete

        Hook->>FS: Delete Lock File
        FS-->>Hook: Lock Released
    end

    Note over Hook,State: Max 30 retries (3 seconds)
    Note over FS: Lock file: {workflow-id}.lock
```

## 4. State Schema - PDCA Cycle

```mermaid
classDiagram
    class PDCAState {
        +string id
        +string status
        +int current_iteration
        +int max_iterations
        +string goal
        +Timestamp created_at
        +Timestamp updated_at
        +Phase[] phases
        +Report[] reports
        +Metrics metrics
    }

    class Phase {
        +string name
        +string status
        +Timestamp started_at
        +Timestamp completed_at
        +string[] agents
        +Result result
    }

    class Report {
        +int iteration
        +string phase
        +string summary
        +Finding[] findings
        +Decision decision
    }

    class Metrics {
        +int files_changed
        +int lines_added
        +int lines_removed
        +int tests_added
        +float cycle_time_seconds
    }

    PDCAState "1" --> "4" Phase: plan/do/check/act
    PDCAState "1" --> "*" Report: iterations
    PDCAState "1" --> "1" Metrics: aggregated
```

## 5. State Schema - Pipeline

```mermaid
classDiagram
    class PipelineState {
        +string id
        +string preset
        +string status
        +string current_phase
        +string goal
        +Timestamp created_at
        +Timestamp updated_at
        +Stage[] stages
        +Context context
    }

    class Stage {
        +string name
        +int order
        +string status
        +Timestamp started_at
        +Timestamp completed_at
        +string agent
        +Gate gate
        +Artifact[] artifacts
    }

    class Gate {
        +string[] conditions
        +string status
        +string[] passed
        +string[] failed
        +int retry_count
    }

    class Context {
        +object requirements
        +object architecture
        +object design
        +string[] files_modified
    }

    PipelineState "1" --> "*" Stage: 3/6/9 stages
    Stage "1" --> "1" Gate: validation
    PipelineState "1" --> "1" Context: shared
```

## 6. State Schema - Gap Analysis

```mermaid
classDiagram
    class GapState {
        +string id
        +string status
        +string desired_state
        +Timestamp created_at
        +Timestamp completed_at
        +CurrentState current
        +Gap[] gaps
        +Recommendation[] recommendations
    }

    class CurrentState {
        +string summary
        +Finding[] findings
        +Metric[] metrics
    }

    class Gap {
        +string id
        +string severity
        +string category
        +string description
        +string current_value
        +string desired_value
        +float impact_score
    }

    class Recommendation {
        +string gap_id
        +string action
        +string priority
        +int estimated_effort
        +string[] dependencies
    }

    GapState "1" --> "1" CurrentState: analysis
    GapState "1" --> "*" Gap: identified
    GapState "1" --> "*" Recommendation: actionable
```

## 7. Concurrent State Access

```mermaid
flowchart TD
    T1[Thread 1: PDCA] --> Lock1{Try Lock}
    T2[Thread 2: Pipeline] --> Lock2{Try Lock}
    T3[Thread 3: Gap] --> Lock3{Try Lock}

    Lock1 -->|Success| Work1[Modify PDCA State]
    Lock2 -->|Success| Work2[Modify Pipeline State]
    Lock3 -->|Success| Work3[Modify Gap State]

    Lock1 -->|Fail| Wait1[Wait 100ms]
    Lock2 -->|Fail| Wait2[Wait 100ms]
    Lock3 -->|Fail| Wait3[Wait 100ms]

    Wait1 --> Lock1
    Wait2 --> Lock2
    Wait3 --> Lock3

    Work1 --> Release1[Release Lock]
    Work2 --> Release2[Release Lock]
    Work3 --> Release3[Release Lock]

    Release1 --> Done1[Done]
    Release2 --> Done2[Done]
    Release3 --> Done3[Done]

    style Lock1 fill:#4caf50,color:#fff
    style Lock2 fill:#2196f3,color:#fff
    style Lock3 fill:#ff9800,color:#fff
    style Work1 fill:#66bb6a,color:#fff
    style Work2 fill:#42a5f5,color:#fff
    style Work3 fill:#ffa726,color:#fff
```

## 8. Session Persistence

```mermaid
sequenceDiagram
    participant Session as Claude Session
    participant Hook as Hooks
    participant State as State Files

    Note over Session: Session Start
    Session->>Hook: SessionStart Event
    Hook->>State: Read All States
    State-->>Hook: Active Workflows
    Hook->>Session: Restore Context

    Note over Session: Work in Progress
    Session->>Hook: PostToolUse Event
    Hook->>State: Update Progress

    Note over Session: Memory Pressure
    Session->>Hook: PreCompact Event
    Hook->>State: Save Current State
    State-->>Hook: Persisted

    Note over Session: User Stops
    Session->>Hook: Stop Event
    Hook->>State: Mark Paused

    Note over Session: Session End
    Session->>Hook: SessionEnd Event
    Hook->>State: Final Cleanup
    State-->>Hook: Cleanup Complete
```

## 9. State Recovery Flow

```mermaid
flowchart TD
    Start[New Session] --> Check{Active States?}

    Check -->|Yes| Analyze[Analyze State]
    Check -->|No| Fresh[Fresh Start]

    Analyze --> Type{Workflow Type}

    Type -->|PDCA| PDCA_Check{Valid Iteration?}
    Type -->|Pipeline| Pipe_Check{Valid Phase?}
    Type -->|Gap| Gap_Check{Valid Analysis?}

    PDCA_Check -->|Yes| Resume_PDCA[Resume PDCA]
    PDCA_Check -->|No| Archive_PDCA[Archive & Start New]

    Pipe_Check -->|Yes| Resume_Pipe[Resume Pipeline]
    Pipe_Check -->|No| Archive_Pipe[Archive & Start New]

    Gap_Check -->|Yes| Resume_Gap[Resume Gap]
    Gap_Check -->|No| Archive_Gap[Archive & Start New]

    Resume_PDCA --> Notify[Notify User]
    Resume_Pipe --> Notify
    Resume_Gap --> Notify

    Archive_PDCA --> Fresh
    Archive_Pipe --> Fresh
    Archive_Gap --> Fresh

    Fresh --> Ready[Ready for New Command]
    Notify --> Ready

    style Resume_PDCA fill:#4caf50,color:#fff
    style Resume_Pipe fill:#2196f3,color:#fff
    style Resume_Gap fill:#ff9800,color:#fff
```

## 10. Cleanup Strategy

```mermaid
graph TB
    Cleanup[Cleanup Trigger] --> Age{Age Check}

    Age -->|> 7 days| Old[Mark Old]
    Age -->|< 7 days| Keep[Keep State]

    Old --> Status{Status Check}

    Status -->|completed| Archive[Move to Archive]
    Status -->|failed| Archive
    Status -->|cancelled| Archive
    Status -->|active| Keep
    Status -->|paused| Keep

    Archive --> Compress[Compress JSON]
    Compress --> Move[.blueprint/archive/]

    Keep --> Monitor[Continue Monitoring]

    Move --> Report[Log Cleanup]
    Monitor --> Next[Next Cleanup Cycle]

    style Archive fill:#ff9800,color:#fff
    style Keep fill:#4caf50,color:#fff
    style Move fill:#2196f3,color:#fff
```
