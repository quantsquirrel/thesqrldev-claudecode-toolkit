# Synod v3.0 Benchmark Suite

Rigorous evaluation of Synod's multi-model deliberation framework against industry baselines on mathematical reasoning (GSM8K) and truthfulness (TruthfulQA).

## Overview

This benchmark compares:
- **Synod v3.0**: Multi-model deliberation (Claude + GPT-4o + Gemini)
- **Claude-only**: Single-model baseline
- **GPT-4o-only**: Single-model baseline
- **Majority Vote**: Multi-model voting without deliberation
- **Self-Consistency** (optional): Sampling-based baseline

> **Note**: The current Phase 1 implementation uses a simplified 2-model approach (Gemini + OpenAI) for rapid validation. Full Synod deliberation with all three models (Claude + GPT-4o + Gemini) will be integrated in Phase 2 once the initial benchmark framework is validated.

## What This Benchmark Does

### Phase 1: Mathematical Reasoning (GSM8K)
- **Dataset**: 300 randomly sampled grade school math problems
- **Metric**: Exact match accuracy
- **Goal**: Validate that Synod's deliberation improves reasoning quality

### Phase 2: Truthfulness (TruthfulQA) - Future
- **Dataset**: 300 multiple-choice questions designed to expose model misconceptions
- **Metric**: Accuracy on MC1 (single correct answer)
- **Goal**: Test if deliberation reduces hallucinations

## Prerequisites

### 1. API Keys

Set these environment variables:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-google-key"
```

### 2. Python Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

### 3. Synod Plugin

Ensure Synod v3.0 is installed and accessible:

```bash
# From synod-plugin root directory
pip install -e .
```

## Running Phase 1 (GSM8K)

### Quick Start

```bash
# From benchmark directory
python run_gsm8k.py --phase gsm8k
```

### Configuration

Edit `config.yaml` to customize:

```yaml
benchmarks:
  gsm8k:
    sample_size: 300  # Reduce for faster testing
    seed: 42          # For reproducibility

synod:
  mode: "general"     # review/design/debug/general
  rounds: 3           # 2 or 3

baselines:
  claude_only: true
  gpt4o_only: true
  majority_vote: true
  self_consistency: false  # Very expensive
```

### Monitoring Progress

The benchmark displays real-time progress with:
- Questions processed
- Current accuracy
- Estimated time remaining
- Cost tracking

```
Processing GSM8K [███████░░░] 120/300 (40%)
Synod Accuracy: 87.5% | Claude: 78.3% | GPT-4o: 81.7%
Estimated Cost: $30.25 / $100.00
```

## Interpreting Results

### Output Files

All results saved to `results/` directory:

```
results/
├── gsm8k_synod_20240115_143022.json       # Raw Synod responses
├── gsm8k_claude_20240115_143022.json      # Claude baseline
├── gsm8k_gpt4o_20240115_143022.json       # GPT-4o baseline
├── gsm8k_majority_20240115_143022.json    # Majority vote
└── gsm8k_report_20240115_143022.html      # Summary report
```

### Key Metrics

1. **Accuracy**: Percentage of correct answers
2. **Confidence**: Average model certainty
3. **Deliberation Quality**: Consensus vs. disagreement rate
4. **Cost**: Total API costs

### Success Criteria (Phase 1)

Synod v3.0 is validated if:
- ✅ Accuracy > max(single-model baselines)
- ✅ Accuracy ≥ majority vote baseline
- ✅ Cost per question < $0.50

### Example Report

```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Method           ┃ Accuracy ┃ Confidence ┃ Cost   ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ Synod v3.0       │ 87.3%    │ 0.91       │ $75.00 │
│ Claude-only      │ 78.7%    │ 0.84       │ $25.00 │
│ GPT-4o-only      │ 81.0%    │ 0.87       │ $30.00 │
│ Majority Vote    │ 84.3%    │ 0.78       │ $55.00 │
└──────────────────┴──────────┴────────────┴────────┘

✅ Synod outperforms all baselines
✅ Cost efficiency: $0.25 per question
```

## Cost Estimates

### Phase 1 (GSM8K, 300 questions)

| Method | Estimated Cost |
|--------|----------------|
| Synod v3.0 (3 rounds) | $75 |
| Claude-only | $25 |
| GPT-4o-only | $30 |
| Majority Vote | $55 |
| **Total** | **$185** |

Budget limit: $100 for Synod only (configurable in `config.yaml`)

### Cost per Question Breakdown

**Synod v3.0** (~$0.25/question):
- Round 1: Claude ($0.03) + GPT-4o ($0.04) + Gemini ($0.01)
- Round 2: Claude ($0.03) + GPT-4o ($0.04) + Gemini ($0.01)
- Round 3: Claude ($0.03) + GPT-4o ($0.04) + Gemini ($0.01)
- Synthesis: Claude ($0.01)

**Single models** (~$0.08-$0.10/question):
- Claude: $0.08
- GPT-4o: $0.10

### Reducing Costs

To test with smaller budget:

```yaml
benchmarks:
  gsm8k:
    sample_size: 100  # 1/3 cost

baselines:
  self_consistency: false  # Skip most expensive
```

## Advanced Usage

### Running Specific Baselines

```bash
python run_gsm8k.py --phase gsm8k --methods synod,claude_only
```

### Custom Synod Configuration

```bash
python run_gsm8k.py --synod-rounds 2 --synod-mode review
```

### Analyzing Previous Results

```bash
python analyze.py results/gsm8k_synod_20240115_143022.json
```

## Troubleshooting

### Rate Limits

If you hit API rate limits, increase delay:

```yaml
execution:
  delay_between_requests: 5  # seconds
```

### Timeouts

For complex questions, increase timeout:

```yaml
execution:
  timeout_seconds: 600  # 10 minutes
```

### Out of Memory

Process smaller batches:

```yaml
execution:
  batch_size: 50  # Process in chunks
```

## Project Structure

```
benchmark/
├── config.yaml              # Main configuration
├── README.md                # This file
├── requirements.txt         # Dependencies
├── __init__.py              # Package init
├── run_gsm8k.py             # Main runner (to be created)
├── analyze.py               # Analysis tools (to be created)
├── results/                 # Output directory (gitignored)
├── data/                    # Dataset cache
└── scripts/                 # Utility scripts
    ├── download_datasets.py
    ├── validate_config.py
    └── cost_estimator.py
```

## Next Steps

1. **Phase 1**: Run GSM8K benchmark (this document)
2. **Phase 2**: Run TruthfulQA benchmark
3. **Analysis**: Statistical significance testing
4. **Publication**: Share results with community

## References

- [GSM8K Paper](https://arxiv.org/abs/2110.14168)
- [TruthfulQA Paper](https://arxiv.org/abs/2109.07958)
- [Synod Documentation](../README.md)

## License

Same as Synod plugin (see root LICENSE file)
