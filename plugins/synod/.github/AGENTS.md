<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-01 -->

# .github Directory - CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration and quality assurance of the Synod plugin.

## Purpose

Automated CI/CD pipelines that run on every push and pull request to ensure code quality:
- **Test**: Run pytest with coverage across multiple Python versions
- **Lint**: Check code style with ruff
- **Type Check**: Static type analysis with mypy

## Directory Structure

```
.github/
└── workflows/
    ├── test.yml        # pytest with coverage, multi-version matrix
    ├── lint.yml        # ruff check and format validation
    └── type-check.yml  # mypy static type checking
```

## Workflow Details

### test.yml - Test Suite

**Triggers**: Push/PR to `main`

**Matrix**: Python 3.9, 3.10, 3.11, 3.12

**Steps**:
1. Checkout code
2. Setup Python with pip cache
3. Install dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest --cov=tools --cov-report=xml`
5. Upload coverage to Codecov (Python 3.12 only)

**Key Configuration**:
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
  fail-fast: false  # Continue other versions if one fails
```

---

### lint.yml - Code Style

**Triggers**: Push/PR to `main`

**Python Version**: 3.12

**Steps**:
1. Checkout code
2. Setup Python
3. Install ruff
4. Run `ruff check .` - Linting rules
5. Run `ruff format --check .` - Format validation

**Ruff Configuration**: See `pyproject.toml` for rule settings.

---

### type-check.yml - Static Type Analysis

**Triggers**: Push/PR to `main`

**Python Version**: 3.12

**Steps**:
1. Checkout code
2. Setup Python
3. Install dependencies: `pip install -e ".[dev]"`
4. Run `mypy tools/`

**Mypy Configuration**: See `pyproject.toml` for type checking rules.

## For AI Agents

### Working In This Directory

- Workflows use `actions/checkout@v4` and `actions/setup-python@v5`
- All workflows have `contents: read` permission only
- pip caching enabled for faster CI runs
- Coverage reports uploaded to Codecov

### Modifying Workflows

When changing workflows:
1. Test changes in a feature branch first
2. Ensure YAML syntax is valid
3. Check that all required secrets exist (CODECOV_TOKEN)
4. Verify matrix combinations complete successfully

### Adding New Workflows

Common patterns:
```yaml
name: Workflow Name

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read

jobs:
  job-name:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
        cache: 'pip'
    # ... additional steps
```

### Required Secrets

| Secret | Used By | Purpose |
|--------|---------|---------|
| `CODECOV_TOKEN` | test.yml | Coverage report upload |

### Build Status Integration

After workflows run, check status:
- ✅ Green: All checks passed
- ❌ Red: At least one check failed
- 🟡 Yellow: In progress

### Debugging Failed Workflows

1. Check workflow run logs in GitHub Actions tab
2. Look for specific step that failed
3. Common issues:
   - Missing dependencies → Update `requirements-dev.txt`
   - Type errors → Fix with `mypy tools/` locally
   - Lint errors → Fix with `ruff check . --fix`

## Dependencies

### GitHub Actions Used

| Action | Version | Purpose |
|--------|---------|---------|
| `actions/checkout` | v4 | Clone repository |
| `actions/setup-python` | v5 | Install Python with caching |
| `codecov/codecov-action` | v4 | Upload coverage reports |

### Tools Installed by Workflows

- `pytest`, `pytest-cov` - Testing and coverage
- `ruff` - Linting and formatting
- `mypy` - Type checking

## Quick Reference

| Workflow | Check | Local Command |
|----------|-------|---------------|
| test.yml | Tests pass | `pytest tests/ -v` |
| test.yml | Coverage | `pytest --cov=tools` |
| lint.yml | Lint check | `ruff check .` |
| lint.yml | Format check | `ruff format --check .` |
| type-check.yml | Type check | `mypy tools/` |

---

**Last Updated**: 2026-02-01
**Workflows**: 3 (test, lint, type-check)
**CI Platform**: GitHub Actions
