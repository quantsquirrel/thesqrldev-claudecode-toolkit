# Synod Module: Resume Protocol

**Inputs:**
- User command: `/synod resume` or `--continue` flag
- Existing session directories in `.omc/synod/`

**Outputs:**
- Restored session context
- Resume execution from checkpoint
- Updated `status.json` with resume timestamp

**Cross-references:**
- Called from main `synod.md` when resume is triggered
- Jumps to appropriate phase module based on checkpoint

---

## Resume Protocol

**Trigger:** `$1 == "resume"` OR `$ARGUMENTS` contains `--continue`

## Step R.1: Find Latest Session

```bash
LATEST=$(ls -td .omc/synod/synod-* 2>/dev/null | head -1)
```

If no session found: "재개할 활성 Synod 세션이 없습니다."

## Step R.2: Read Session State

Read `${LATEST}/status.json` to determine:
- `current_round` - Last completed round
- `resume_point` - Specific checkpoint
- `can_resume` - Whether session is resumable

If `status == "complete"`: "세션이 이미 완료되었습니다. 새 세션을 시작하세요."
If `status == "cancelled"`: "세션이 취소되었습니다. 새 세션을 시작하세요."

## Step R.3: Load Context

Read all completed round files to rebuild context:
- Round 0: `meta.json` for configuration
- Round 1: `round-1-solver/*.md` for initial solutions
- Round 2: `round-2-critic/*.md` for critiques and Trust Scores
- Round 3: `round-3-defense/*.md` for court arguments

## Step R.4: Continue Execution

Jump to the appropriate phase based on `current_round`:
- Round 0 incomplete → PHASE 0 (see `synod-phase0-setup.md`)
- Round 1 incomplete → PHASE 1 (see `synod-phase1-solver.md`, may have partial responses)
- Round 2 incomplete → PHASE 2 (see `synod-phase2-critic.md`)
- Round 3 incomplete → PHASE 3 (see `synod-phase3-defense.md`)
- Round 4 incomplete → PHASE 4 (see `synod-phase4-synthesis.md`)

Announce: `[Synod] {SESSION_ID} 세션을 단계 {N}부터 재개합니다`

**Resume Strategy:**

1. **Check for partial outputs:** If a round is "in_progress", check for any completed model responses
2. **Skip completed models:** Don't re-run models that already have valid responses
3. **Re-run failed models:** Retry any models that timed out or failed
4. **Preserve state:** Never overwrite existing valid responses

---

## Session Cleanup

Sessions are preserved in `.omc/synod` for:
- Debugging and auditing
- Resume capability
- Learning from past deliberations

To clean old sessions:
```bash
# Remove sessions older than 7 days
find .omc/synod -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
```

**Auto-cleanup (optional):**

Add to `.omc/synod/.cleanup-policy.json`:
```json
{
  "max_age_days": 7,
  "max_sessions": 50,
  "keep_complete": true,
  "auto_cleanup": true
}
```

**Manual cleanup commands:**

```bash
# Remove all incomplete sessions
find .omc/synod -name "status.json" -exec grep -l '"status": "cancelled"' {} \; | xargs dirname | xargs rm -rf

# Remove sessions older than N days
find .omc/synod -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

# Keep only the 20 most recent sessions
ls -td .omc/synod/synod-* | tail -n +21 | xargs rm -rf
```
