# Synod Module: Phase 4.5 — Evidence Coverage Gate

> **NEW in v3.5.0** — post-synthesis coverage check. Annotates the final
> verdict with the % of claims backed by `file:line` citations. Does NOT
> block output — the user sees everything plus the metric.

Only runs when Phase 0.5 was active (i.e., `SYNOD_EVIDENCE_FIRST=1` or
`--evidence-first` was passed). Legacy flow skips this gate.

**Input:** Final synthesis markdown from Phase 4.
**Output:** A single annotation line appended to the user-visible verdict.

---

## Algorithm

1. Parse the Phase 4 synthesis markdown.
2. Enumerate candidate claims: each `- bullet` or `N.` numbered item, excluding:
   - Lines inside fenced code blocks
   - Headers (`#`, `##`, ...)
   - Meta lines starting with "Overall Verdict:", "Summary:", "Top-N:"
3. For each claim, check whether it contains a citation matching
   `\S+\.(py|ts|js|go|rs|java|rb|md|json|toml):\d+` OR `<file>:<start>-<end>`.
4. Compute `coverage = cited_claims / max(total_claims, 1)`.

## Thresholds

| Coverage | Label | Meaning |
|:-:|---|---|
| ≥ 70% | `evidence-based` | Concrete claims mostly traceable |
| 30% – 70% | `partial` | Mix of evidence and narrative; treat with caution |
| < 30% | `narrative-based` | Essentially qualitative opinion, not audit |

## Output format

Append one line to the final verdict, immediately after the last synthesis
section, before any cancellation/shutdown notes:

```
📊 Evidence Coverage: 58% (23/40 claims cite file:line).
   Verdict: partial — mix of evidence and narrative. Consider re-running with
   richer Primary Evidence or accept this as qualitative assessment.
```

For `evidence-based`:
```
📊 Evidence Coverage: 78% (31/40) — verdict is evidence-based.
```

For `narrative-based`:
```
⚠ Evidence Coverage: 18% (7/40) — verdict is narrative-based.
   Treat recommendations as opinion, not audit findings.
```

## Why 70% and not 90%

- 90% is unreachable in natural prose — topic sentences, transitions, and
  judgment calls are legitimately uncitable.
- 50% is too lenient — lets "vibes-based review" pass as evidence.
- 70% empirically forces most concrete recommendations to ground in primary
  evidence while allowing reasonable narrative glue. Tune via
  `config/synod-modes.yaml` → `evidence_gate.min_coverage` if needed.

## Orchestrator implementation

The gate runs in the lead's Phase 4 context — no external CLI call. ~30 lines
of Python on the synthesis markdown is sufficient. See
`tools/evidence_gate.py` for reference implementation (if provided in a
future release) OR implement inline per the pseudocode:

```python
import re

CITATION_RE = re.compile(r"\S+\.(py|ts|js|go|rs|java|rb|md|json|toml):\d+(-\d+)?")
CLAIM_RE = re.compile(r"^\s*(?:-|\*|\d+\.)\s+")

def coverage(markdown: str) -> tuple[int, int]:
    in_code = False
    claims = 0
    cited = 0
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith("#"):
            continue
        if line.lstrip().lower().startswith(("overall verdict:", "summary:", "top-")):
            continue
        if CLAIM_RE.match(line):
            claims += 1
            if CITATION_RE.search(line):
                cited += 1
    return cited, claims
```

The gate is additive — if parsing fails for any reason, skip annotation
rather than blocking output. Synod's rule #3 ("자동 폐기 금지") applies: the
gate informs, the human decides.
