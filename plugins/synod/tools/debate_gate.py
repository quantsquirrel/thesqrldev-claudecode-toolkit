#!/usr/bin/env python3
"""
Debate Gate — Feature-flagged pre-gate that decides whether to skip or run full
multi-agent debate after Phase-1 solvers have returned their signals.

Background
----------
Research (DOWN arXiv:2504.05047, iMAD) shows ~60% of queries can skip full
multi-agent debate when round-1 solvers already agree, achieving equal or better
accuracy at ~1.5 vs 3-9 model calls.  This gate inspects already-parsed solver
signals — no extra model calls, CLI-only.

Agreement measurement is a LEXICAL + SIGNAL PROXY.  It compares the primary
claim (first semantic_focus item) of each solver after lowercasing, punctuation
stripping, and trivial stopword removal, then averages pairwise Jaccard
similarities.  This is fast and requires no embeddings or LLM-judge, but it can
miss paraphrased agreement or flag false disagreement on synonyms.
Embeddings/LLM-judge scoring is a documented future upgrade path.

Fail-safe: any error or bad input forces decision='run_debate' — the gate
NEVER skips debate due to malformed data.

Environment overrides
---------------------
SYNOD_DEBATE_GATE            '1' enables gate; default '0' (observe-only)
SYNOD_GATE_AGREE_THRESHOLD   float 0-1, default 0.80
SYNOD_GATE_MIN_CONF          int 0-100, default 80
SYNOD_GATE_HIGH_CONF         int 0-100, default 85
SYNOD_GATE_MIN_TRUST         float 0+, default 1.0  (min per-solver trust_score;
                             absent trust_score defaults to 1.0 so a solver
                             with no trust field still passes this guard)
SYNOD_GATE_MIN_CANEXIT       float 0-1, default 0.5 (min fraction of solvers
                             that must self-report can_exit=True)

Usage
-----
  debate_gate.py --signals-dir <round-1-solver-dir>
  debate_gate.py --signals-json '[{"model":"gpt-4o","confidence":90,...},...]'
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import string
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Constants / configurable defaults
# ---------------------------------------------------------------------------

_DEFAULT_AGREE_THRESHOLD = 0.80
_DEFAULT_MIN_CONF = 80
_DEFAULT_HIGH_CONF = 85
_DEFAULT_MIN_TRUST = 1.0
_DEFAULT_MIN_CANEXIT = 0.5

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "must",
        "can",
        "could",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "from",
        "as",
        "that",
        "this",
        "it",
        "its",
        # NOTE: negation words ("not", "no", "never", "cannot") are deliberately
        # NOT stopwords — stripping them made "X" and "not X" tokenize identically,
        # so two opposite high-confidence claims scored agreement 1.0 and wrongly
        # skipped the debate. Keep negation tokens so contradictions stay visible.
        "and",
        "or",
        "but",
        "so",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, drop stopwords, return token set."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = {t for t in text.split() if t and t not in _STOPWORDS}
    return tokens


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce to float, returning ``default`` on any bad value.

    Keeps the gate fail-OPEN and crash-free: a non-numeric confidence/trust
    field becomes a conservative default (e.g. 0.0) that prevents a skip rather
    than raising an uncaught ValueError mid-decision (the previous inconsistency
    where malformed *shape* fail-safed but a malformed *number* tracebacked).
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


# Negation-bearing tokens. Kept OUT of _STOPWORDS so they survive tokenization,
# and handled explicitly here: plain Jaccard treats "not" as a single differing
# token (high overlap), so "X" and "not X" would look ~80% similar and the gate
# would wrongly skip the debate. _claim_similarity collapses that to ~0.
_NEGATIONS = frozenset(
    {
        "not",
        "no",
        "never",
        "cannot",
        "cant",
        "dont",
        "doesnt",
        "didnt",
        "isnt",
        "arent",
        "wasnt",
        "werent",
        "wont",
        "wouldnt",
        "shouldnt",
        "couldnt",
        "havent",
        "hasnt",
        "hadnt",
        "mustnt",
        "none",
        "neither",
        "nor",
        "without",
    }
)

_FAIL_SAFE_KEY = "_debate_gate_fail_safe"


def _claim_similarity(a: set[str], b: set[str]) -> float:
    """Negation-polarity-aware Jaccard between two primary-claim token sets.

    When the two claims share their semantic (non-negation) tokens but disagree
    on negation parity (one negated, one not), they are contradictory — the more
    semantically similar they are, the STRONGER the contradiction, so the score
    is driven toward 0. Same-parity claims use ordinary semantic Jaccard.
    """
    neg_a = bool(len(a & _NEGATIONS) % 2)
    neg_b = bool(len(b & _NEGATIONS) % 2)
    sem_a = a - _NEGATIONS
    sem_b = b - _NEGATIONS
    j = _jaccard(sem_a, sem_b)
    if neg_a != neg_b:
        return j * (1.0 - j)
    return j


def _run_debate_result(reason: str, n_solvers: int = 0) -> dict[str, Any]:
    return {
        "decision": "run_debate",
        "agreement_score": 0.0,
        "vote_confidence": 0.0,
        "dominant_model": None,
        "n_solvers": n_solvers,
        "rationale": f"fail-safe: {reason}",
        "signals": {
            "claim_agreement": 0.0,
            "frac_can_exit": 0.0,
            "frac_high_conf": 0.0,
            "min_confidence": 0.0,
        },
    }


def _focus_is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


# ---------------------------------------------------------------------------
# Core agreement signals
# ---------------------------------------------------------------------------


def claim_agreement(focus_lists: list[list[str]]) -> float:
    """Average pairwise Jaccard over the PRIMARY claim of each solver.

    Primary claim = first item in semantic_focus list (index 0).
    Returns 0.0 for n < 2.
    """
    primaries = []
    for fl in focus_lists:
        if fl:
            primaries.append(_tokenize(fl[0]))
        else:
            primaries.append(set())

    n = len(primaries)
    if n < 2:
        return 0.0

    pairs = 0
    total = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            total += _claim_similarity(primaries[i], primaries[j])
            pairs += 1

    return total / pairs if pairs else 0.0


def _weighted_vote(signals: list[dict]) -> dict:
    """Weighted vote using trust_score as weight (equal weight if absent).

    Returns: {final_confidence, weights, dominant_model}
    Compatible with synod-parser.weighted_consensus output shape.
    """
    if not signals:
        return {"final_confidence": 0.0, "weights": {}, "dominant_model": None}

    total_trust = sum(_safe_float(s.get("trust_score", 1.0), 1.0) for s in signals)

    if total_trust == 0:
        n = len(signals)
        final = sum(_safe_float(s.get("confidence", 0)) for s in signals) / n
        weights = {s.get("model", f"model_{i}"): round(1.0 / n, 3) for i, s in enumerate(signals)}
    else:
        final = (
            sum(
                _safe_float(s.get("trust_score", 1.0), 1.0) * _safe_float(s.get("confidence", 0))
                for s in signals
            )
            / total_trust
        )
        weights = {
            s.get("model", f"model_{i}"): round(
                _safe_float(s.get("trust_score", 1.0), 1.0) / total_trust, 3
            )
            for i, s in enumerate(signals)
        }

    dominant = max(signals, key=lambda s: _safe_float(s.get("trust_score", 1.0), 1.0))

    return {
        "final_confidence": round(final, 1),
        "weights": weights,
        "dominant_model": dominant.get("model"),
    }


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------


def decide(signals: list[dict]) -> dict[str, Any]:
    """Evaluate solver signals and decide whether to skip or run debate.

    Parameters
    ----------
    signals : list of dicts, each with keys:
        model         (str)
        confidence    (int/float, 0-100)
        can_exit      (bool)
        semantic_focus (list[str])
        trust_score   (float, optional — defaults to 1.0)

    Returns
    -------
    dict with:
        decision        : 'skip_debate' | 'run_debate'
        agreement_score : float 0-1
        vote_confidence : float (weighted consensus confidence)
        dominant_model  : str | None
        n_solvers       : int
        rationale       : str
        signals         : dict of component scores
    """
    # --- Read thresholds from env (allow test/runtime override) ---
    agree_threshold = _env_float("SYNOD_GATE_AGREE_THRESHOLD", _DEFAULT_AGREE_THRESHOLD)
    min_conf = _env_int("SYNOD_GATE_MIN_CONF", _DEFAULT_MIN_CONF)
    high_conf = _env_int("SYNOD_GATE_HIGH_CONF", _DEFAULT_HIGH_CONF)
    min_trust_thresh = _env_float("SYNOD_GATE_MIN_TRUST", _DEFAULT_MIN_TRUST)
    min_canexit = _env_float("SYNOD_GATE_MIN_CANEXIT", _DEFAULT_MIN_CANEXIT)
    gate_enabled = os.environ.get("SYNOD_DEBATE_GATE", "0").strip() == "1"

    # --- Fail-safe: bad/empty input -> run_debate ---
    if not signals or not isinstance(signals, list):
        return _run_debate_result("empty or malformed signals")

    n = len(signals)

    # --- Validate each signal dict (fail-safe on bad shape) ---
    for s in signals:
        if not isinstance(s, dict):
            return _run_debate_result("malformed signal entry (not a dict)", n)
        fail_reason = s.get(_FAIL_SAFE_KEY)
        if isinstance(fail_reason, str):
            return _run_debate_result(fail_reason, n)
        focus = s.get("semantic_focus")
        if focus is not None and not _focus_is_string_list(focus):
            return _run_debate_result("malformed semantic_focus", n)

    # --- Compute component scores ---
    focus_lists = [s.get("semantic_focus") or [] for s in signals]
    ca = claim_agreement(focus_lists)

    confidences = [_safe_float(s.get("confidence", 0)) for s in signals]
    min_confidence_val = min(confidences) if confidences else 0.0
    frac_ce = sum(1 for s in signals if s.get("can_exit", False)) / n
    frac_hc = sum(1 for s in signals if _safe_float(s.get("confidence", 0)) >= high_conf) / n

    # Composite agreement score
    agreement_score = round(0.5 * ca + 0.3 * frac_ce + 0.2 * frac_hc, 4)

    # Weighted vote for confidence and dominant model
    vote_result = _weighted_vote(signals)
    vote_confidence = vote_result["final_confidence"]
    dominant_model = vote_result["dominant_model"]

    # Additional derived values for hardened skip criteria
    min_trust = min(_safe_float(s.get("trust_score", 1.0), 0.0) for s in signals)
    primary_sufficient = all(len(_tokenize(fl[0])) >= 2 if fl else False for fl in focus_lists)

    signal_components = {
        "claim_agreement": round(ca, 4),
        "frac_can_exit": round(frac_ce, 4),
        "frac_high_conf": round(frac_hc, 4),
        "min_confidence": min_confidence_val,
        "min_trust": round(min_trust, 4),
        "vote_confidence": vote_confidence,
        "primary_sufficient": primary_sufficient,
    }

    # --- Gate-off path: compute + report, but always run_debate ---
    if not gate_enabled:
        return {
            "decision": "run_debate",
            "agreement_score": agreement_score,
            "vote_confidence": vote_confidence,
            "dominant_model": dominant_model,
            "n_solvers": n,
            "rationale": (
                "gate disabled (SYNOD_DEBATE_GATE=0); "
                f"would have {'skipped' if _would_skip(agreement_score, min_confidence_val, n, agree_threshold, min_conf, vote_confidence, high_conf, min_trust, min_trust_thresh, frac_ce, min_canexit, primary_sufficient) else 'debated'} "
                "— set SYNOD_DEBATE_GATE=1 to enable"
            ),
            "signals": signal_components,
        }

    # --- Gate-on: apply skip criteria ---
    if _would_skip(
        agreement_score,
        min_confidence_val,
        n,
        agree_threshold,
        min_conf,
        vote_confidence,
        high_conf,
        min_trust,
        min_trust_thresh,
        frac_ce,
        min_canexit,
        primary_sufficient,
    ):
        rationale = (
            f"agreement_score={agreement_score:.3f} >= {agree_threshold}, "
            f"min_confidence={min_confidence_val:.0f} >= {min_conf}, "
            f"vote_confidence={vote_confidence:.1f} >= {high_conf}, "
            f"min_trust={min_trust:.3f} >= {min_trust_thresh}, "
            f"frac_can_exit={frac_ce:.2f} >= {min_canexit}, "
            f"primary_sufficient=True, "
            f"n_solvers={n} >= 2"
        )
        return {
            "decision": "skip_debate",
            "agreement_score": agreement_score,
            "vote_confidence": vote_confidence,
            "dominant_model": dominant_model,
            "n_solvers": n,
            "rationale": rationale,
            "signals": signal_components,
        }
    else:
        reasons = []
        if agreement_score < agree_threshold:
            reasons.append(f"agreement_score={agreement_score:.3f} < {agree_threshold}")
        if min_confidence_val < min_conf:
            reasons.append(f"min_confidence={min_confidence_val:.0f} < {min_conf}")
        if vote_confidence < high_conf:
            reasons.append(f"vote_confidence={vote_confidence:.1f} < {high_conf}")
        if min_trust < min_trust_thresh:
            reasons.append(f"min_trust={min_trust:.3f} < {min_trust_thresh}")
        if frac_ce < min_canexit:
            reasons.append(f"frac_can_exit={frac_ce:.2f} < {min_canexit}")
        if not primary_sufficient:
            reasons.append("primary_sufficient=False (trivial single-token primary claim)")
        if n < 2:
            reasons.append(f"n_solvers={n} < 2")
        return {
            "decision": "run_debate",
            "agreement_score": agreement_score,
            "vote_confidence": vote_confidence,
            "dominant_model": dominant_model,
            "n_solvers": n,
            "rationale": "; ".join(reasons) if reasons else "thresholds not met",
            "signals": signal_components,
        }


def _would_skip(
    agreement_score: float,
    min_confidence_val: float,
    n: int,
    agree_threshold: float,
    min_conf: int,
    vote_confidence: float,
    high_conf: int,
    min_trust: float,
    min_trust_thresh: float,
    frac_ce: float,
    min_canexit: float,
    primary_sufficient: bool,
) -> bool:
    """Return True only when ALL skip conditions are met.

    Conditions (all must hold):
      1. agreement_score >= agree_threshold
      2. min_confidence >= min_conf  (every solver surface confidence)
      3. vote_confidence >= high_conf  (weighted vote must also be high)
      4. min_trust >= min_trust_thresh  (weakest solver trust floor)
      5. frac_can_exit >= min_canexit  (majority self-report done)
      6. primary_sufficient  (all primary claims tokenize to >= 2 tokens)
      7. n >= 2
    """
    return (
        agreement_score >= agree_threshold
        and min_confidence_val >= min_conf
        and vote_confidence >= high_conf
        and min_trust >= min_trust_thresh
        and frac_ce >= min_canexit
        and primary_sufficient
        and n >= 2
    )


# ---------------------------------------------------------------------------
# Loader helpers for CLI
# ---------------------------------------------------------------------------


def load_signals_from_dir(signals_dir: str) -> list[dict]:
    """Load all *-parsed.json files from a directory and extract solver signals.

    Each parsed JSON is expected to have a shape produced by synod-parser
    (confidence.score, confidence.can_exit, semantic_focus).  The file stem
    (minus '-parsed') is used as the model name if the dict has no 'model' key.
    """
    pattern = os.path.join(signals_dir, "*-parsed.json")
    paths = sorted(glob.glob(pattern))
    signals = []
    for path in paths:
        try:
            with open(path) as f:
                data = json.load(f)
            # Normalise synod-parser shape -> gate signal shape
            signal = _normalize_parsed(data, path)
            if signal:
                signals.append(signal)
        except Exception as exc:
            print(
                f"[debate_gate] WARN: unreadable signal file forces debate {path}: {exc}",
                file=sys.stderr,
            )
            signals.append({_FAIL_SAFE_KEY: f"unreadable signal file {path}"})
    return signals


def _normalize_parsed(data: dict, path: str) -> dict | None:
    """Convert a synod-parser output dict to a gate signal dict."""
    if not isinstance(data, dict):
        return {_FAIL_SAFE_KEY: f"malformed parsed signal {path}"}
    conf_block = data.get("confidence") or {}
    model_name = data.get("model") or os.path.basename(path).replace("-parsed.json", "")
    return {
        "model": model_name,
        "confidence": _safe_float(conf_block.get("score", 0)),
        "can_exit": bool(conf_block.get("can_exit", False)),
        "semantic_focus": data.get("semantic_focus") or [],
        "trust_score": _safe_float(data.get("trust_score", 1.0), 1.0),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Debate gate: decide skip_debate vs run_debate from Phase-1 solver signals."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--signals-dir",
        metavar="DIR",
        help="Directory containing *-parsed.json files from round-1 solvers.",
    )
    group.add_argument(
        "--signals-json",
        metavar="JSON",
        help="Inline JSON list of solver signal dicts.",
    )

    args = parser.parse_args()

    try:
        if args.signals_dir:
            signals = load_signals_from_dir(args.signals_dir)
        else:
            signals = json.loads(args.signals_json)
            if not isinstance(signals, list):
                signals = []
    except Exception as exc:
        # Fail-safe: malformed input -> run_debate
        result = {
            "decision": "run_debate",
            "agreement_score": 0.0,
            "vote_confidence": 0.0,
            "dominant_model": None,
            "n_solvers": 0,
            "rationale": f"fail-safe: could not parse input — {exc}",
            "signals": {
                "claim_agreement": 0.0,
                "frac_can_exit": 0.0,
                "frac_high_conf": 0.0,
                "min_confidence": 0.0,
            },
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = decide(signals)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
