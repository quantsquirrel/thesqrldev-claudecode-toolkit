<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-02 | Updated: 2026-02-10 -->

# examples

## Purpose

Canonical example handoff documents demonstrating proper structure and content for session handoffs. These serve as reference implementations for both humans and AI agents creating handoff documents.

## Key Files

| File | Description |
|------|-------------|
| `example-handoff.md` | Production-quality reference handoff (JWT auth feature, 4.5h session) |

## For AI Agents

### Working In This Directory

- Study `example-handoff.md` before creating handoff documents
- Examples demonstrate the v2.2.0 7-section format: Summary, Completed, Pending, Key Decisions, Failed Approaches, Files Modified, Next Step
- Quality standard: specific details over vague descriptions

### Quality Patterns

| Pattern | Bad Example | Good Example |
|---------|------------|--------------|
| Specificity | "Added authentication" | "Implemented JWT with HS256 signing, 15-min expiry" |
| Failed approaches | "Didn't work" | "localStorage for tokens: vulnerable to XSS, switched to httpOnly cookies" |
| Next step | "Continue work" | "Implement refresh token rotation in `src/auth/refresh.ts`" |

### When Updating Examples

1. Ensure all 7 sections are demonstrated
2. Include realistic technical details
3. Show both completed and pending items
4. Document at least one failed approach with lesson learned

## Dependencies

### Internal

- `../SKILL.md` - Defines the template these examples follow
- `../scripts/validate.sh` - Can validate example quality

<!-- MANUAL: -->
