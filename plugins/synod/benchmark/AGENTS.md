<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2025-01-31 -->

# Benchmark Suite - Agent Reference

This directory contains the rigorous evaluation framework for Synod v3.0's multi-model deliberation capabilities. Agents working here orchestrate large-scale benchmarks comparing Synod's mathematical reasoning and truthfulness against industry baselines.

## Directory Overview

```
benchmark/
├── README.md                    # Benchmark suite documentation
├── config.yaml                  # Configuration (models, sample size, costs)
├── requirements.txt             # Benchmark-specific dependencies
├── __init__.py                  # Package initialization
├── run_gsm8k.py                 # GSM8K benchmark runner (Phase 1)
├── evaluator.py                 # Evaluation logic & metrics calculation
├── baselines.py                 # Baseline performance references
├── analyze.py                   # Result analysis & reporting utilities
├── data/                        # Input datasets (gitignored in results)
├── results/                     # Output results & measurements (gitignored)
└── scripts/                     # Helper scripts for automation
    ├── download_datasets.py     # Dataset acquisition
    ├── validate_config.py       # Config validation
    └── cost_estimator.py        # Cost analysis tools
```

## File Reference

### Core Execution
- **run_gsm8k.py**: Main benchmark runner for Phase 1 (GSM8K). Orchestrates model evaluation, result tracking, and baseline comparison.
- **evaluator.py**: Implements evaluation metrics (accuracy, confidence, deliberation quality), response parsing, and answer extraction.
- **baselines.py**: Provides baseline implementations (Claude-only, GPT-4o-only, Majority Vote, Self-Consistency).
- **analyze.py**: Generates reports, statistical comparisons, and result visualization utilities.

### Configuration & Dependencies
- **config.yaml**: Single source of truth for benchmark settings:
  - Model versions (Claude, Gemini, GPT-4o)
  - Sample sizes and random seeds
  - Cost budgets and API limits
  - Synod deliberation rounds/modes
  - Baseline selection
- **requirements.txt**: Benchmark-specific Python packages (datasets, anthropic, openai, google-genai, pandas, numpy, scipy, tqdm, pyyaml, rich)
- **__init__.py**: Package initialization

### Data Management
- **data/**: Input dataset cache (GSM8K, TruthfulQA)
- **results/**: Output files with timestamped naming:
  - `gsm8k_synod_TIMESTAMP.json` - Synod deliberation responses
  - `gsm8k_claude_TIMESTAMP.json` - Claude-only baseline
  - `gsm8k_gpt4o_TIMESTAMP.json` - GPT-4o baseline
  - `gsm8k_majority_TIMESTAMP.json` - Majority vote results
  - `gsm8k_report_TIMESTAMP.html` - Summary report

### Utility Scripts
- **scripts/download_datasets.py**: Fetches GSM8K and TruthfulQA from Hugging Face
- **scripts/validate_config.py**: Validates config.yaml structure and values
- **scripts/cost_estimator.py**: Pre-calculates API costs before benchmark run

## Working Instructions for AI Agents

### Environment Setup

```bash
# 1. Install benchmark dependencies
cd /Users/ahnjundaram_g/dev/tools/synod-plugin
pip install -e ".[benchmark]"

# 2. Or install from requirements.txt directly
pip install -r benchmark/requirements.txt

# 3. Set required API keys (must be set before execution)
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
```

### Running Benchmarks

**Phase 1 - GSM8K (Mathematical Reasoning)**
```bash
cd benchmark/
python run_gsm8k.py --phase gsm8k
```

Options:
- `--methods synod,claude_only,gpt4o_only,majority_vote` - Select specific baselines
- `--synod-rounds 2` - Override deliberation rounds (2 or 3)
- `--synod-mode review` - Override deliberation mode (review/design/debug/general)
- `--sample-size 100` - Override dataset size for testing

**Phase 2 - TruthfulQA (Truthfulness)** - Future
```bash
python run_truthfulqa.py --phase truthfulqa
```

### Configuration Management

Edit `config.yaml` to customize:

```yaml
# Reduce cost for testing
benchmarks:
  gsm8k:
    sample_size: 50  # Default: 300

# Adjust Synod deliberation
synod:
  rounds: 2  # Faster (2 rounds), less thorough
  mode: "general"

# Select baselines to run
baselines:
  claude_only: true
  gpt4o_only: true
  majority_vote: true
  self_consistency: false  # Expensive
```

Validate config before running:
```bash
python scripts/validate_config.py
```

### Cost Management

**Pre-benchmark estimation:**
```bash
python scripts/cost_estimator.py --sample-size 300
# Output: Estimated cost: $75 for Synod, $55 for Majority Vote, etc.
```

**Cost per question (Phase 1 - GSM8K):**
- Synod v3.0 (3 rounds): ~$0.25/question
- Claude-only: ~$0.08/question
- GPT-4o-only: ~$0.10/question
- Majority Vote: ~$0.18/question

**Cost optimization:**
1. Reduce `sample_size` in config.yaml (300 → 100 = 1/3 cost)
2. Disable expensive baselines (self_consistency: false)
3. Reduce rounds (synod.rounds: 2 instead of 3)
4. Use smaller models (if available in future phases)

### Result Analysis

```bash
# Analyze specific benchmark results
python analyze.py results/gsm8k_synod_20250131_143022.json

# Compare multiple runs
python analyze.py results/gsm8k_*.json --compare

# Generate HTML report
python analyze.py results/ --report
```

## Common Patterns

### Sequential Execution (Default)
```yaml
execution:
  parallel_workers: 1  # IMPORTANT: Keep 1 for rate limiting
  delay_between_requests: 2  # Minimum 2 seconds
  retry_attempts: 3
```

Rate limits (Jan 2025):
- Anthropic Claude: ~10k tokens/minute
- OpenAI GPT-4o: ~90k tokens/minute
- Google Gemini: ~1000 requests/minute

Sequential processing (parallel_workers: 1) respects all limits automatically.

### Automatic Retry & Timeout

```yaml
execution:
  timeout_seconds: 300  # 5 minutes per question
  retry_attempts: 3     # Retry failed requests
```

Failures handled:
- Rate limit → Exponential backoff (2s, 4s, 8s)
- Timeout → Retry with increased delay
- API error → Retry up to 3 times
- Invalid response → Mark as failed, log details

### Progress Tracking

Real-time display during execution:
```
Processing GSM8K [████████░░░] 240/300 (80%)
Synod: 87.5% | Claude: 78.3% | GPT-4o: 81.7% | Majority: 84.5%
Cost: $60.00 / $100.00 budget | ETA: 5 min
```

## Testing Requirements

### Validation Workflow
1. **Config validation** before benchmark start:
   ```bash
   python scripts/validate_config.py
   ```

2. **Cost estimation** for budget planning:
   ```bash
   python scripts/cost_estimator.py
   ```

3. **Single question test** before full run:
   ```bash
   python run_gsm8k.py --sample-size 1 --methods synod
   ```

4. **Results verification** after completion:
   ```bash
   python analyze.py results/gsm8k_synod_*.json --validate
   ```

### Expected Output Files
After successful benchmark run:
- `results/gsm8k_synod_TIMESTAMP.json` (exists and valid JSON)
- `results/gsm8k_claude_TIMESTAMP.json` (if claude_only enabled)
- `results/gsm8k_gpt4o_TIMESTAMP.json` (if gpt4o_only enabled)
- `results/gsm8k_majority_TIMESTAMP.json` (if majority_vote enabled)
- `results/gsm8k_report_TIMESTAMP.html` (if generate_report enabled)

### Common Issues & Troubleshooting

| Issue | Solution |
|-------|----------|
| API key not found | Set environment variables: `export ANTHROPIC_API_KEY=...` |
| Rate limit errors | Increase `delay_between_requests` in config.yaml |
| Timeout errors | Increase `timeout_seconds` or reduce `sample_size` |
| Out of memory | Reduce `sample_size` or increase `batch_size` |
| Invalid config | Run `python scripts/validate_config.py` |
| Missing datasets | Run `python scripts/download_datasets.py` |

## Dependencies

### Internal (Synod Plugin)
- `synod-parser` (from tools/)
- Claude, Gemini, OpenAI integrations

### External (Python packages)
- `datasets>=2.14.0` - Benchmark datasets (GSM8K, TruthfulQA)
- `anthropic>=0.18.0` - Claude API client
- `openai>=1.0.0` - GPT-4o API client
- `google-genai>=1.0.0` - Gemini API client
- `pandas>=2.0.0` - Data analysis and CSV handling
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.10.0` - Statistical functions
- `tqdm>=4.65.0` - Progress bars
- `pyyaml>=6.0` - YAML configuration parsing
- `rich>=13.0.0` - Terminal formatting and tables

### Installing Dependencies
```bash
# From synod-plugin root
pip install -e ".[benchmark]"

# Or directly from benchmark/requirements.txt
pip install -r benchmark/requirements.txt
```

## Benchmark Phases

### Phase 1: GSM8K (In Progress)
- **Focus**: Mathematical reasoning evaluation
- **Dataset**: 300 grade school math problems
- **Metric**: Exact match accuracy
- **Timeline**: January 2025
- **Status**: Framework complete, initial runs starting
- **Models**: Gemini + OpenAI (Phase 2 adds Claude)

### Phase 2: TruthfulQA (Planned)
- **Focus**: Hallucination/truthfulness evaluation
- **Dataset**: 300 multiple-choice questions
- **Metric**: MC1 accuracy
- **Timeline**: February 2025
- **Status**: Script structure ready (run_truthfulqa.py placeholder)
- **Models**: Full Synod (Claude + GPT-4o + Gemini)

## Performance Targets (Phase 1 Validation)

Synod v3.0 is considered validated if:
- ✅ Accuracy exceeds all single-model baselines
- ✅ Accuracy ≥ Majority Vote baseline
- ✅ Cost per question < $0.50
- ✅ Results are reproducible (same seed)

Example target metrics:
| Method | Target Accuracy | Cost/Q |
|--------|-----------------|--------|
| Synod v3.0 | >87% | ~$0.25 |
| Claude-only | ~78% | ~$0.08 |
| GPT-4o-only | ~81% | ~$0.10 |
| Majority Vote | ~84% | ~$0.18 |

## Monitoring & Logging

### Console Output
- Real-time progress bars with accuracy tracking
- Cost tracking against budget
- Estimated time remaining
- Error summaries

### Log Files (Future)
- `benchmark.log` - Execution logs
- `cost_tracking.json` - Per-question costs
- `timing_metrics.json` - Response latencies

### Result Files
All outputs timestamped and organized by method:
```
results/
├── gsm8k_synod_20250131_143022.json
├── gsm8k_claude_20250131_143022.json
├── gsm8k_gpt4o_20250131_143022.json
├── gsm8k_majority_20250131_143022.json
└── gsm8k_report_20250131_143022.html
```

## Advanced Usage for Agents

### Parallel Multiple Benchmarks
```bash
# Run multiple benchmark configs in sequence
for config in config_*.yaml; do
  SYNOD_CONFIG=$config python run_gsm8k.py --phase gsm8k
done
```

### Custom Evaluation Metrics
Extend `evaluator.py`:
```python
from evaluator import BaseEvaluator

class CustomEvaluator(BaseEvaluator):
    def compute_metric(self, responses, answers):
        # Custom metric logic
        pass
```

### Baseline Extension
Add new baseline in `baselines.py`:
```python
class MyBaseline(BaselineMethod):
    def evaluate(self, questions):
        # Implementation
        pass
```

## Key Contacts & References

- **Synod Documentation**: See root README.md
- **GSM8K Paper**: https://arxiv.org/abs/2110.14168
- **TruthfulQA Paper**: https://arxiv.org/abs/2109.07958
- **Benchmark Progress**: Check CHANGELOG.md for updates

## Agent Checklist for Benchmark Tasks

When working on benchmark tasks, ensure:

- [ ] API keys are set (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY)
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Config validated: `python scripts/validate_config.py`
- [ ] Cost estimated before running: `python scripts/cost_estimator.py`
- [ ] Single-question test passes: `python run_gsm8k.py --sample-size 1`
- [ ] Full benchmark runs to completion
- [ ] Results files verified in `results/` directory
- [ ] Report generated and reviewed
- [ ] Cost stayed within budget
- [ ] No errors in benchmark execution logs

---

**Last Updated**: 2025-01-31
**Framework Status**: Phase 1 GSM8K ready, Phase 2 TruthfulQA planned
**Cost Tracking**: All API calls tracked and logged per question
