<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-01 -->

# Tests Directory - Synod Plugin Test Suite

This directory contains the comprehensive test suite for synod-plugin, covering all CLI tools with unit tests, mock fixtures, and CI/CD integration.

## Purpose

Automated testing for the Synod multi-agent deliberation system:
- Unit tests for parser, Gemini, and OpenAI CLI tools
- Mock fixtures for API key isolation
- No external API calls required
- pytest-based test framework with coverage reporting

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared pytest fixtures (mock API keys, sample data)
├── test_synod_parser.py     # synod-parser.py tests (36 test cases)
├── test_gemini.py           # gemini-3.py tests (14 test cases)
├── test_openai_cli.py       # openai-cli.py tests (13 test cases)
├── README.md                # Test documentation (Korean)
└── AGENTS.md                # This file
```

## Key Files

| File | Description |
|------|-------------|
| `conftest.py` | Shared fixtures: mock API keys, sample valid/invalid/partial responses |
| `test_synod_parser.py` | XML validation, confidence extraction, Trust Score calculation |
| `test_gemini.py` | Model mapping, thinking budgets, error detection, retry logic |
| `test_openai_cli.py` | Model mapping, O-series detection, timeout strategy, reasoning levels |

## For AI Agents

### Running Tests

```bash
# Full test suite
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=tools --cov-report=html

# Specific test file
pytest tests/test_synod_parser.py -v

# Specific test class
pytest tests/test_synod_parser.py::TestCalculateTrustScore -v

# Specific test case
pytest tests/test_synod_parser.py::TestCalculateTrustScore::test_perfect_trust -v
```

### Working In This Directory

- **No API keys required**: All tests use mock fixtures from `conftest.py`
- **No external calls**: Tests focus on configuration, validation, and logic
- **TDD approach**: Write tests first when adding new features
- **Coverage target**: Maintain or increase coverage when modifying tools

### Test Categories

| Tool | Coverage | Test Focus |
|------|----------|------------|
| synod-parser.py | ~70% | XML parsing, Trust Score calculation, defaults |
| gemini-3.py | ~21% | Config, model mapping, error detection |
| openai-cli.py | ~16% | Config, timeout strategy, O-series detection |

### Adding New Tests

1. Add fixtures to `conftest.py` if needed (mock data, environment)
2. Create test file: `test_{tool_name}.py`
3. Use descriptive test names: `test_{function}_{scenario}`
4. Cover happy path AND edge cases
5. Run full suite before committing

### Common Fixtures (from conftest.py)

```python
# Mock API keys
mock_gemini_api_key   # Sets GEMINI_API_KEY="test-gemini-key-12345"
mock_openai_api_key   # Sets OPENAI_API_KEY="test-openai-key-12345"

# Sample responses
sample_valid_response    # Full SID format with confidence + semantic_focus
sample_invalid_response  # Plain text without XML
sample_partial_response  # Only confidence tag, missing semantic_focus
```

### Testing Requirements

Before submitting changes:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage maintained: `pytest tests/ --cov=tools`
- [ ] No regressions in existing functionality
- [ ] New features have corresponding tests

### Troubleshooting

**ImportError for tools module:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/tools"
pytest tests/
```

**pytest not found:**
```bash
pip install -r requirements-dev.txt
```

## Dependencies

### Internal
- `tools/synod-parser.py` - Main parsing tool under test
- `tools/gemini-3.py` - Gemini CLI under test
- `tools/openai-cli.py` - OpenAI CLI under test

### External (Dev Dependencies)
- `pytest>=7.0.0` - Test framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `pytest-mock>=3.10.0` - Mocking utilities

## CI/CD Integration

Tests run automatically via GitHub Actions on:
- Push to `main` branch
- Pull requests to `main` branch

Matrix testing: Python 3.9, 3.10, 3.11, 3.12

See `.github/workflows/test.yml` for configuration.

---

**Last Updated**: 2026-02-01
**Test Count**: 63 total (36 + 14 + 13)
**Framework**: pytest
