# Synod Modularization Summary

## Overview

The monolithic `synod.md` file (1,420 lines, cyclomatic complexity ~80) has been split into 8 focused modules for improved maintainability and comprehension.

## File Structure

### Main Entry Point
- **synod.md** (264 lines, -81% reduction)
  - Command argument parsing
  - Auto-classification trigger
  - Input validation
  - Module reference table
  - Execution flow summary
  - Mode-specific focus areas
  - CLI prerequisites
  - Quick reference

### Phase Modules
- **synod-phase0-setup.md** (265 lines)
  - Problem classification
  - Complexity and round count determination
  - Model configuration selection
  - Canary pre-sampling
  - Extended model options
  - Creativity configuration
  - Session initialization

- **synod-phase1-solver.md** (291 lines)
  - Prompt file preparation
  - Parallel model execution
  - Response validation
  - SID signal parsing
  - Early exit condition check

- **synod-phase2-critic.md** (246 lines)
  - Claude aggregation
  - Low confidence soft defer check
  - Gemini critic execution
  - OpenAI critic execution
  - Trust score calculation (CRIS rubric)

- **synod-phase3-defense.md** (164 lines)
  - Court role assignment
  - Defense target identification
  - Gemini defense execution
  - OpenAI prosecution execution
  - Claude judge deliberation

- **synod-phase4-synthesis.md** (172 lines)
  - Final evidence compilation
  - Confidence calculation
  - Mode-specific output generation (5 modes)
  - Decision rationale inclusion

### Support Modules
- **synod-error-handling.md** (133 lines)
  - Timeout fallback chains (all providers)
  - Format enforcement protocol
  - Low trust score fallback
  - API error handling
  - Graceful degradation strategy

- **synod-resume.md** (104 lines)
  - Session discovery
  - State restoration
  - Context loading
  - Execution continuation
  - Session cleanup

## Benefits

1. **Reduced Complexity**: Main file is now 264 lines (from 1,420)
2. **Clear Separation**: Each phase has dedicated documentation
3. **Cross-references**: Modules link to each other for navigation
4. **Inputs/Outputs**: Each module declares its contract
5. **Maintainability**: Changes to one phase don't affect others
6. **Discoverability**: Module reference table shows the big picture

## Module Contract Pattern

Each module file includes:
- **Header**: Module name and purpose
- **Inputs**: Required data from previous phases
- **Outputs**: Generated artifacts and state updates
- **Cross-references**: Links to calling and called modules

## Total Lines

- Original: 1,420 lines (monolithic)
- New: 1,737 lines (modular, +317 lines for documentation structure)
- Main entry: 264 lines (-81% from original)

The increase in total lines is due to:
- Module headers and metadata (8 files × ~20 lines)
- Explicit input/output declarations
- Cross-reference sections
- Improved documentation clarity

## Migration Notes

- All bash code blocks preserved exactly
- All prompt templates preserved exactly
- No functional changes, pure reorganization
- Backward compatibility maintained
