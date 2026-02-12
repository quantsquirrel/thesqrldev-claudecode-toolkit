# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Extended debate modes (5+ round deliberation for complex architectural decisions)
- Custom model configuration per session (not just global defaults)
- Debate visualization dashboard showing confidence trajectories
- Integration with Claude Code's native analysis capabilities
- Batch processing for multiple problems in sequence
- Export debates to markdown reports with embedded confidence metrics

---

## [1.0.0] - 2026-01-31

### Added

#### Core Deliberation System
- **3-round structured debate framework**: Solver → Critic → Defense/Prosecution with full court-style arbitration
- **Multi-agent coordination**: Parallel execution of Claude (Validator), Gemini, and OpenAI models with intelligent fallback chains
- **SID (Self-Signals Driven) confidence scoring**: 0-100 scale with semantic focus anchoring (primary, secondary, tertiary claims)
- **CortexDebate Trust Score calculation**: Formula-based trust assessment = min((C×R×I)/S, 2.0)
  - Credibility (evidence quality)
  - Reliability (logical consistency)
  - Intimacy (problem relevance)
  - Self-Orientation (bias detection)

#### Specialized Modes
- **review mode**: Code review and analysis with severity levels (ERROR, WARNING, INFO)
- **design mode**: Architecture and system design with trade-off analysis
- **debug mode**: Root cause analysis with evidence chains and prevention strategies
- **idea mode**: Brainstorming with ranked ideas and feasibility assessment
- **general mode**: Balanced question answering with comprehensive coverage

#### Anti-Conformity & Debate Quality
- **Free-MAD methodology**: Explicit anti-conformity instructions preventing premature consensus
- **Soft defer mechanism (ConfMAD)**: Preserved low-confidence perspectives instead of forcing agreement
- **Adversarial roles**: Defense lawyer vs. prosecutor model enforcing balanced argumentation
- **ReConcile convergence pattern**: 3-round structured agreement resolution process

#### Session Management
- **Full session persistence**: Complete debate history stored in structured directories
- **Session resume capability**: Continue interrupted debates from any checkpoint
- **Session state tracking**: Current round, completion status, and resume points
- **Configurable session directory**: `SYNOD_SESSION_DIR` environment variable support
- **Session metadata**: Mode, problem type, complexity classification, and model configuration

#### Robustness & Error Handling
- **Timeout fallback chains**: Graceful degradation with 110-second internal timeouts and automatic retry logic
- **Format enforcement protocol**: Re-prompting for malformed responses with XML validation
- **Low trust score fallback**: Prevents exclusion of all agents even when confidence is universally low
- **API error handling**: Rate limit detection, authentication error handling, and cached response fallback
- **Parser redundancy**: Inline fallback parser activates if external `synod-parser` unavailable

#### CLI Tools
- **synod-parser.py**: SID signal extraction, XML validation, and Trust Score calculation
  - Validates response format compliance
  - Extracts confidence scores and semantic focus
  - Calculates CortexDebate Trust Scores
  - Applies intelligent defaults for malformed responses

- **gemini-3.py**: Google Gemini API integration with adaptive thinking
  - Support for Gemini Flash and Gemini Pro models
  - Configurable thinking effort (low/medium/high)
  - Adaptive temperature control (0.5-0.7 per persona)
  - Automatic timeout retry with exponential backoff

- **openai-cli.py**: OpenAI integration with advanced reasoning support
  - Support for GPT-4o and o3 models (o3 for complex reasoning)
  - Reasoning effort levels (medium/high) for o3
  - Fallback models for degraded operations
  - Temperature configuration for gpt4o (o3 maintains fixed 1.0)

#### Benchmark Suite
- **GSM8K benchmark**: Math reasoning evaluation dataset
- **Baseline implementations**: Reference implementations for model comparison
- **Evaluator framework**: Structured evaluation metrics and result aggregation
- **Analysis tools**: Statistical analysis and confidence metrics reporting

#### Configuration System
- **Environment variables**: API keys, session directory, and retention policies
- **Mode-specific model selection**: Different models for each mode (Flash for review/debug, Pro for design/idea)
- **Temperature configuration per persona**: Solver (0.7), Critic (0.5), different models for different roles
- **Custom model override**: Optional `.claude/synod-config.json` for per-user customization

#### Output & Reporting
- **Mode-specific output formatting**: Tailored results for review, design, debug, idea, and general modes
- **Confidence-weighted synthesis**: Final conclusions weighted by Trust Scores
- **Decision rationale collapsible section**: Shows deliberation process with model contributions
- **XML-based structured output**: Confidence blocks with evidence, logic, and expertise annotations

### Technical Foundation

- **Multi-model orchestration**: Parallel execution with intelligent coordination and state management
- **Deterministic session IDs**: `synod-YYYYMMDD-HHMMSS-xxx` format for easy identification and resume
- **Structured session directories**: Organized round-by-round response storage with JSON state tracking
- **POSIX-compatible tooling**: macOS and Linux support with bash fallbacks for all utilities
- **Stdin/stdout piping**: Native Claude Code integration with streaming support

### Documentation

- **Comprehensive README**: Installation, usage, configuration, and troubleshooting guides
- **Skill definitions**: `/synod` command with full argument documentation
- **Error reference**: Common issues and solutions with diagnostic hints
- **Theoretical foundation**: Research citations and methodology explanations
- **API documentation**: Detailed response format specifications with examples

### Dependencies

- Python 3.9+ (for CLI tools and benchmarking)
- System utilities: `jq`, `openssl`, `bash`
- API credentials: `GEMINI_API_KEY`, `OPENAI_API_KEY`
- Claude Code: v1.0.0 or later

### Known Limitations

- Debate duration: Typically 2-5 minutes per 3-round session
- Token usage: ~5,000-15,000 tokens per debate (varies by prompt length)
- API timeouts: 110-second internal limits with automatic retry and degradation
- Model selection: Limited to Gemini (Flash/Pro) and OpenAI (GPT-4o/o3) models

---

## How to Report Issues

For bug reports, feature requests, or discussions:
- **Issues**: https://github.com/quantsquirrel/claude-synod-debate/issues
- **Discussions**: https://github.com/quantsquirrel/claude-synod-debate/discussions
- **Repository**: https://github.com/quantsquirrel/claude-synod-debate

## Upgrade Guide

### Installing v1.0.0

#### Via Plugin (Recommended)
```bash
/plugin install quantsquirrel/claude-synod-debate
```

#### Manual Installation
```bash
git clone https://github.com/quantsquirrel/claude-synod-debate.git
cd synod
pip install -r requirements.txt
cp skills/*.md ~/.claude/commands/
chmod +x tools/*.py
export PATH="$PATH:$(pwd)/tools"
```

#### Environment Setup
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export SYNOD_SESSION_DIR="~/.synod/sessions"  # Optional, defaults shown
```

### Quick Start
```bash
# Code review with multi-agent debate
/synod review Analyze the performance of this function

# Architecture design discussion
/synod design Design a JWT authentication system

# Debugging with cross-model analysis
/synod debug Why is this test failing?

# Brainstorming with idea evaluation
/synod idea How can we improve user onboarding?

# Resume interrupted debate
/synod resume

# General question with balanced perspective
/synod How should we approach this problem?
```

---

[Unreleased]: https://github.com/quantsquirrel/claude-synod-debate/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/quantsquirrel/claude-synod-debate/releases/tag/v1.0.0
