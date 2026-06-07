# Synod Module: Phase 1.5 — Debate Gate

> **NEW in v3.7.0** — pre-debate consensus check. Opt-in via `SYNOD_DEBATE_GATE=1`.
> When enabled, runs AFTER Phase 1 (Step 1.7 HALT) and BEFORE Phase 2.
> When the flag is unset (default `0`) this module is a strict no-op — legacy
> 4-phase behavior is completely unchanged.

**Inputs:**
- `${SESSION_DIR}/round-1-solver/` — solver output directory produced by Phase 1
  (files matching `*-parsed.json`, written by `synod-parser.py`)
- `SYNOD_DEBATE_GATE` — feature flag; gate is active only when set to `1`

**Outputs:**
- `${SESSION_DIR}/phase1.5/gate.json` — gate decision record (always written when
  flag is active, for auditability)
- Either: continues to Phase 2/3/4 unchanged (`decision=run_debate`)
- Or: jumps directly to lightweight Phase 4 synthesis (`decision=skip_debate`),
  recording the skip in `${SESSION_DIR}/status.json`

**Cross-references:**
- Runs after Phase 1 (`synod-phase1-solver.md`), specifically after Step 1.7 HALT
- If `decision=skip_debate`, Phase 2 (`synod-phase2-critic.md`) and Phase 3
  (`synod-phase3-defense.md`) are bypassed entirely
- If `decision=run_debate`, Phase 2/3/4 proceed without modification (legacy path)
- Phase 4.5 evidence gate (`synod-phase4-5-evidence-gate.md`) runs after whichever
  Phase 4 path was taken, subject to its own flag

---

## Why this phase exists

The full Synod debate cycle (Phases 2–3) is expensive in both latency and external
model calls. When solvers have already converged on the same answer — same primary
claim, high confidence — running a critic round and a court-style defense adds noise,
not signal. The original responses simply get echoed back to each other.

Phase 1.5 detects this convergence cheaply before any Phase 2 API call is made:

1. **Claim Agreement** — pairwise Jaccard over the primary semantic-focus tokens of
   each solver's response. High overlap means solvers are talking about the same core
   claim.
2. **Weighted Vote Confidence** — `trust_score`-weighted average of solver confidence
   signals. High confidence means solvers are not hedging.
3. **Composite decision** — both thresholds must be met to skip debate. Any failure
   (including parsing errors or missing files) forces `run_debate` for safety.

The gate makes zero external model calls — it operates entirely on the JSON files
already written by Phase 1.

## Step 1.5.1 — Check Feature Flag

```bash
if [[ "${SYNOD_DEBATE_GATE:-0}" != "1" ]]; then
    echo "[Phase 1.5] Skipped — gate disabled (set SYNOD_DEBATE_GATE=1 to enable)" >&2
    # → proceed directly to Phase 2 (legacy path unchanged)
fi
```

If the flag is not `1`, skip the rest of this phase entirely. Phase 2 begins
immediately as in all prior versions.

## Step 1.5.2 — Run Debate Gate

```bash
mkdir -p "${SESSION_DIR}/phase1.5"
python3 "${PLUGIN_ROOT}/tools/debate_gate.py" \
    --signals-dir "${SESSION_DIR}/round-1-solver" \
    > "${SESSION_DIR}/phase1.5/gate.json"
GATE_EXIT=$?
GATE_DECISION=$(python3 -c \
    "import json; print(json.load(open('${SESSION_DIR}/phase1.5/gate.json'))['decision'])" \
    2>/dev/null || echo "run_debate")
```

On any non-zero exit or parse failure, `GATE_DECISION` defaults to `run_debate`
(fail-safe). The gate never blocks the pipeline.

## Step 1.5.3 — Decision Routing

```
IF GATE_DECISION == "skip_debate":
    → Record skip in status.json, then jump to Step 1.5.4 (lightweight synthesis)

IF GATE_DECISION == "run_debate":
    → Continue to Phase 2 unchanged (no modification to critic/defense flow)
```

Decision table:

| `decision` | `agreement_score` | `vote_confidence` | Action |
|---|---|---|---|
| `skip_debate` | ≥ 0.70 | ≥ 80% | Bypass Phases 2–3; lightweight Phase 4 |
| `run_debate` | < 0.70 OR < 80% | (any) | Full Phase 2 → 3 → 4 path |
| `run_debate` (fail-safe) | parse error | (any) | Full path (gate failed open) |

Thresholds are set by `debate_gate.py` defaults. They are intentionally conservative:
the gate only skips when evidence of agreement is strong.

## Step 1.5.4 — Lightweight Phase 4 Synthesis (skip_debate path only)

Runs only when `GATE_DECISION == "skip_debate"`. Phases 2 and 3 are not executed.

```bash
# Record skip in session state
python3 -c "
import json, pathlib
p = pathlib.Path('${SESSION_DIR}/status.json')
s = json.loads(p.read_text()) if p.exists() else {}
gate = json.load(open('${SESSION_DIR}/phase1.5/gate.json'))
s['phase1_5_skipped_debate'] = True
s['agreement_score'] = gate.get('agreement_score')
s['dominant_model'] = gate.get('dominant_model')
p.write_text(json.dumps(s, indent=2))
"
```

Then proceed directly to Phase 4 synthesis (`synod-phase4-synthesis.md`) with the
following adjustments:

- **Input source**: Use solver outputs from `round-1-solver/` directly (no critic
  or defense files exist — Phase 4 must not expect them).
- **Trust scores**: Use `vote_confidence` and `dominant_model` from `gate.json` in
  place of CRIS-computed trust scores for confidence weighting.
- **Verdict note**: Prepend the following line to the final synthesis output,
  immediately after the mode header:

  ```
  ⚡ Debate skipped — solvers reached consensus (agreement={agreement_score:.2f},
     confidence={vote_confidence:.0f}%). Phases 2–3 bypassed.
  ```

- **Phase 4.5** evidence gate runs normally afterward if `SYNOD_EVIDENCE_FIRST=1`.

## Skip path (flag unset)

If `SYNOD_DEBATE_GATE != "1"`:

```bash
echo "[Phase 1.5] Skipped — legacy mode (set SYNOD_DEBATE_GATE=1 to enable)" >&2
```

Phase 2 proceeds immediately with raw Phase 1 outputs, identical to all prior
versions. No files are written to `phase1.5/`. This preserves full backward
compatibility.
