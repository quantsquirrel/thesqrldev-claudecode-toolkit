---
name: synod-cancel
description: "Cancel active Synod deliberation session"
allowed-tools: Read, Write, Bash, Glob
user-invocable: true
---

# Cancel Synod Session

## Action
1. Find active session (status != "complete" in `${SYNOD_BASE}/*/status.json`)
   - `SYNOD_BASE="${SYNOD_SESSION_DIR:-.omc/synod}"` — matches the real session root used by phase0-setup (`SESSION_DIR=".omc/synod/${SESSION_ID}"`) and synod-resume (`ls -td .omc/synod/synod-*`).
   - Locate the most-recent non-complete session:
     ```bash
     SYNOD_BASE="${SYNOD_SESSION_DIR:-.omc/synod}"
     ACTIVE_SESSION=""
     for dir in $(ls -td "${SYNOD_BASE}"/synod-* 2>/dev/null); do
       status=$(python3 -c "import json,sys; d=json.load(open('${dir}/status.json')); print(d.get('status',''))" 2>/dev/null)
       if [[ "$status" != "complete" && "$status" != "cancelled" && -n "$status" ]]; then
         ACTIVE_SESSION="$dir"
         break
       fi
     done
     ```
2. Kill worker processes scoped to the active session's tmp directory.
   Phase 1 invokes CLIs as `run_cli "$GEMINI_CLI" ... < "${SESSION_DIR}/tmp/gemini-prompt.txt"` — the word "synod" never appears in their argv, so patterns like `pkill -f "agy-cli.*synod"` are no-ops. Instead, target processes whose command line references the session-specific tmp path:
   ```bash
   if [[ -n "$ACTIVE_SESSION" ]]; then
     SESSION_TMP="${ACTIVE_SESSION}/tmp"
     # Kill agy-cli or cliproxy-cli processes reading from this session's tmp files.
     # Scope the match to the session path to avoid killing unrelated user processes.
     pkill -f "agy-cli.*${SESSION_TMP}" 2>/dev/null || true
     pkill -f "cliproxy-cli.*${SESSION_TMP}" 2>/dev/null || true
     # Fallback: terminate any process with an open file under the session tmp dir.
     # (Handles shells/wrappers that exec the CLI without the path in argv.)
     if command -v fuser >/dev/null 2>&1; then
       fuser -k "${SESSION_TMP}"/* 2>/dev/null || true
     fi
   fi
   ```
   **Limitation:** Phase 1 does not write PID files, so there is no authoritative PID list. The above matchers are best-effort; processes that have already closed their stdin fd before cancel runs will not be matched. A future improvement would be for phase0-setup to write `$GEMINI_PID` / `$OPENAI_PID` to `${SESSION_DIR}/pids.json` immediately after backgrounding.
3. Update status.json: `"status": "cancelled"`
4. Report cancellation to user

## Output
Session {session-id} cancelled at round {N}.
Partial results preserved in ${SYNOD_BASE}/{session-id}/

## If No Active Session
Report: "No active Synod session found."
