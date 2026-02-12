# Contributing to Synod

Thank you for your interest in contributing to **Synod**! This multi-agent deliberation system thrives on community collaboration. Whether you're fixing bugs, adding features, or improving documentation, your contributions are welcome.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Report Bugs](#how-to-report-bugs)
- [How to Suggest Features](#how-to-suggest-features)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)

---

## Code of Conduct

We are committed to fostering a welcoming and inclusive community. Please be respectful and constructive in all interactions. A formal Code of Conduct will be added soon—until then, treat others with kindness and professionalism.

---

## How to Report Bugs

Found a bug? Help us improve Synod by reporting it!

### Before Submitting
1. **Search existing issues** to avoid duplicates
2. **Check the [Troubleshooting](README.md#troubleshooting)** section in the README
3. **Verify your environment** (Python version, API keys, dependencies)

### Submitting a Bug Report
[Open an issue](https://github.com/quantsquirrel/claude-synod-debate/issues/new) with:

- **Title**: Clear, descriptive summary (e.g., "Timeout during round-2-critic with GPT-4o")
- **Environment**: Python version, OS, Claude Code version
- **Steps to reproduce**: Exact commands and inputs
- **Expected vs. actual behavior**: What should happen vs. what happened
- **Logs/screenshots**: Include error messages or `~/.synod/sessions/` logs
- **Workaround**: If you found a temporary fix, share it!

---

## How to Suggest Features

Have an idea to improve Synod? We'd love to hear it!

### Before Suggesting
1. **Review the [Research Foundation](README.md#research-foundation)** to align with core principles
2. **Check existing discussions** for similar proposals
3. **Consider feasibility**: Does it fit the 3-round debate structure?

### Submitting a Feature Request
[Start a discussion](https://github.com/quantsquirrel/claude-synod-debate/discussions) with:

- **Problem statement**: What pain point does this solve?
- **Proposed solution**: How would it work?
- **Alternatives considered**: Other approaches you explored
- **Research backing** (optional): Papers or experiments supporting the idea

---

## Development Setup

### Prerequisites
- **Python 3.9+**
- **Git**
- **Claude Code CLI v1.0.0+**
- **API Keys**: `GEMINI_API_KEY`, `OPENAI_API_KEY`

### Installation

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-synod-debate.git
   cd claude-synod-debate
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install development dependencies** (for testing)
   ```bash
   pip install pytest pytest-cov pytest-mock
   ```

5. **Set up environment variables**
   ```bash
   export GEMINI_API_KEY="your-gemini-key"
   export OPENAI_API_KEY="your-openai-key"
   ```

6. **Run tests to verify setup**
   ```bash
   pytest tests/
   ```

### Project Structure
```
synod-plugin/
├── skills/           # Claude Code skill definitions (.md files)
├── tools/            # Python CLI tools (synod-parser.py, etc.)
├── tests/            # Test suite
├── benchmark/        # Evaluation framework
├── requirements.txt  # Runtime dependencies
└── plugin.json       # Plugin metadata
```

---

## Pull Request Process

### Before You Start
1. **Check existing PRs** to avoid duplicate work
2. **Open an issue first** for major changes to discuss approach
3. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Workflow

1. **Make your changes**
   - Keep commits atomic and focused
   - Write clear commit messages (e.g., `fix: Handle timeout in round-3-defense`)
   - Follow [Conventional Commits](https://www.conventionalcommits.org/) format

2. **Add tests**
   - All new features must include tests
   - Bug fixes should include regression tests
   - Aim for >80% code coverage

3. **Run tests and linters**
   ```bash
   pytest tests/                    # Run all tests
   pytest tests/ --cov=tools        # Check coverage
   python -m py_compile tools/*.py  # Check syntax
   ```

4. **Update documentation**
   - Update `README.md` if adding features or changing behavior
   - Add docstrings to new functions/classes
   - Update `skills/` if modifying debate flows

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Open a PR on GitHub
   - Fill out the PR template (title, description, testing notes)
   - Link related issues with `Fixes #123` or `Closes #456`

### PR Review
- Maintainers will review within 3-5 business days
- Address feedback with new commits (don't force-push during review)
- Once approved, maintainers will merge your PR

---

## Code Style Guidelines

### Python Style
- **Follow PEP 8**: Use consistent formatting (4 spaces, max 100 chars/line)
- **Simplicity over cleverness**: Readable code > terse code
- **Type hints**: Use where they improve clarity
  ```python
  def calculate_trust(credibility: float, reliability: float) -> float:
      return min((credibility * reliability) / 0.5, 2.0)
  ```

### Documentation
- **Docstrings**: Use Google-style docstrings for functions/classes
  ```python
  def parse_confidence(xml_str: str) -> dict:
      """Parse confidence XML from agent response.

      Args:
          xml_str: Raw XML string from agent output

      Returns:
          Dict with 'score', 'evidence', 'logic', 'expertise'

      Raises:
          ValueError: If XML is malformed or missing required tags
      """
  ```
- **Comments**: Explain *why*, not *what* (code shows what)

### Error Handling
- **Fail gracefully**: Always provide helpful error messages
- **Retry with backoff**: For API calls, implement exponential backoff
- **Validate inputs**: Check API keys, file paths, JSON structure early

### Dependencies
- **Minimize additions**: Only add dependencies when necessary
- **Pin versions**: Use `>=` for flexibility but test with pinned versions
- **No vendoring**: Use pip packages, not copied code

---

## Testing Guidelines

### Test Organization
```
tests/
├── test_synod_parser.py    # Parser logic tests
├── test_gemini.py           # Gemini API integration tests
├── test_openai_cli.py       # OpenAI CLI tests
└── conftest.py              # Shared fixtures
```

### Writing Tests
- **Use pytest**: Standard testing framework
- **Naming**: `test_<function>_<scenario>` (e.g., `test_parse_confidence_missing_tag`)
- **Arrange-Act-Assert**: Clear structure
  ```python
  def test_calculate_trust_high_confidence():
      # Arrange
      credibility, reliability = 0.9, 0.85

      # Act
      trust = calculate_trust(credibility, reliability)

      # Assert
      assert trust >= 1.5, "Should qualify as high trust"
  ```

### Test Coverage
- **Unit tests**: Core logic (parsers, calculators)
- **Integration tests**: API calls (use mocks for external services)
- **Smoke tests**: End-to-end debate flows (use fixtures)

### Running Tests
```bash
# All tests
pytest tests/

# Specific file
pytest tests/test_synod_parser.py

# With coverage report
pytest tests/ --cov=tools --cov-report=term-missing

# Verbose output
pytest tests/ -v
```

### Mocking External APIs
```python
@pytest.fixture
def mock_gemini_response():
    return {
        "confidence": 85,
        "evidence": "Test evidence",
        "can_exit": True
    }

def test_gemini_call(mock_gemini_response, monkeypatch):
    monkeypatch.setattr("tools.gemini.call_api", lambda x: mock_gemini_response)
    # Test your code here
```

---

## Questions?

- **General questions**: [Start a discussion](https://github.com/quantsquirrel/claude-synod-debate/discussions)
- **Bug reports**: [Open an issue](https://github.com/quantsquirrel/claude-synod-debate/issues)
- **Security concerns**: Email maintainers (see `plugin.json`)

---

**Thank you for making Synod better!** 🎯
