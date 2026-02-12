# Architecture Diagrams

This directory contains comprehensive Mermaid diagrams documenting the architecture and workflows of claude-blueprint-helix.

## 📚 Diagram Files

### 1. [Blueprint + OMC Workflow](blueprint-omc-workflow.md)

Core integration patterns between Blueprint (strategic layer) and OMC (tactical layer):

- **B-O-B-O Cycle** - The fundamental Blueprint→OMC→Blueprint→OMC iteration pattern
- **PDCA Cycle Integration** - How Plan-Do-Check-Act maps to Blueprint and OMC commands
- **Complexity-Based Routing** - Decision tree for choosing the right workflow (direct OMC, standard, or full pipeline)
- **Layer Responsibility Matrix** - Clear separation of concerns between strategic and tactical layers
- **Feature Overlap Resolution** - How to handle overlapping features (pipeline, planning, cancellation)
- **Anti-Patterns** - Common mistakes to avoid
- **Cheat Sheet** - Quick reference for the 8 essential commands

### 2. [Skill Orchestration](skill-orchestration.md)

How skills invoke agents and manage workflows:

- **Skill Invocation Lifecycle** - From user command to completion
- **Pipeline Stage Progression** - Full/Standard/Minimal preset flows
- **Agent Selection and Execution** - Routing phases to appropriate agents
- **Hook Integration Flow** - How hooks intercept and enhance workflows
- **Parallel Agent Execution** - Timeline visualization of concurrent operations
- **Cancel/Cleanup Flow** - Graceful termination and resource cleanup
- **Multi-Cycle Concurrency** - Multiple workflows running simultaneously

### 3. [State Management](state-management.md)

Persistent state architecture and data flows:

- **State Directory Structure** - `.blueprint/` organization
- **State Lifecycle** - From creation through completion/cancellation
- **Lock Protocol** - Race condition prevention mechanism
- **State Schema - PDCA Cycle** - Data model for PDCA workflows
- **State Schema - Pipeline** - Data model for pipeline workflows
- **State Schema - Gap Analysis** - Data model for gap analysis
- **Concurrent State Access** - Multi-threaded safety patterns
- **Session Persistence** - Hook-based state preservation
- **State Recovery Flow** - Resuming interrupted workflows
- **Cleanup Strategy** - Archival and retention policies

### 4. [Agent Interactions](agent-interactions.md)

Agent catalog and communication patterns:

- **Agent Catalog Overview** - 9 specialized agents (analyst, architect, executor, etc.)
- **Agent Communication Pattern** - Sequence of agent invocations
- **Read-Only vs Write Agents** - Permission boundaries
- **Agent Selection by Phase** - Which agents handle which pipeline phases
- **Model Cost Optimization** - Haiku/Sonnet/Opus routing strategy
- **MCP Server Integration** - External tool access patterns
- **Agent Dependency Graph** - Execution order and parallelization
- **Agent Context Sharing** - How context flows between phases
- **Error Handling and Retries** - Fault tolerance mechanisms
- **Agent Resource Usage** - Cost and time optimization
- **Orchestrator Role** - How pdca-iterator coordinates cycles

## 🎯 Quick Navigation

### By Use Case

**Understanding the System**
- Start with [Blueprint + OMC Workflow](blueprint-omc-workflow.md) for the big picture
- Then read [Skill Orchestration](skill-orchestration.md) for workflow mechanics

**Developing Features**
- Check [Agent Interactions](agent-interactions.md) for agent selection
- Reference [State Management](state-management.md) for persistence patterns

**Debugging Issues**
- [State Management](state-management.md) - State file corruption, lock issues
- [Skill Orchestration](skill-orchestration.md) - Hook problems, cancellation
- [Agent Interactions](agent-interactions.md) - Agent failures, retries

**Optimizing Performance**
- [Agent Interactions](agent-interactions.md) - Model selection, parallelization
- [Skill Orchestration](skill-orchestration.md) - Preset selection

### By Concept

| Concept | Primary Diagram | Secondary Diagram |
|---------|----------------|-------------------|
| **B-O-B-O Cycle** | [blueprint-omc-workflow.md](blueprint-omc-workflow.md) | [skill-orchestration.md](skill-orchestration.md) |
| **PDCA Iterations** | [blueprint-omc-workflow.md](blueprint-omc-workflow.md) | [state-management.md](state-management.md) |
| **Pipeline Stages** | [skill-orchestration.md](skill-orchestration.md) | [agent-interactions.md](agent-interactions.md) |
| **Agent Catalog** | [agent-interactions.md](agent-interactions.md) | [skill-orchestration.md](skill-orchestration.md) |
| **State Files** | [state-management.md](state-management.md) | [skill-orchestration.md](skill-orchestration.md) |
| **Lock Protocol** | [state-management.md](state-management.md) | - |
| **Hooks** | [skill-orchestration.md](skill-orchestration.md) | [state-management.md](state-management.md) |
| **MCP Server** | [agent-interactions.md](agent-interactions.md) | - |

## 📖 Reading Order

### For New Users

1. **[Blueprint + OMC Workflow](blueprint-omc-workflow.md)** - Understand the strategic/tactical split
2. **[Skill Orchestration](skill-orchestration.md)** - Learn how to invoke workflows
3. **[Agent Interactions](agent-interactions.md)** - See which agents do what
4. **[State Management](state-management.md)** - Understand persistence (optional)

### For Contributors

1. **[State Management](state-management.md)** - Critical for understanding file formats
2. **[Skill Orchestration](skill-orchestration.md)** - How hooks and skills work together
3. **[Agent Interactions](agent-interactions.md)** - Agent communication protocols
4. **[Blueprint + OMC Workflow](blueprint-omc-workflow.md)** - Design philosophy

### For Troubleshooters

1. **[State Management](state-management.md)** - Debug state corruption
2. **[Skill Orchestration](skill-orchestration.md)** - Trace workflow execution
3. **[Agent Interactions](agent-interactions.md)** - Diagnose agent failures

## 🔧 Diagram Conventions

### Color Coding

- **Blue (`#1976d2`, `#e1f5ff`)** - Blueprint layer, strategic components
- **Orange (`#f57c00`, `#fff3e0`)** - OMC layer, tactical components
- **Green (`#4caf50`)** - Success states, write operations, execution
- **Red (`#f44336`)** - Failure states, errors, locks
- **Purple (`#9c27b0`)** - Analysis, high-level operations (opus model)
- **Cyan (`#00bcd4`)** - Review, verification operations
- **Yellow (`#ff9800`)** - Warnings, intermediate states, pipelines

### Node Shapes

- **Rectangle** - Process, agent, component
- **Diamond** - Decision point, conditional branch
- **Rounded Rectangle** - State, status
- **Circle** - Start/end point
- **Cylinder** - Data storage, state files

### Arrow Types

- **Solid Arrow (`-->`)** - Direct control flow, execution order
- **Dotted Arrow (`-.->`)** - Data flow, context passing
- **Thick Arrow** - High-importance flow

## 📝 Maintenance Notes

These diagrams are manually maintained. When updating:

1. **Keep synchronized** - Changes to one diagram may require updates to related diagrams
2. **Test rendering** - Preview Mermaid syntax on GitHub or with a Mermaid viewer
3. **Update this index** - Add new diagrams to the navigation sections
4. **Cross-reference** - Link between related diagrams for easy navigation

## 🔗 Related Documentation

- [Main README](../../README.md) - Overview and quick start
- [Korean README](../../README.ko.md) - 한국어 문서
- [CHANGELOG](../../CHANGELOG.md) - Version history
- [Agent Definitions](../../agents/) - Agent prompt files
- [Skill Definitions](../../skills/) - Skill implementation files

---

**Legend**: 📚 Content | 🎯 Navigation | 📖 Learning Paths | 🔧 Conventions | 📝 Maintenance | 🔗 Links
