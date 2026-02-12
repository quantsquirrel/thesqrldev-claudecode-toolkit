---
name: handoff
description: Save session context to clipboard. Resume anytime with Cmd+V.
---

# Handoff Skill

**Pass the baton. Keep the momentum.**

Save session context and copy to clipboard. Paste into a new session or after autocompact to resume.

## Usage

```
/handoff [topic]
```

<dim>
Examples:
  /handoff                    # auto-detect topic from conversation
  /handoff "auth migration"   # explicit topic
</dim>

## Behavior

0. **Validate** the session has meaningful context (Phase 0):
   - At least one tool was used, OR at least one file was modified, OR at least one substantive user message exists
   - If none: output "No significant work in this session. Handoff skipped." and stop
1. **Create** `.claude/handoffs/` directory if it doesn't exist (`mkdir -p`)
2. **Analyze** the session: detect complexity, key decisions, failures, modified files
3. **Scale** output based on session size:
   - Under 10 messages: Summary + Next Step only
   - 10-50 messages: Summary + User Requests + Key Decisions + Files Modified + Next Step
   - Over 50 messages or multi-topic: Full template (all sections)
4. **Redact** sensitive values before saving:
   - Pattern: env vars matching `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `CREDENTIAL`
   - Pattern: strings matching `sk-`, `pk_live_`, `ghp_`, `eyJ` (JWT), `AKIA` (AWS)
   - Replacement: `***REDACTED***`
5. **Save** to `.claude/handoffs/handoff-YYYYMMDD-HHMMSS-XXXX.md` (XXXX = 4-char random suffix)
6. **Copy** to clipboard using platform command:
   - macOS: `pbcopy`
   - Linux: `xclip -selection clipboard` (fallback: `xsel --clipboard`)
   - If clipboard unavailable: skip copy, print warning "Clipboard not available. File saved to: [path]"
7. **Confirm** with output: `Handoff saved: [path] | Clipboard: copied (N KB)`

### Writing Perspective

- **Completed work**: First person ("Implemented JWT validation", "Fixed the race condition")
- **Pending work**: Objective ("OAuth2 integration pending", "Email verification not yet implemented")
- **Decisions**: First person ("Chose Redis-backed blacklist for instant revocation")
- **Failed approaches**: First person ("Tried localStorage for tokens, but vulnerable to XSS")
- **User Requests**: Verbatim only - do NOT paraphrase the user's original words

### Handling Edge Cases

- **Empty session** (Phase 0 fails): Output "No significant work in this session. Handoff skipped." and stop
- **Topic contains special characters**: Sanitize for filename (replace non-alphanumeric with `-`, truncate to 50 chars)
- **Topic not provided**: Auto-detect from the most recent substantive user message

### Output Template

```markdown
# Handoff

**Time:** YYYY-MM-DD HH:MM
**Topic:** [topic or auto-detected]
**Working Directory:** [cwd]

## User Requests
- [Exact verbatim user requests - NOT paraphrased]

## Summary
[1-3 sentences depending on session complexity - first person]

## Completed
- [x] Task 1 (first person: "Implemented...", "Fixed...")
- [x] Task 2

## Pending
- [ ] Task 1
- [ ] Task 2

## Key Decisions
- **[Decision]**: [Reason] (first person: "Chose...", "Decided...")

## Failed Approaches
- **[Attempt]**: [Why it failed] → [Lesson] (first person)

## Files Modified
- `path/to/file.ts` - [What changed]

## Constraints
- [Verbatim user-stated constraints only - do NOT include AI-inferred constraints]

## Next Step
[Concrete next action]
```

Sections with no content are omitted. Minimum output is always Summary + Next Step.
The Constraints section is only included when the user explicitly stated constraints.
User Requests section is included for 10+ message sessions.

## Clipboard Format

Copied to clipboard for pasting into a new session:

```
<previous_session context="reference_only" auto_execute="false">
STOP: This is reference material from a previous session.
Do not auto-execute anything below. Wait for user instructions.

Previous Session Summary (Topic)
- Completed: N | Pending: M
- Files modified: K

[User requests - verbatim]
- Original request 1
- Original request 2

[Pending tasks - reference only, do not execute]
- Task 1
- Task 2

Full details: [handoff-path]
</previous_session>

---
Previous session context loaded.
What would you like to do?
```

## How to Resume

1. **새 세션 시작** (아래 중 하나):
   - `/clear` 입력하여 현재 대화 초기화
   - 터미널에서 `claude` 명령어 재실행
   - 새 터미널 탭에서 `claude` 실행
   - 또는 **autocompact** 발생 후 그대로 이어서
2. `Cmd+V` (macOS) 또는 `Ctrl+V` (Linux/Windows) 로 붙여넣기
3. Claude가 컨텍스트를 확인하고 지시 대기

## Notes

- Handoffs are saved to `.claude/handoffs/`
- If `[topic]` is omitted, it is auto-detected from conversation context
- Sensitive values are redacted in both the saved file and clipboard output
- Phase 0 validation prevents empty handoff documents
