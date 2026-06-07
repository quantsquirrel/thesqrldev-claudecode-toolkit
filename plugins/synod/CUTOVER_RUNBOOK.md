# Synod Backend Cutover Runbook — bridge → direct

**Status:** prepared 2026-06-06 · **Deadline:** bridges expire **~2026-06-30**

## What this is

Synod routes its Gemini and OpenAI lanes through two backends:

| Backend | Gemini CLI | OpenAI CLI | Auth | Lifetime |
|---|---|---|---|---|
| **bridge** (current default) | `agy-cli` (Antigravity 3.5 Flash) | `cliproxy-cli` (CLIProxyAPI :8317) | personal OAuth / proxy | **temporary — expires ~2026-06-30** |
| **direct** (durable canonical) | `gemini-3.py` | `openai-cli.py` | `GEMINI_API_KEY` / `OPENAI_API_KEY` | permanent |

`config/model_matrix.json` is authored against the **bridge** vocabulary. The
cutover does not rewrite that file — `tools/provider_backend.py` translates a
bridge roster to direct on demand, controlled by `SYNOD_PROVIDER_BACKEND`
(`bridge` default, `direct` post-cutover).

### Model translation (model-accurate, not tier-accurate)

| Provider | Bridge model | Direct model | Direct CLI key → vendor |
|---|---|---|---|
| gemini | `3.5-flash` | `flash-latest` | `gemini-flash-latest` (stable alias, no preview EOL) |
| openai | `gpt54mini` | `gpt54mini` | `gpt-5.4-mini` |
| openai | `gpt55fast` | `gpt55` | `gpt-5.5` |
| openai | `gpt55` | `gpt55` | `gpt-5.5` |

## Pre-cutover checklist (offline — run any time)

```bash
python3 tools/cutover_check.py            # structural readiness (exit 0 = ready)
python3 tools/cutover_check.py --json     # machine-readable report
```

This verifies, with **no network call**:
1. every tier in `model_matrix.json` resolves cleanly to the direct backend,
2. each resolved direct model is a real key in the CLI `MODEL_MAP` **and** an
   accepted `--model` choice,
3. `gemini-3.py` and `openai-cli.py` exist,
4. API keys are set (advisory; enforce with `--require-keys`).

## Cutover steps (on/after 2026-06-30, or whenever bridges stop working)

1. **Export vendor API keys** in the runtime shell / profile:
   ```bash
   export GEMINI_API_KEY="..."     # or GOOGLE_API_KEY
   export OPENAI_API_KEY="..."
   ```
2. **Gate + flip** with the helper (enforces keys, prints the activation):
   ```bash
   tools/cutover.sh --require-keys           # dry-run, fails if not ready
   . tools/cutover.sh --apply --require-keys # exports SYNOD_PROVIDER_BACKEND=direct
   ```
   Or manually after a clean check:
   ```bash
   export SYNOD_PROVIDER_BACKEND=direct
   ```
3. **Verify routing** resolves to direct CLIs:
   ```bash
   python3 tools/tier_matrix.py --tier standard --backend direct
   # expect cli: gemini-3 / openai-cli, model: flash-latest / gpt55
   ```
4. **(Optional) Decommission bridges** so accidental bridge use fails loudly:
   ```bash
   rm -f ~/.synod/bin/agy-cli ~/.synod/bin/cliproxy-cli
   ```
   With the bridges gone, the legacy-fallback resolution in the skill picks the
   direct wrappers regardless of `SYNOD_PROVIDER_BACKEND`.

## Rollback

The bridges remain valid until 2026-06-30. To revert before then:
```bash
unset SYNOD_PROVIDER_BACKEND     # or: export SYNOD_PROVIDER_BACKEND=bridge
```
`bridge` is an identity pass-through — the roster is served exactly as authored.

## Verification evidence captured at prep time

- `tools/cutover_check.py` → **READY** (all tiers resolve+validate to direct).
- `python3 tools/tier_matrix.py --tier {simple,standard,deep,ultra} --backend direct`
  → every roster rewrites to `gemini-3`/`openai-cli` with valid model keys.
- Test suites: `tests/test_provider_backend.py`, `tests/test_cutover_check.py`,
  `tests/test_direct_cli_currency.py`.
