<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 -->

# Tools Directory - LLM Integration CLI Utilities

This directory contains standalone Python CLI utilities for integrating external LLM models (Google Gemini, OpenAI) with the Synod plugin framework. Each tool provides robust timeout handling, adaptive retry logic, and streaming support.

## Purpose

CLI utilities for querying multiple LLM providers with:
- Adaptive thinking/reasoning budgets that degrade on timeout
- Streaming mode to prevent response timeouts
- Robust error handling (timeout, rate limit, overloaded)
- SID signal parsing for response validation
- Trust score calculation for response credibility assessment

## Directory Structure

```
tools/
├── synod-parser.py        # Response parser & Trust Score calculator
├── gemini-3.py            # Google Gemini integration
├── openai-cli.py          # OpenAI integration
├── AGENTS.md              # This file
└── tests/                 # Unit tests (at project root)
    └── test_*.py
```

---

## Tool Reference

### synod-parser.py

**Purpose**: Parse SID (Synod ID) signals from model responses and calculate Trust Scores.

**Executable**: Yes (`chmod +x synod-parser.py`)

**Dependencies**:
- Python 3.7+ (no external packages required)
- Uses only stdlib: `sys`, `re`, `json`, `argparse`

**Modes of Operation**:

1. **Parse Response** (default)
   ```bash
   echo "response_text" | synod-parser
   synod-parser "response_text"
   ```
   Extracts:
   - Confidence block with score (0-100), evidence, logic, expertise, can_exit flag
   - Semantic focus points (key concepts)
   - Validation status
   - Derived metrics (can_exit_early, high_confidence)

2. **Format Validation**
   ```bash
   synod-parser --validate "response_text"
   ```
   Returns JSON with:
   - `has_confidence`: confidence block present
   - `has_score`: score attribute in confidence tag
   - `has_semantic_focus`: semantic_focus block present
   - `is_valid`: all required fields present

   Exit codes: 0 if valid, 1 if invalid

3. **Trust Score Calculation**
   ```bash
   synod-parser --trust C R I S
   ```
   Calculates: T = (C × R × I) / S, capped at 2.0
   - C: Credibility (0-1)
   - R: Reliability (0-1)
   - I: Intimacy (0-1)
   - S: Self-Orientation (0.1-1, minimum enforced)

   Returns JSON with trust_score and rating (high/good/acceptable/low)

**Output Format**: JSON (always)

**Error Handling**:
- Malformed responses: applies defaults, includes format_warning
- Missing semantic_focus: extracts key sentences as fallback
- Invalid format: returns validation details

**Key Functions**:
| Function | Purpose |
|----------|---------|
| `validate_format(text)` | Check required XML format |
| `extract_confidence(text)` | Parse confidence block |
| `extract_semantic_focus(text)` | Extract key concepts |
| `calculate_trust_score(c, r, i, s)` | Compute Trust Score |
| `parse_response(text)` | Full response parsing |

---

### gemini-3.py

**Purpose**: Query Google Gemini models with adaptive thinking budget and streaming support.

**Executable**: Yes (`chmod +x gemini-3.py`)

**Dependencies**:
- External: `google-genai>=1.0.0`
- Environment: `GEMINI_API_KEY`

**Models**:
| Alias | Full Name | Capability |
|-------|-----------|-----------|
| `flash` | gemini-3-flash-preview | Fast, cost-effective |
| `pro` | gemini-3-pro-preview | High quality reasoning |
| `2.5-flash` | gemini-2.5-flash | Latest fast model |
| `2.5-pro` | gemini-2.5-pro | Latest powerful model |

Default: `flash`

**Thinking Levels** (progressive downgrade on timeout):
| Level | Budget (tokens) | Use Case |
|-------|-----------------|----------|
| `minimal` | 50 | Quick questions |
| `low` | 200 | Simple tasks |
| `medium` | 500 | Balanced (default) |
| `high` | 2000 | Complex reasoning |
| `max` | 10000 | Maximum depth |

**Command-Line Interface**:

```bash
# Basic usage
echo "prompt" | gemini-3
gemini-3 "prompt"

# With options
gemini-3 --model pro --thinking high --temperature 0.7 "prompt"
gemini-3 -m flash -t medium "prompt"

# Advanced
gemini-3 --model 2.5-pro --thinking max --timeout 600 "prompt"
gemini-3 --no-stream --no-adaptive "prompt"
```

**Options**:
```
-m, --model          Model to use (flash|pro|2.5-flash|2.5-pro, default: flash)
-t, --thinking       Thinking level (minimal|low|medium|high|max, default: medium)
--timeout            Timeout in seconds (default: 300)
--no-stream          Disable streaming (not recommended for long responses)
--no-adaptive        Disable adaptive retry (thinking level downgrade)
--retries            Max retries (default: 3)
--temperature        Generation temperature (default: 0.7, range: 0-2)
-v, --verbose        Verbose output to stderr
```

**Streaming Behavior**:
- Enabled by default: prevents timeout on long responses
- Chunks streamed to stdout in real-time
- Automatically reassembles full response
- Disable with `--no-stream` (not recommended)

**Adaptive Retry Strategy**:

1. Initial attempt with specified thinking level
2. On timeout/overload: downgrade thinking level progressively
   - `high` → `medium` → `low` → `minimal`
3. Exponential backoff: 1s, 2s, 4s (2^n seconds)
4. Rate limit: longer backoff (2^(n+2) seconds)

Example flow:
```
Attempt 1: thinking=high, timeout → downgrade
Attempt 2: thinking=medium, timeout → downgrade
Attempt 3: thinking=low, success → return response
```

**Exit Codes**:
- 0: Success
- 1: Error (non-retryable, max retries exceeded)

**Retryable Errors**:
- Timeout (includes "timeout", "504", "gateway", "deadline")
- Overloaded (includes "503", "overloaded", "unavailable")
- Rate limited (includes "429", "rate", "quota", "resource_exhausted")

---

### openai-cli.py

**Purpose**: Query OpenAI models with reasoning effort and adaptive retry support.

**Executable**: Yes (`chmod +x openai-cli.py`)

**Dependencies**:
- External: `openai>=1.0.0`, `httpx>=0.24.0`
- Environment: `OPENAI_API_KEY`

**Models**:
| Alias | Full ID | Best For | Cost |
|-------|---------|----------|------|
| `gpt4o` | gpt-4o | General tasks, fast | $2.50-$10 per 1M |
| `o3` | o3 | Math, logic, reasoning | $10-$40 per 1M |
| `o4mini` | o4-mini | Economic reasoning | Lower cost |

Default: `gpt4o`

**Reasoning Levels** (o-series models only):
| Level | Use Case |
|-------|----------|
| `low` | Speed priority, economical |
| `medium` | Balanced (default) |
| `high` | Maximum reasoning depth |

Note: gpt4o ignores reasoning_effort parameter

**Command-Line Interface**:

```bash
# Basic usage
echo "prompt" | openai-cli
openai-cli "prompt"

# With options
openai-cli --model o3 --reasoning high "prompt"
openai-cli -m o4mini -r medium "prompt"

# Alternative syntax
openai-cli --prompt "prompt" --model o3
```

**Options**:
```
prompt                 Prompt text (positional or --prompt)
-p, --prompt          Prompt text (named option)
-m, --model           Model (gpt4o|o3|o4mini, default: gpt4o)
-r, --reasoning       Reasoning level (low|medium|high, default: medium)
--timeout             Timeout in seconds (defaults per model/level)
--retries             Max retries (default: 3)
--no-adaptive         Disable adaptive reasoning downgrade
-v, --verbose         Verbose output to stderr
```

**Model-Specific Timeouts** (automatic):
```
gpt4o:   60s   (all reasoning levels)
o3:      120s  (low) → 180s (medium) → 300s (high)
o4mini:  60s   (low) → 90s  (medium) → 120s (high)
```

**Prompt Input Priority**:
1. stdin (if piped)
2. `--prompt` argument
3. positional argument
4. remaining unparsed arguments

**Adaptive Retry Strategy**:

1. Initial attempt with specified reasoning level
2. On timeout/overload: downgrade reasoning level
   - `high` → `medium` → `low`
3. Exponential backoff with jitter: (2^n) + random()
4. Rate limit: longer backoff (2^(n+2)) + random()

Example flow:
```
Attempt 1: reasoning=high, timeout → downgrade
Attempt 2: reasoning=medium, timeout → downgrade
Attempt 3: reasoning=low, success → return response
```

Only o-series models support reasoning downgrade. gpt4o retries without downgrade.

**Exit Codes**:
- 0: Success
- 1: Error (non-retryable, max retries exceeded)

**Retryable Errors**:
- Timeout (includes "timeout", "timed out", "deadline")
- Overloaded (includes "503", "overloaded", "unavailable", "502")
- Rate limited (includes "429", "rate", "quota")

---

## For AI Agents Working In This Directory

### Tool Selection Guide

| Task | Tool | Example |
|------|------|---------|
| Parse response from Gemini | synod-parser | `gemini-3 "prompt" \| synod-parser` |
| Query Gemini fast | gemini-3 -m flash | `gemini-3 -m flash "prompt"` |
| Query Gemini with reasoning | gemini-3 -m pro -t high | `gemini-3 -m pro -t high "prompt"` |
| Query OpenAI general | openai-cli -m gpt4o | `openai-cli -m gpt4o "prompt"` |
| Query OpenAI reasoning | openai-cli -m o3 -r high | `openai-cli -m o3 -r high "prompt"` |
| Validate response format | synod-parser --validate | `synod-parser --validate "response"` |
| Calculate Trust Score | synod-parser --trust | `synod-parser --trust 0.9 0.8 0.9 0.2` |

### Common Patterns

**Pattern 1: Query → Parse → Trust**
```bash
response=$(gemini-3 --model pro --thinking high "Complex analysis")
parsed=$(echo "$response" | synod-parser)
trust=$(echo "$parsed" | jq '.confidence.score')
```

**Pattern 2: Progressive Model Upgrade**
```bash
# Start fast, upgrade if needed
response=$(gemini-3 --model flash "simple question")
if ! echo "$response" | synod-parser --validate; then
    response=$(gemini-3 --model pro --thinking high "simple question")
fi
```

**Pattern 3: Timeout Resilience**
```bash
# Streaming prevents timeout on long responses
gemini-3 --model pro --thinking max --no-adaptive "long analysis"
# Without --no-adaptive, will downgrade thinking if timeout occurs
```

**Pattern 4: Cost-Effective OpenAI**
```bash
# Use o4mini for economical reasoning
openai-cli --model o4mini --reasoning medium "standard question"
```

**Pattern 5: Reliable Retry**
```bash
# Manual retry with exponential backoff
for i in {1..3}; do
    openai-cli --model o3 --reasoning high "prompt" && break
    sleep $((2 ** i))
done
```

### Integration Points

**With Synod Plugin**:
```bash
# Propose changes using Gemini reasoning
proposal=$(gemini-3 --model pro --thinking high --temperature 0.1 \
    "Analyze: $code_context")
confidence=$(echo "$proposal" | synod-parser | jq '.confidence.score')
```

**With External Scripts**:
```bash
#!/bin/bash
# script.sh using tools directory

TOOLS_DIR="$(dirname "$0")/tools"

# Make tools executable
chmod +x "$TOOLS_DIR"/*.py

# Use tools
response=$("$TOOLS_DIR/gemini-3.py" --model flash "prompt")
parsed=$("$TOOLS_DIR/synod-parser.py" <<< "$response")
```

---

## Usage Examples

### Gemini Examples

```bash
# Basic query
gemini-3 "What is quantum computing?"

# With medium thinking
gemini-3 --model pro --thinking medium "Explain neural networks"

# Long response with streaming
gemini-3 --model pro --thinking high --temperature 0.5 \
    "Write detailed analysis of..."

# Disable adaptive retry (keep high thinking even on timeout)
gemini-3 --no-adaptive --model pro --thinking high "prompt"

# Verbose output
gemini-3 -v --model 2.5-pro --thinking max "prompt"

# From stdin
echo "2 + 2 = ?" | gemini-3 --model flash

# Multiple arguments
gemini-3 --model pro --temperature 0.3 "prompt" "additional context"
```

### OpenAI Examples

```bash
# Basic query with gpt4o
openai-cli "What is machine learning?"

# Reasoning with o3
openai-cli --model o3 --reasoning high \
    "Prove that sqrt(2) is irrational"

# Economic reasoning with o4mini
openai-cli --model o4mini --reasoning medium "quick analysis"

# From stdin
echo "한국의 수도는?" | openai-cli --model gpt4o

# Verbose output
openai-cli -v --model o3 --reasoning high "prompt"

# Custom timeout
openai-cli --model o3 --timeout 600 "long task"

# No adaptive downgrade (try high reasoning once)
openai-cli --no-adaptive --model o3 --reasoning high "prompt"
```

### Parser Examples

```bash
# Parse response
echo '<confidence score="85"><evidence>...</evidence></confidence>
       <semantic_focus>Point 1\nPoint 2</semantic_focus>' | synod-parser

# Validate format only
synod-parser --validate "response text"

# Calculate Trust Score
synod-parser --trust 0.9 0.85 0.88 0.2
# Output: {credibility: 0.9, reliability: 0.85, intimacy: 0.88,
#          self_orientation: 0.2, trust_score: 3.4, rating: "high"}

# Parse with pipe
gemini-3 "prompt" | synod-parser | jq '.confidence.score'
```

---

## Testing Requirements

### Test Structure

Tests are located at project root: `/Users/ahnjundaram_g/dev/tools/synod-plugin/tests/`

```
tests/
├── test_synod_parser.py
├── test_gemini_integration.py
├── test_openai_integration.py
├── fixtures/
│   ├── sample_responses.json
│   └── malformed_responses.json
└── conftest.py  # shared fixtures
```

### Test Categories

**Unit Tests**:
- Format validation (valid/invalid XML)
- Parsing (extract confidence, semantic focus)
- Trust score calculation
- Error handling (malformed input, missing fields)
- Exit codes (0 for success, 1 for error)

**Integration Tests**:
- Timeout handling (mock slow API responses)
- Adaptive retry (verify thinking/reasoning downgrade)
- Streaming (verify chunk assembly)
- Error scenarios (rate limit, overload, timeout)
- API key validation

**Edge Cases**:
- Empty responses
- Malformed XML
- Missing confidence block
- Missing semantic_focus (fallback to key sentences)
- Timeout with retries exhausted
- Rate limit with exponential backoff

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_synod_parser.py -v

# With coverage
pytest tests/ --cov=tools --cov-report=html

# Integration tests only (requires API keys)
pytest tests/test_gemini_integration.py --integration

# Mock/unit tests only
pytest tests/test_gemini_integration.py -m "not integration"
```

### Test Fixtures

**Mock API Responses**:
```json
{
  "valid_confidence": {
    "response": "<confidence score=\"85\"><evidence>...</evidence></confidence>",
    "expected_score": 85
  },
  "timeout_error": {
    "error": "504 Gateway Timeout",
    "retry_expected": true
  }
}
```

### Timeout Testing

```python
# Mock a slow API response
import time
from unittest.mock import patch

def test_timeout_triggers_downgrade():
    with patch('gemini_3.generate_with_retry') as mock:
        mock.side_effect = TimeoutError("deadline exceeded")
        # Verify thinking level downgraded from high to medium
```

### POSIX Compliance

Tools must work on macOS/Linux with POSIX sed/grep:
```bash
# ✓ Use: sed -E (extended regex)
# ✗ Avoid: sed -r (GNU only)

# ✓ Use: grep -E (extended regex)
# ✗ Avoid: grep -P (Perl regex, GNU only)
```

---

## Dependencies

### External Packages

| Package | Version | Used By | Installation |
|---------|---------|---------|--------------|
| google-genai | >=1.0.0 | gemini-3.py | `pip install google-genai` |
| openai | >=1.0.0 | openai-cli.py | `pip install openai` |
| httpx | >=0.24.0 | openai-cli.py | `pip install httpx` |

### Environment Variables

| Variable | Required | Used By | Example |
|----------|----------|---------|---------|
| GEMINI_API_KEY | Yes | gemini-3.py | `export GEMINI_API_KEY="..."` |
| OPENAI_API_KEY | Yes | openai-cli.py | `export OPENAI_API_KEY="..."` |

### Python Version

- Minimum: Python 3.7
- Tested: Python 3.9, 3.10, 3.11, 3.12
- Recommended: Python 3.11+

---

## Error Handling Reference

### Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Response generated and printed |
| 1 | Error | API error, max retries exceeded, missing API key |
| 124 | Timeout | Command timeout (rare, handled by adaptive retry) |

### Common Errors

**GEMINI_API_KEY not set**
```
Error: GEMINI_API_KEY environment variable not set
```
Fix: `export GEMINI_API_KEY="your_key"`

**OpenAI package not installed**
```
Error: openai 패키지가 설치되지 않았습니다.
설치: pip install openai
```
Fix: `pip install openai httpx`

**Timeout after retries**
```
Error: Max retries (3) exceeded
```
- Increase `--retries` to 5
- Try `--no-adaptive` to keep higher thinking
- Check network connectivity

**Rate Limited**
```
[Retry 1/3] Rate limited - waiting 4.5s
```
- Automatic: exponential backoff
- Manual: decrease `--retries` or use `--no-adaptive`

**Empty Response**
```
Error: Empty response
```
- Model returned null
- Increase thinking/reasoning level
- Try different model

---

## Security Considerations

### API Key Handling

- Keys loaded from environment variables only
- Never logged to stdout (only to stderr for errors)
- Keys should have appropriate rate limits and scopes

### Input Validation

- Prompts passed directly to API (no sanitization)
- Responses parsed as JSON (safe from injection)
- XML validation in synod-parser uses regex (safe)

### Network Security

- HTTPS enforced by SDK libraries
- Custom timeouts prevent hanging connections
- Backoff prevents API hammering

---

## Troubleshooting

### Tools not executable
```bash
chmod +x /Users/ahnjundaram_g/dev/tools/synod-plugin/tools/*.py
```

### Import errors in scripts
```bash
# Verify tools are in PATH or use full path
/Users/ahnjundaram_g/dev/tools/synod-plugin/tools/gemini-3.py "prompt"

# Or make symlinks
ln -s /Users/ahnjundaram_g/dev/tools/synod-plugin/tools/*.py /usr/local/bin/
```

### Streaming issues
```bash
# If output appears incomplete:
gemini-3 --no-stream "prompt"  # Disable streaming

# If streaming hangs:
gemini-3 --timeout 120 "prompt"  # Increase timeout
```

### Adaptive retry not triggering
```bash
# Check if model/reasoning supports downgrade:
# - gemini-3: high→medium→low→minimal works
# - openai o-series: high→medium→low works
# - openai gpt4o: no downgrade (already optimized)

# Force downgrade behavior:
gemini-3 --no-adaptive "prompt"  # Disable to see original error
```

---

## Roadmap & Future

**Planned Features**:
- Caching layer for repeated prompts
- Batch processing (multiple prompts from file)
- Output format options (JSON, YAML, markdown)
- Custom retry strategies
- Webhook integration for long-running tasks

**Deprecation Notice**:
- gemini-2 models (use 2.5-flash instead)
- gpt-4-turbo (use gpt-4o instead)

---

**Last Updated**: 2026-01-31
**Status**: Stable
**Maintainer**: Synod Plugin Team
