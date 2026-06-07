# Strategy Compare — Accuracy vs Cost Benchmark Harness

`benchmark/strategy_compare.py` compares three Synod debate strategies over a
GSM8K sample and reports **accuracy AND cost** (model-call count, wall-time,
and token estimate) for each.

## Strategies

| ID | Name | Description |
|----|------|-------------|
| S1 | `S1_single_solver` | One strong solver call per question — cheapest |
| S2 | `S2_debate_gate` | Phase-1 solvers → `debate_gate.decide` → vote OR full debate |
| S3 | `S3_full_debate` | Always runs the full 4-phase Synod pipeline — most thorough |

## Quick start — offline (CI, no API keys)

```bash
# Run all three strategies on 10 mock GSM8K questions
python benchmark/strategy_compare.py --mock --n 10

# Enable the debate gate so S2 actually skips debate on high-agreement items
SYNOD_DEBATE_GATE=1 python benchmark/strategy_compare.py --mock --n 10
```

## Live run (requires model services)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="sk-..."

# Run on 50 real GSM8K questions with gate enabled, save JSON report
SYNOD_DEBATE_GATE=1 \
  python benchmark/strategy_compare.py \
    --live \
    --n 50 \
    --output benchmark/results/strategy_compare_$(date +%Y%m%d).json
```

### Prerequisites for live mode

- `tools/agy-cli` and `tools/cliproxy-cli.py` must be accessible and wired to
  working provider APIs.
- All three API keys must be set in the environment.
- The `LiveRunner` class in `strategy_compare.py` is a stub — extend it to
  shell out to the CLI tools following the pattern in `benchmark/run_gsm8k.py`
  (`call_synod_solver`).

## Debate gate toggle

S2's skip behaviour is controlled by `SYNOD_DEBATE_GATE`:

| Value | Effect |
|-------|--------|
| `0` (default) | Gate observe-only — S2 always runs full debate (safe legacy behaviour) |
| `1` | Gate active — S2 skips debate when all solvers agree with high confidence |

Additional gate thresholds (see `tools/debate_gate.py` for full reference):

```bash
SYNOD_GATE_AGREE_THRESHOLD=0.80   # minimum agreement score to skip
SYNOD_GATE_MIN_CONF=80            # minimum per-solver confidence
SYNOD_GATE_MIN_CANEXIT=0.5        # fraction of solvers that must self-report done
```

## Token / cost model

The harness does **not** make real token-counting API calls. Costs are
estimated by multiplying model-call counts by per-tier token constants:

| Call type | Default tokens | Env override |
|-----------|---------------|-------------|
| Strong solver (S1) | 1 500 | `SYNOD_BENCH_TOKENS_STRONG` |
| Phase-1 solver (S2/S3) | 800 | `SYNOD_BENCH_TOKENS_SOLVER` |
| Full debate phase | 3 000 | `SYNOD_BENCH_TOKENS_DEBATE` |
| Blended cost/token | $0.000002 | (hardcoded, adjust in source) |

## Running tests

```bash
rtk proxy python3 -m pytest tests/test_strategy_compare.py -v
```

28 tests cover: harness completion, call-count efficiency (S2 < S3 on
high-agreement items), accuracy computation, and report shape validity.
All tests run fully offline with `MockRunner`.

---

## Live-verification gap

> **Real accuracy and cost numbers are NOT produced by this harness in its
> current state.**
>
> The `MockRunner` uses scripted correct/wrong answers and scripted agreement
> patterns — it validates harness *logic* only, not model performance.
>
> Producing real accuracy-vs-cost measurements requires:
> 1. Wiring `LiveRunner` to shell out to `agy-cli` / `cliproxy-cli`.
> 2. Valid API keys for Anthropic, Gemini, and OpenAI.
> 3. Running against the real GSM8K test split (downloaded via
>    `benchmark/scripts/download_datasets.py`).
>
> Until those steps are completed, treat all numbers from `--mock` runs as
> proxy values that confirm the *harness works*, not that Synod debate beats
> cheaper strategies.
