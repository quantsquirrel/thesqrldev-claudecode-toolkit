<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# scripts

## Purpose

Validation and utility scripts for handoff document quality assurance. Cross-platform compatible (macOS and Linux).

## Key Files

| File | Description |
|------|-------------|
| `validate.sh` | Handoff quality validator - 5 checks, scoring 0-100, pass threshold 70 |

## For AI Agents

### Working In This Directory

- All scripts use bash strict mode (`set -euo pipefail`)
- Color output auto-detected (disabled when piped)
- Compatible with both BSD (macOS) and GNU (Linux) tools

### validate.sh - Quality Checks

| Check | Points | What It Validates |
|-------|--------|-------------------|
| No TODOs | +20 | No `[TODO: ...]` placeholders remain |
| No Secrets | +20 | No API keys, tokens, passwords, or long random strings |
| Required Sections | +20 | Summary, Completed, Pending, Next Steps headers present |
| Files Exist | +20 | Referenced files in "Files Modified" exist on disk (+10 partial) |
| Next Steps | +20 | At least 2 action items in Next Steps section |

**Exit codes:** 0 = PASS (>=70), 1 = FAIL (<70), 2 = ERROR (bad usage)

### Usage

```bash
./scripts/validate.sh <handoff-file.md>
./scripts/validate.sh examples/example-handoff.md
```

### Testing Requirements

```bash
# Should pass
./scripts/validate.sh examples/example-handoff.md

# Verify exit codes
echo $?  # 0 = pass, 1 = fail, 2 = error
```

## Dependencies

### Internal

- `../examples/example-handoff.md` - Test input for validation

### External

- bash, grep (-E extended regex), sed (POSIX compatible)

<!-- MANUAL: -->
