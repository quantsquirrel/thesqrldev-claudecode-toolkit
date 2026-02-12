"""Tests for CRIS trust score enhancements - confidence intervals and weighted consensus."""

import os
import sys
import importlib.util

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

# Import synod-parser.py using importlib
spec = importlib.util.spec_from_file_location(
    "synod_parser", os.path.join(os.path.dirname(__file__), "..", "tools", "synod-parser.py")
)
synod_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(synod_parser)

# Import functions
calculate_confidence_interval = synod_parser.calculate_confidence_interval
calculate_trust_score = synod_parser.calculate_trust_score
weighted_consensus = synod_parser.weighted_consensus


class TestConfidenceInterval:
    """Tests for calculate_confidence_interval function."""

    def test_confidence_interval_empty_scores(self):
        """Empty scores should return all zeros."""
        result = calculate_confidence_interval([])
        assert result["mean"] == 0
        assert result["lower"] == 0
        assert result["upper"] == 0
        assert result["margin"] == 0
        assert result["n"] == 0

    def test_confidence_interval_single_score(self):
        """Single score should have margin=0 and mean=score."""
        result = calculate_confidence_interval([1.5])
        assert result["mean"] == 1.5
        assert result["lower"] == 1.5
        assert result["upper"] == 1.5
        assert result["margin"] == 0
        assert result["n"] == 1

    def test_confidence_interval_two_scores(self):
        """Two scores should use t-distribution."""
        scores = [1.0, 1.5]
        result = calculate_confidence_interval(scores)

        assert result["n"] == 2
        assert result["mean"] == 1.25
        assert result["lower"] < result["mean"]
        assert result["upper"] > result["mean"]
        assert result["margin"] > 0

    def test_confidence_interval_multiple_scores(self):
        """Multiple scores should have mean within bounds."""
        scores = [1.0, 1.2, 1.4, 1.6, 1.8]
        result = calculate_confidence_interval(scores)

        assert result["n"] == 5
        assert result["lower"] <= result["mean"] <= result["upper"]
        assert result["margin"] > 0

    def test_confidence_interval_bounds_clamped(self):
        """Confidence interval should be clamped to [0, 2.0]."""
        # Test lower bound clamping
        low_scores = [0.01, 0.02, 0.03]
        result_low = calculate_confidence_interval(low_scores)
        assert result_low["lower"] >= 0

        # Test upper bound clamping
        high_scores = [1.95, 1.98, 2.0]
        result_high = calculate_confidence_interval(high_scores)
        assert result_high["upper"] <= 2.0

    def test_confidence_interval_90_percent(self):
        """90% CI should be narrower than 95% CI."""
        scores = [1.0, 1.2, 1.4, 1.6, 1.8]

        result_95 = calculate_confidence_interval(scores, confidence_level=0.95)
        result_90 = calculate_confidence_interval(scores, confidence_level=0.90)

        assert result_90["margin"] < result_95["margin"]
        assert result_90["upper"] - result_90["lower"] < result_95["upper"] - result_95["lower"]


class TestWeightedConsensus:
    """Tests for weighted_consensus function."""

    def test_weighted_consensus_empty(self):
        """Empty model scores should return final=0."""
        result = weighted_consensus([])
        assert result["final_confidence"] == 0
        assert result["weights"] == {}
        assert result["dominant_model"] is None

    def test_weighted_consensus_single_model(self):
        """Single model should have weight=1.0."""
        scores = [{"model": "gpt-4", "trust_score": 1.5, "confidence": 90}]
        result = weighted_consensus(scores)

        assert result["final_confidence"] == 90
        assert result["weights"]["gpt-4"] == 1.0
        assert result["dominant_model"] == "gpt-4"

    def test_weighted_consensus_equal_trust(self):
        """Equal trust scores should give equal weights."""
        scores = [
            {"model": "gpt-4", "trust_score": 1.0, "confidence": 80},
            {"model": "claude", "trust_score": 1.0, "confidence": 90},
        ]
        result = weighted_consensus(scores)

        assert result["weights"]["gpt-4"] == 0.5
        assert result["weights"]["claude"] == 0.5
        assert result["final_confidence"] == 85.0

    def test_weighted_consensus_higher_trust_gets_more_weight(self):
        """Higher trust score should get more weight."""
        scores = [
            {"model": "gpt-4", "trust_score": 1.5, "confidence": 80},
            {"model": "claude", "trust_score": 0.5, "confidence": 90},
        ]
        result = weighted_consensus(scores)

        assert result["weights"]["gpt-4"] > result["weights"]["claude"]
        assert result["weights"]["gpt-4"] == 0.75
        assert result["weights"]["claude"] == 0.25
        # Weighted average: (1.5 * 80 + 0.5 * 90) / 2.0 = (120 + 45) / 2 = 82.5
        assert result["final_confidence"] == 82.5

    def test_weighted_consensus_zero_trust_fallback(self):
        """Zero trust scores should use equal weighting fallback."""
        scores = [
            {"model": "gpt-4", "trust_score": 0.0, "confidence": 80},
            {"model": "claude", "trust_score": 0.0, "confidence": 90},
        ]
        result = weighted_consensus(scores)

        assert result["weights"]["gpt-4"] == 0.5
        assert result["weights"]["claude"] == 0.5
        assert result["final_confidence"] == 85.0

    def test_weighted_consensus_dominant_model_identified(self):
        """Dominant model should be the one with highest trust score."""
        scores = [
            {"model": "gpt-4", "trust_score": 1.8, "confidence": 80},
            {"model": "claude", "trust_score": 1.2, "confidence": 90},
            {"model": "gemini", "trust_score": 1.5, "confidence": 85},
        ]
        result = weighted_consensus(scores)

        assert result["dominant_model"] == "gpt-4"

    def test_weighted_consensus_formula_verification(self):
        """Verify the weighted consensus formula manually."""
        scores = [
            {"model": "gpt-4", "trust_score": 1.0, "confidence": 80},
            {"model": "claude", "trust_score": 2.0, "confidence": 90},
        ]
        result = weighted_consensus(scores)

        # Manual calculation:
        # Total trust = 1.0 + 2.0 = 3.0
        # Weight(gpt-4) = 1.0 / 3.0 = 0.333
        # Weight(claude) = 2.0 / 3.0 = 0.667
        # Final = (1.0 * 80 + 2.0 * 90) / 3.0 = (80 + 180) / 3.0 = 86.667

        assert result["weights"]["gpt-4"] == 0.333
        assert result["weights"]["claude"] == 0.667
        assert result["final_confidence"] == 86.7


class TestTrustScoreRegression:
    """Tests for existing calculate_trust_score to verify it still works."""

    def test_trust_score_high_trust(self):
        """High CRIS values should produce T >= 1.5."""
        result = calculate_trust_score(c=0.9, r=0.9, i=0.9, s=0.4)
        assert result["trust_score"] >= 1.5
        assert result["rating"] == "high"
        assert result["include"] is True

    def test_trust_score_cap_at_2(self):
        """Trust score should be capped at 2.0."""
        result = calculate_trust_score(c=1.0, r=1.0, i=1.0, s=0.1)
        assert result["trust_score"] == 2.0
        assert result["rating"] == "high"

    def test_trust_score_low_bias(self):
        """Low self-orientation should give higher score."""
        result_low_s = calculate_trust_score(c=0.8, r=0.8, i=0.8, s=0.2)
        result_high_s = calculate_trust_score(c=0.8, r=0.8, i=0.8, s=0.8)

        assert result_low_s["trust_score"] > result_high_s["trust_score"]

    def test_trust_score_acceptable_range(self):
        """Trust score in acceptable range (0.5-1.0)."""
        result = calculate_trust_score(c=0.7, r=0.7, i=0.7, s=0.5)
        assert 0.5 <= result["trust_score"] < 1.0
        assert result["rating"] == "acceptable"
        assert result["include"] is True

    def test_trust_score_low_rating(self):
        """Low trust score should be rated as 'low'."""
        result = calculate_trust_score(c=0.3, r=0.3, i=0.3, s=0.8)
        assert result["trust_score"] < 0.5
        assert result["rating"] == "low"
        assert result["include"] is False

    def test_trust_score_good_rating(self):
        """Good trust score should be rated as 'good'."""
        result = calculate_trust_score(c=0.8, r=0.8, i=0.8, s=0.5)
        assert 1.0 <= result["trust_score"] < 1.5
        assert result["rating"] == "good"
        assert result["include"] is True

    def test_trust_score_minimum_s_clamp(self):
        """Self-orientation below 0.1 should be clamped."""
        result = calculate_trust_score(c=0.5, r=0.5, i=0.5, s=0.05)
        # s should be clamped to 0.1
        assert result["self_orientation"] == 0.1
        assert result["trust_score"] == min((0.5 * 0.5 * 0.5) / 0.1, 2.0)
