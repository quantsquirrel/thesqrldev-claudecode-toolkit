---
description: Cancel active Synod deliberation session
allowed-tools: [Read, Write, Bash, Glob]
---

# Cancel Synod Session

## Action
1. Find active session (status != "complete" in `${SYNOD_BASE}/*/status.json`)
   - `SYNOD_BASE="${SYNOD_SESSION_DIR:-${HOME}/.synod/sessions}"`
2. Kill any background processes:
   ```bash
   pkill -f "gemini-3.*synod" 2>/dev/null || true
   pkill -f "openai-cli.*synod" 2>/dev/null || true
   ```
3. Update status.json: `"status": "cancelled"`
4. Report cancellation to user

## Output
Session {session-id} cancelled at round {N}.
Partial results preserved in ${SYNOD_BASE}/{session-id}/

## If No Active Session
Report: "No active Synod session found."
