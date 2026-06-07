#!/usr/bin/env python3
"""
Synod Response Parser - Extract SID signals from model responses.

Usage:
  echo "response" | synod-parser
  synod-parser "response"
  synod-parser --validate "response"  # Check format only
  synod-parser --trust C R I S        # Calculate Trust Score
  synod-parser --prune model1:0.8 model2:1.2 model3:0.5   # CRIS edge pruning
  synod-parser --ece pred1:bool1 pred2:bool2 ...           # Expected Calibration Error
  synod-parser --brier pred1:bool1 pred2:bool2 ...         # Brier score
  synod-parser --semantic-entropy cluster1 cluster2 ...    # Semantic entropy

Research functions note
-----------------------
calibration params (T, a, b) in temperature_scale / platt_scale require a
held-out calibration set (future work); the functions are tested as pure math
now.  semantic_entropy / cluster_by_lexical need N-sample solver runs (future
infra) — tested as pure functions now.
"""

import argparse
import json
import math
import re
import sys
from typing import Any, Optional


def validate_format(text: str) -> dict[str, bool]:
    """Check if response has required XML format."""
    return {
        "has_confidence": bool(re.search(r"<confidence[^>]*>.*?</confidence>", text, re.DOTALL)),
        "has_score": bool(re.search(r'<confidence\s+score="\d+"', text)),
        "has_semantic_focus": bool(
            re.search(r"<semantic_focus>.*?</semantic_focus>", text, re.DOTALL)
        ),
        "is_valid": all(
            [
                re.search(r"<confidence[^>]*>.*?</confidence>", text, re.DOTALL),
                re.search(r"<semantic_focus>.*?</semantic_focus>", text, re.DOTALL),
            ]
        ),
    }


def extract_confidence(text: str) -> Optional[dict[str, Any]]:
    """Extract confidence block from response."""
    pattern = r'<confidence\s+score="(\d+)">(.*?)</confidence>'
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return None

    score = max(0, min(100, int(match.group(1))))
    inner = match.group(2)

    # Extract sub-elements
    evidence = re.search(r"<evidence>(.*?)</evidence>", inner, re.DOTALL)
    logic = re.search(r"<logic>(.*?)</logic>", inner, re.DOTALL)
    expertise = re.search(r"<expertise>(.*?)</expertise>", inner, re.DOTALL)
    can_exit = re.search(r"<can_exit>(.*?)</can_exit>", inner, re.DOTALL)

    return {
        "score": score,
        "evidence": evidence.group(1).strip() if evidence else None,
        "logic": logic.group(1).strip() if logic else None,
        "expertise": expertise.group(1).strip() if expertise else None,
        "can_exit": can_exit.group(1).strip().lower() == "true" if can_exit else False,
    }


def extract_semantic_focus(text: str) -> list[str]:
    """Extract semantic focus points."""
    pattern = r"<semantic_focus>(.*?)</semantic_focus>"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return []

    content = match.group(1).strip()
    # Split by newlines or numbered items. The split consumes the newline
    # before each "N. " marker for items 1..N, but the first item starts at
    # content.strip() with no leading newline, so its "N. " prefix survives.
    # Strip a leading numeric prefix from every item to make output uniform.
    items = re.split(r"\n\s*\d+\.\s*|\n", content)
    return [re.sub(r"^\d+\.\s*", "", item.strip()) for item in items if item.strip()]


def extract_key_sentences(text: str, limit: int = 3) -> list[str]:
    """Extract key sentences when semantic_focus is missing."""
    # Remove XML tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Split into sentences
    sentences = re.split(r"[.!?]\s+", clean)
    # Return first N non-empty sentences
    return [s.strip() for s in sentences if len(s.strip()) > 20][:limit]


def calculate_trust_score(c: float, r: float, i: float, s: float) -> dict[str, Any]:
    """
    Calculate CortexDebate Trust Score.
    T = (C x R x I) / S

    Args:
        c: Credibility (0-1)
        r: Reliability (0-1)
        i: Informativeness (Intimacy) (0-1)
        s: Self-Orientation (0.1-1)
    """
    if s < 0.1:
        s = 0.1  # Minimum to avoid extreme values

    trust = min((c * r * i) / s, 2.0)  # Capped at 2.0 per CortexDebate spec

    return {
        "credibility": c,
        "reliability": r,
        "intimacy": i,
        "self_orientation": s,
        "trust_score": round(trust, 3),
        "include": trust >= 0.5,
        "rating": "high"
        if trust >= 1.5
        else "good"
        if trust >= 1.0
        else "acceptable"
        if trust >= 0.5
        else "low",
    }


def calculate_confidence_interval(
    scores: list[float],
    confidence_level: float = 0.95,
    upper_bound: Optional[float] = None,
) -> dict:
    """Calculate confidence interval for a set of scores.

    Uses t-distribution for small samples (n < 30).

    Args:
        scores: List of numeric scores
        confidence_level: Confidence level (default 0.95 for 95% CI)
        upper_bound: Optional upper clamp for the result (e.g. 2.0 for trust
            scores on a 0-2 scale).  When None, no upper clamp is applied.
            The lower bound is always clamped to 0.

    Returns:
        Dict with mean, lower, upper, margin, n
    """
    import math

    n = len(scores)
    if n == 0:
        return {"mean": 0, "lower": 0, "upper": 0, "margin": 0, "n": 0}
    if n == 1:
        return {"mean": scores[0], "lower": scores[0], "upper": scores[0], "margin": 0, "n": 1}

    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
    std_dev = math.sqrt(variance)

    # t-distribution critical values for common confidence levels.
    # Keys are degrees of freedom (n - 1).
    t_values = {
        1: {0.95: 12.706, 0.90: 6.314},
        2: {0.95: 4.303, 0.90: 2.920},
        3: {0.95: 3.182, 0.90: 2.353},
        4: {0.95: 2.776, 0.90: 2.132},
        5: {0.95: 2.571, 0.90: 2.015},
    }

    if n - 1 in t_values and confidence_level in t_values[n - 1]:
        t_crit = t_values[n - 1][confidence_level]
    else:
        t_crit = 1.96  # z-approximation for larger samples

    margin = t_crit * (std_dev / math.sqrt(n))

    raw_upper = mean + margin
    upper = round(min(upper_bound, raw_upper) if upper_bound is not None else raw_upper, 3)

    return {
        "mean": round(mean, 3),
        "lower": round(max(0, mean - margin), 3),
        "upper": upper,
        "margin": round(margin, 3),
        "n": n,
    }


def weighted_consensus(model_scores: list[dict]) -> dict:
    """Calculate weighted consensus from multiple model trust scores.

    Implements: FINAL = Σ(T_i × C_i) / Σ(T_i)
    where T = trust score, C = confidence score.

    Args:
        model_scores: List of dicts with keys: model, trust_score, confidence

    Returns:
        Dict with final_confidence, weights, dominant_model
    """
    if not model_scores:
        return {"final_confidence": 0, "weights": {}, "dominant_model": None}

    total_trust = sum(s["trust_score"] for s in model_scores)
    if total_trust == 0:
        # Equal weighting fallback
        n = len(model_scores)
        final = sum(s["confidence"] for s in model_scores) / n
        weights = {s["model"]: round(1.0 / n, 3) for s in model_scores}
    else:
        final = sum(s["trust_score"] * s["confidence"] for s in model_scores) / total_trust
        weights = {s["model"]: round(s["trust_score"] / total_trust, 3) for s in model_scores}

    dominant = max(model_scores, key=lambda s: s["trust_score"])

    return {
        "final_confidence": round(final, 1),
        "weights": weights,
        "dominant_model": dominant["model"],
    }


def prune_debate_edges(
    trust_scores: list[dict],
    keep_above_mean: bool = True,
    floor: Optional[float] = None,
) -> dict:
    """Filter debate edges so only high-trust sources drive discussion.

    Implements the CortexDebate edge-pruning mechanism (arXiv:2507.03928)
    that achieves ~70% token savings by dropping low-credibility directed
    edges before the next round of responses.

    Args:
        trust_scores: List of dicts with keys ``model`` (str) and
            ``trust_score`` (float).
        keep_above_mean: When True (default) the threshold is the mean trust
            score across all models.  When False you must supply ``floor``.
        floor: Explicit threshold to use instead of the mean.  Overrides
            ``keep_above_mean`` when provided.

    Returns:
        Dict with keys:
            edges_kept      – list of model names whose edges are kept
            edges_pruned    – list of model names whose edges are dropped
            pruned_fraction – fraction of edges dropped (0.0 – 1.0)
            threshold       – the trust-score cutoff that was applied
    """
    if not trust_scores:
        return {
            "edges_kept": [],
            "edges_pruned": [],
            "pruned_fraction": 0.0,
            "threshold": 0.0,
        }

    scores = [s["trust_score"] for s in trust_scores]
    if floor is not None:
        threshold = floor
    else:
        threshold = sum(scores) / len(scores)

    kept = [s["model"] for s in trust_scores if s["trust_score"] >= threshold]
    pruned = [s["model"] for s in trust_scores if s["trust_score"] < threshold]
    total = len(trust_scores)
    pruned_fraction = round(len(pruned) / total, 4) if total > 0 else 0.0

    return {
        "edges_kept": kept,
        "edges_pruned": pruned,
        "pruned_fraction": pruned_fraction,
        "threshold": round(threshold, 6),
    }


# ---------------------------------------------------------------------------
# Confidence calibration
# NOTE: temperature_scale / platt_scale parameters (T, a, b) require a
# held-out calibration set for fitting — they are pure math functions here.
# ---------------------------------------------------------------------------


def temperature_scale(scores: list[float], T: float) -> list[float]:
    """Apply logit temperature scaling to a list of 0-100 SID confidence scores.

    Converts each score s to a probability p = s/100, applies logit
    temperature scaling in probability space (softmax with temperature T),
    then converts back to 0-100.

    T > 1 spreads the distribution (reduces extremes, increases calibration).
    T < 1 sharpens it (pushes toward 0/1).
    T = 1 is identity.

    Args:
        scores: List of confidence scores in [0, 100].
        T:      Temperature parameter (> 0).

    Returns:
        List of rescaled scores in [0, 100].
    """
    if T <= 0:
        raise ValueError("Temperature T must be > 0")

    result = []
    for s in scores:
        p = max(1e-7, min(1 - 1e-7, s / 100.0))
        logit = math.log(p / (1.0 - p))
        scaled_logit = logit / T
        p_scaled = 1.0 / (1.0 + math.exp(-scaled_logit))
        result.append(round(p_scaled * 100.0, 6))
    return result


def platt_scale(scores: list[float], a: float, b: float) -> list[float]:
    """Apply Platt scaling (logistic regression calibration) to 0-100 scores.

    Maps each score s via sigmoid(a * s/100 + b) then back to 0-100.
    Parameters a and b are fit on a held-out calibration set (future work).

    Args:
        scores: List of confidence scores in [0, 100].
        a:      Slope parameter (fit on calibration data).
        b:      Intercept parameter (fit on calibration data).

    Returns:
        List of calibrated scores in [0, 100].
    """
    result = []
    for s in scores:
        p = s / 100.0
        calibrated = 1.0 / (1.0 + math.exp(-(a * p + b)))
        result.append(round(calibrated * 100.0, 6))
    return result


def compute_ece(
    pred_probs: list[float],
    correct: list[bool],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE).

    Bins predictions by confidence, then computes the weighted average of
    |accuracy - confidence| across bins.

    Args:
        pred_probs: Predicted probabilities in [0, 1].
        correct:    Ground-truth labels (True = correct prediction).
        n_bins:     Number of equal-width bins (default 10).

    Returns:
        ECE as a float in [0, 1].  0.0 = perfectly calibrated.
    """
    if len(pred_probs) != len(correct):
        raise ValueError("pred_probs and correct must have the same length")
    if not pred_probs:
        return 0.0

    n = len(pred_probs)
    bin_size = 1.0 / n_bins
    ece = 0.0

    for b in range(n_bins):
        lo = b * bin_size
        hi = lo + bin_size
        # Include upper edge in last bin
        indices = [
            i for i, p in enumerate(pred_probs) if lo <= p < hi or (b == n_bins - 1 and p == 1.0)
        ]
        if not indices:
            continue
        bin_n = len(indices)
        avg_conf = sum(pred_probs[i] for i in indices) / bin_n
        avg_acc = sum(1 for i in indices if correct[i]) / bin_n
        ece += (bin_n / n) * abs(avg_acc - avg_conf)

    return round(ece, 6)


def compute_brier(pred_probs: list[float], correct: list[bool]) -> float:
    """Compute the Brier score (mean squared error of probability forecasts).

    Args:
        pred_probs: Predicted probabilities in [0, 1].
        correct:    Ground-truth labels (True = correct prediction).

    Returns:
        Brier score in [0, 1].  0.0 = perfect, 1.0 = maximally wrong.
    """
    if len(pred_probs) != len(correct):
        raise ValueError("pred_probs and correct must have the same length")
    if not pred_probs:
        return 0.0

    n = len(pred_probs)
    total = sum((p - (1.0 if c else 0.0)) ** 2 for p, c in zip(pred_probs, correct))
    return round(total / n, 6)


# ---------------------------------------------------------------------------
# Semantic entropy (Nature 2024 / arXiv:2406.15927)
# NOTE: semantic_entropy needs N-sample solver runs (future infra); tested as
# a pure function now.  cluster_by_lexical is a logit-free proxy; embedding-
# based clustering is documented as future work.
# ---------------------------------------------------------------------------


def semantic_entropy(answer_clusters: list[int]) -> float:
    """Compute entropy over cluster-id assignments of N sampled answers.

    High entropy indicates the model generates semantically diverse answers
    for the same prompt, which correlates with hallucination / confabulation
    (Nature 2024, arXiv:2406.15927).

    Args:
        answer_clusters: List of integer cluster IDs, one per sampled answer.
            Cluster IDs provided by the caller (via cluster_by_lexical or a
            future embedding-based clusterer).

    Returns:
        Shannon entropy H (nats) over cluster distribution.
        0.0 = all answers in the same cluster (confident/consistent).
        log(k) = uniform over k clusters (maximum uncertainty).
    """
    if not answer_clusters:
        return 0.0

    n = len(answer_clusters)
    counts: dict = {}
    for c in answer_clusters:
        counts[c] = counts.get(c, 0) + 1

    entropy = 0.0
    for cnt in counts.values():
        p = cnt / n
        entropy -= p * math.log(p)

    return round(entropy, 6)


def cluster_by_lexical(answers: list[str], threshold: float = 0.6) -> list[int]:
    """Greedily cluster answers by Jaccard token overlap (logit-free proxy).

    Assigns each answer to the first existing cluster whose representative
    has Jaccard similarity >= threshold, or opens a new cluster.

    Args:
        answers:   List of answer strings to cluster.
        threshold: Minimum Jaccard similarity to join an existing cluster
                   (default 0.6).

    Returns:
        List of integer cluster IDs (same length as ``answers``).
    """

    def _jaccard(a: str, b: str) -> float:
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union

    cluster_ids: list[int] = []
    # Representatives: one answer string per cluster
    representatives: list[str] = []

    for answer in answers:
        assigned = -1
        for cid, rep in enumerate(representatives):
            if _jaccard(answer, rep) >= threshold:
                assigned = cid
                break
        if assigned == -1:
            assigned = len(representatives)
            representatives.append(answer)
        cluster_ids.append(assigned)

    return cluster_ids


def apply_defaults(text: str) -> dict[str, Any]:
    """Apply default values for malformed responses."""
    return {
        "confidence": {
            "score": 50,
            "evidence": None,
            "logic": None,
            "expertise": None,
            "can_exit": False,
        },
        "semantic_focus": extract_key_sentences(text, 3),
        "format_warning": "Model did not comply with SID format - defaults applied",
    }


def _compute_metrics(text: str, parsed: dict) -> dict:
    """Compute debate quality metrics from a parsed response."""
    conf = parsed.get("confidence") or {}
    return {
        "response_length": len(text),
        "format_compliance": parsed.get("validation", {}).get("is_valid", False),
        "confidence_score": conf.get("score", 0),
        "semantic_focus_count": len(parsed.get("semantic_focus", [])),
        "has_evidence": conf.get("evidence") is not None,
        "has_logic": conf.get("logic") is not None,
        "has_code": parsed.get("has_code", False),
    }


def collect_round_metrics(parsed_results: list) -> dict:
    """Aggregate metrics from multiple parse results for a debate round."""
    if not parsed_results:
        return {
            "avg_confidence": 0,
            "compliance_rate": 0,
            "total_responses": 0,
            "avg_response_length": 0,
            "total_semantic_focuses": 0,
        }

    n = len(parsed_results)
    metrics_list = [r["metrics"] for r in parsed_results]
    return {
        "avg_confidence": round(sum(m["confidence_score"] for m in metrics_list) / n),
        "compliance_rate": sum(1 for m in metrics_list if m["format_compliance"]),
        "total_responses": n,
        "avg_response_length": round(sum(m["response_length"] for m in metrics_list) / n),
        "total_semantic_focuses": sum(m["semantic_focus_count"] for m in metrics_list),
    }


def format_metrics_summary(metrics: dict) -> str:
    """Return a human-readable one-line summary of round metrics."""
    return (
        f"토론 품질: confidence 평균 {metrics['avg_confidence']}%, "
        f"format 준수율 {metrics['compliance_rate']}/{metrics['total_responses']}, "
        f"semantic focus 총 {metrics['total_semantic_focuses']}개"
    )


def parse_response(text: str) -> dict[str, Any]:
    """Parse full response and extract all SID signals."""
    validation = validate_format(text)

    if not validation["is_valid"]:
        result = apply_defaults(text)
        result["validation"] = validation
        result["metrics"] = _compute_metrics(text, result)
        return result

    result = {
        "confidence": extract_confidence(text),
        "semantic_focus": extract_semantic_focus(text),
        "validation": validation,
        "raw_length": len(text),
        "has_code": bool(re.search(r"```[\w]*\n", text)),
    }

    # Calculate derived metrics
    if result["confidence"]:
        result["can_exit_early"] = result["confidence"].get("can_exit", False)
        result["high_confidence"] = result["confidence"]["score"] >= 90

    result["metrics"] = _compute_metrics(text, result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Parse Synod SID signals")
    parser.add_argument("text", nargs="?", help="Response text to parse")
    parser.add_argument("--validate", action="store_true", help="Only validate format")
    parser.add_argument(
        "--trust",
        nargs=4,
        type=float,
        metavar=("C", "R", "I", "S"),
        help="Calculate Trust Score from C R I S values",
    )
    parser.add_argument(
        "--consensus",
        nargs="+",
        type=str,
        help="Calculate weighted consensus: model1:trust:confidence model2:trust:confidence ...",
    )
    parser.add_argument(
        "--prune",
        nargs="+",
        type=str,
        metavar="MODEL:TRUST",
        help="CRIS edge pruning: model1:trust_score model2:trust_score ...",
    )
    parser.add_argument(
        "--ece",
        nargs="+",
        type=str,
        metavar="PROB:CORRECT",
        help="Expected Calibration Error: prob1:true prob2:false ... (prob in 0-1)",
    )
    parser.add_argument(
        "--brier",
        nargs="+",
        type=str,
        metavar="PROB:CORRECT",
        help="Brier score: prob1:true prob2:false ... (prob in 0-1)",
    )
    parser.add_argument(
        "--semantic-entropy",
        nargs="+",
        type=int,
        metavar="CLUSTER_ID",
        dest="semantic_entropy",
        help="Semantic entropy over cluster-id assignments: 0 1 0 2 1 ...",
    )

    args = parser.parse_args()

    # CRIS edge pruning mode
    if args.prune:
        trust_scores = []
        for entry in args.prune:
            parts = entry.split(":")
            if len(parts) == 2:
                trust_scores.append({"model": parts[0], "trust_score": float(parts[1])})
        result = prune_debate_edges(trust_scores)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # ECE mode
    if args.ece:
        probs: list[float] = []
        labels: list[bool] = []
        for entry in args.ece:
            parts = entry.split(":")
            if len(parts) == 2:
                probs.append(float(parts[0]))
                labels.append(parts[1].lower() in ("true", "1", "yes"))
        result = {"ece": compute_ece(probs, labels)}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Brier score mode
    if args.brier:
        probs = []
        labels = []
        for entry in args.brier:
            parts = entry.split(":")
            if len(parts) == 2:
                probs.append(float(parts[0]))
                labels.append(parts[1].lower() in ("true", "1", "yes"))
        result = {"brier": compute_brier(probs, labels)}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Semantic entropy mode
    if args.semantic_entropy is not None:
        result = {"semantic_entropy": semantic_entropy(args.semantic_entropy)}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Consensus calculation mode
    if args.consensus:
        scores = []
        for entry in args.consensus:
            parts = entry.split(":")
            if len(parts) == 3:
                scores.append(
                    {
                        "model": parts[0],
                        "trust_score": float(parts[1]),
                        "confidence": float(parts[2]),
                    }
                )
        result = weighted_consensus(scores)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Trust score calculation mode
    if args.trust:
        result = calculate_trust_score(*args.trust)
        print(json.dumps(result, indent=2))
        return

    # Get input text
    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Usage: synod-parser 'response' or echo 'response' | synod-parser", file=sys.stderr)
        sys.exit(1)

    # Validation only mode
    if args.validate:
        result = validate_format(text)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["is_valid"] else 1)

    # Full parse
    result = parse_response(text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
