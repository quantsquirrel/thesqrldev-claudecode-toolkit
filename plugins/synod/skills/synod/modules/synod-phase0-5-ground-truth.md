# Synod Module: Phase 0.5 — Ground-Truth Probe + Prompt Lint + Tier Select

> **NEW in v3.4.0** — evidence-first gating. Opt-in via `SYNOD_EVIDENCE_FIRST=1`
> or the `--evidence-first` flag. When enabled, runs BEFORE Phase 1 Solver
> and enriches the PROBLEM passed to external models.

**Inputs:**
- `PROBLEM` — user's problem statement
- `TARGET_PATH` — optional filesystem path under review (file, directory, or repo root).
  When provided, the ground-truth probe inspects it mechanically.
- `SYNOD_EVIDENCE_FIRST` or `--evidence-first` flag — gates this entire phase
- `USER_TIER` (optional) — overrides `--tier` selection: `simple|standard|deep|ultra|auto`

**Outputs:**
- `${SESSION_DIR}/phase0.5/probe/` — ground-truth probe artifacts (5 files)
- `${SESSION_DIR}/phase0.5/lint.json` — prompt linter output
- `${SESSION_DIR}/phase0.5/tier.json` — chosen model roster
- `ENRICHED_PROBLEM` — PROBLEM with Primary Evidence + Known Limitations sections

**Cross-references:**
- Called after Phase 0 (`synod-phase0-setup.md`), before Phase 1 (`synod-phase1-solver.md`)
- If this phase is disabled (env flag unset AND no --evidence-first), skip entirely and
  pass PROBLEM to Phase 1 verbatim (legacy behavior preserved).

---

## Why this phase exists

The v1 Synod pipeline treats the orchestrator's PROBLEM statement as ground
truth. In practice, the orchestrator (Claude) may embed stale self-descriptions
or fabricated references. Solvers then evaluate a fiction. CRIS (Phase 2)
scores solver output but never audits the input.

Phase 0.5 closes that gap with three cheap mechanical checks:

1. **Ground-Truth Probe** — if a target path is supplied, inspect import/test/
   version state. Broken artifacts (e.g., unpackable tarballs) become a
   **first-class finding** instead of being silently rationalized.
2. **Prompt Linter** — regex audit for common unbacked claims
   (`default X`, `providers/ 추상화`, `22/22 regression green`). High-severity
   findings gate Phase 1 unless the user passes `--skip-lint`.
3. **Tier Selection** — replace latency-based "recommended" defaults with an
   explicit tier → model roster mapping (`config/model_matrix.json`). The
   strongest reasoning models (pro-thinking, o3-high) are no longer silently
   demoted for being slow.

## Step 0.5.1 — Ground-Truth Probe (conditional)

Run only if `TARGET_PATH` is set (from `--target <path>` flag or detected as
an absolute path prefix in PROBLEM):

```bash
mkdir -p "${SESSION_DIR}/phase0.5/probe"
python3 "${PLUGIN_ROOT}/tools/ground_truth_probe.py" "${TARGET_PATH}" \
  --output-dir "${SESSION_DIR}/phase0.5/probe" \
  > "${SESSION_DIR}/phase0.5/probe/summary.json"
PROBE_STATUS=$(python3 -c "import json; print(json.load(open('${SESSION_DIR}/phase0.5/probe/summary.json'))['status'])")
```

Decision table:

| `status` | Action |
|---|---|
| `ok` | Continue silently; embed `integrity.json` summary in Primary Evidence. |
| `degraded` | Continue; surface top findings to user as a yellow warning. |
| `broken` | **Surface `top_findings` to user.** Ask confirmation: "대상이 import/build되지 않습니다. 그래도 진행할까요? [y/N]". If yes, proceed with `status=broken` embedded. |

## Step 0.5.2 — Prompt Linter

```bash
python3 "${PLUGIN_ROOT}/tools/prompt_linter.py" --file /tmp/synod-prompt.txt \
  > "${SESSION_DIR}/phase0.5/lint.json"
LINT_EXIT=$?
```

- `LINT_EXIT=0` → no high-severity warnings, proceed
- `LINT_EXIT=2` AND `--skip-lint` not passed → HALT. Display warnings and
  advise the user to revise the prompt. Do not auto-fix.
- `LINT_EXIT=2` AND `--skip-lint` passed → proceed but embed warnings in
  "Known Limitations" section of ENRICHED_PROBLEM.

## Step 0.5.3 — Tier Selection

```bash
# Use classifier output (already written by Phase 0) or user-supplied tier
python3 "${PLUGIN_ROOT}/tools/tier_matrix.py" \
  --tier "${USER_TIER:-auto}" \
  --classifier-json "${SESSION_DIR}/meta.json" \
  > "${SESSION_DIR}/phase0.5/tier.json"
```

If `tier.json.requires_async=true` and the current runtime lacks async support
(v3.4.0 does not implement async dispatch yet), warn the user:

> ⚠ Selected tier requires wall-clock ≥ 300s. v3.4.0 runs synchronously —
> expect a long wait. Downgrade to `--tier standard` for ≤120s.

Export the roster so Phase 1 solvers can consume it:

```bash
export SYNOD_MODEL_OVERRIDES="$(cat ${SESSION_DIR}/phase0.5/tier.json)"
```

Phase 1 Solver reads `SYNOD_MODEL_OVERRIDES` at the top of Step 1.2 and, if
set, uses the roster's `provider/cli/model/thinking|reasoning` fields instead
of `GEMINI_MODEL`/`OPENAI_MODEL` defaults.

## Step 0.5.4 — Compose ENRICHED_PROBLEM

Replace the raw PROBLEM that Phase 1 would otherwise pass to solvers with:

```
## Primary Evidence (machine-verified — authoritative)
{probe.integrity.json summary, max 20 lines}
{probe.top_findings as bullets}
{probe.file_tree.txt first 30 lines, if status != ok}

## Known Limitations of the Orchestrator Summary Below
{prompt_linter warnings as bullets, each with rule/span/severity}

## Orchestrator Hypothesis (may be stale — verify against Primary Evidence above)
{user's original PROBLEM verbatim}

## Your Task
Base all claims on Primary Evidence. If Orchestrator Hypothesis contradicts
Primary Evidence, report the contradiction as a FIRST-CLASS finding before
your main analysis.
```

Pass ENRICHED_PROBLEM (not raw PROBLEM) to Phase 1 solvers.

## Skip path

If `SYNOD_EVIDENCE_FIRST != "1"` AND `--evidence-first` not present:

```bash
echo "[Phase 0.5] Skipped — legacy mode (set SYNOD_EVIDENCE_FIRST=1 to enable)" >&2
```

Phase 1 proceeds with raw PROBLEM, identical to v3.3 behavior. This preserves
backward compatibility for all existing users.
