"""
Tests for research-grounded parser functions in synod-parser.py.

Covers:
  1. prune_debate_edges    — CortexDebate CRIS edge pruning (arXiv:2507.03928)
  2. temperature_scale     — logit temperature scaling calibration
  3. platt_scale           — Platt scaling calibration
  4. compute_ece           — Expected Calibration Error
  5. compute_brier         — Brier score
  6. semantic_entropy      — Semantic entropy (Nature 2024 / arXiv:2406.15927)
  7. cluster_by_lexical    — greedy Jaccard clustering proxy
  8. CLI subcommands       — --prune / --ece / --brier / --semantic-entropy
"""

import importlib.util
import json
import math
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Module loading (mirrors pattern in test_synod_parser.py / test_trust_scoring.py)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

spec = importlib.util.spec_from_file_location(
    "synod_parser",
    os.path.join(os.path.dirname(__file__), "..", "tools", "synod-parser.py"),
)
synod_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(synod_parser)

prune_debate_edges = synod_parser.prune_debate_edges
temperature_scale = synod_parser.temperature_scale
platt_scale = synod_parser.platt_scale
compute_ece = synod_parser.compute_ece
compute_brier = synod_parser.compute_brier
semantic_entropy = synod_parser.semantic_entropy
cluster_by_lexical = synod_parser.cluster_by_lexical


# ---------------------------------------------------------------------------
# 1. prune_debate_edges
# ---------------------------------------------------------------------------


class TestPruneDebateEdges:
    """Tests for prune_debate_edges() — CortexDebate arXiv:2507.03928."""

    def _make_scores(self, values):
        """Build trust_scores list from {model_name: trust_score} dict."""
        return [{"model": f"m{i}", "trust_score": v} for i, v in enumerate(values)]

    def test_empty_input(self):
        result = prune_debate_edges([])
        assert result["edges_kept"] == []
        assert result["edges_pruned"] == []
        assert result["pruned_fraction"] == 0.0
        assert result["threshold"] == 0.0

    def test_keeps_only_above_mean(self):
        # mean = (0.5 + 1.0 + 1.5 + 2.0) / 4 = 1.25
        scores = [
            {"model": "low", "trust_score": 0.5},
            {"model": "below", "trust_score": 1.0},
            {"model": "above", "trust_score": 1.5},
            {"model": "high", "trust_score": 2.0},
        ]
        result = prune_debate_edges(scores)
        assert result["threshold"] == pytest.approx(1.25)
        assert set(result["edges_kept"]) == {"above", "high"}
        assert set(result["edges_pruned"]) == {"low", "below"}

    def test_pruned_fraction_correct(self):
        scores = [
            {"model": "a", "trust_score": 0.3},
            {"model": "b", "trust_score": 0.8},
            {"model": "c", "trust_score": 1.2},
            {"model": "d", "trust_score": 1.5},
        ]
        result = prune_debate_edges(scores)
        # mean = (0.3 + 0.8 + 1.2 + 1.5) / 4 = 0.95
        # below mean: a (0.3), kept: b, c, d — wait, 0.8 < 0.95 so pruned too
        # pruned: a, b => fraction = 2/4 = 0.5
        assert result["pruned_fraction"] == pytest.approx(0.5)

    def test_explicit_floor_overrides_mean(self):
        scores = [
            {"model": "x", "trust_score": 0.4},
            {"model": "y", "trust_score": 0.9},
            {"model": "z", "trust_score": 1.5},
        ]
        result = prune_debate_edges(scores, floor=1.0)
        assert result["threshold"] == pytest.approx(1.0)
        assert "z" in result["edges_kept"]
        assert "x" in result["edges_pruned"]
        assert "y" in result["edges_pruned"]

    def test_all_equal_trust_keeps_all(self):
        scores = [{"model": f"m{i}", "trust_score": 1.0} for i in range(5)]
        result = prune_debate_edges(scores)
        assert len(result["edges_kept"]) == 5
        assert len(result["edges_pruned"]) == 0
        assert result["pruned_fraction"] == 0.0

    def test_single_model_always_kept(self):
        scores = [{"model": "solo", "trust_score": 0.7}]
        result = prune_debate_edges(scores)
        assert result["edges_kept"] == ["solo"]
        assert result["edges_pruned"] == []
        assert result["pruned_fraction"] == 0.0

    def test_returns_required_keys(self):
        scores = [{"model": "a", "trust_score": 1.0}]
        result = prune_debate_edges(scores)
        for key in ("edges_kept", "edges_pruned", "pruned_fraction", "threshold"):
            assert key in result

    def test_floor_zero_keeps_all_positive(self):
        scores = [
            {"model": "a", "trust_score": 0.1},
            {"model": "b", "trust_score": 0.5},
        ]
        result = prune_debate_edges(scores, floor=0.0)
        assert len(result["edges_kept"]) == 2
        assert result["pruned_fraction"] == 0.0


# ---------------------------------------------------------------------------
# 2. temperature_scale
# ---------------------------------------------------------------------------


class TestTemperatureScale:
    """Tests for temperature_scale() — logit temperature scaling."""

    def test_identity_at_T_equals_1(self):
        scores = [10.0, 30.0, 50.0, 70.0, 90.0]
        result = temperature_scale(scores, T=1.0)
        for orig, scaled in zip(scores, result):
            assert abs(scaled - orig) < 0.01, f"T=1 should be identity, got {scaled} for {orig}"

    def test_T_greater_than_1_reduces_extremes(self):
        # With T > 1 the logit is shrunk → predictions move toward 50%
        scores = [10.0, 90.0]
        result = temperature_scale(scores, T=2.0)
        assert result[0] > 10.0, "Low score should increase toward 50 with T>1"
        assert result[1] < 90.0, "High score should decrease toward 50 with T>1"

    def test_T_less_than_1_sharpens_extremes(self):
        # T < 1 → logit is amplified → predictions pushed toward 0/100
        scores = [30.0, 70.0]
        result = temperature_scale(scores, T=0.5)
        assert result[0] < 30.0, "Low score should decrease toward 0 with T<1"
        assert result[1] > 70.0, "High score should increase toward 100 with T<1"

    def test_monotonic_ordering_preserved(self):
        scores = [20.0, 40.0, 60.0, 80.0]
        result = temperature_scale(scores, T=3.0)
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1], "Monotonic order must be preserved"

    def test_output_in_0_100_range(self):
        scores = [0.0, 25.0, 50.0, 75.0, 100.0]
        for T in [0.5, 1.0, 2.0, 5.0]:
            result = temperature_scale(scores, T=T)
            for v in result:
                assert 0.0 <= v <= 100.0, f"Out of range for T={T}: {v}"

    def test_invalid_T_raises(self):
        with pytest.raises(ValueError):
            temperature_scale([50.0], T=0.0)
        with pytest.raises(ValueError):
            temperature_scale([50.0], T=-1.0)

    def test_empty_input_returns_empty(self):
        assert temperature_scale([], T=1.0) == []

    def test_symmetric_around_50(self):
        # score s and 100-s should map to x and 100-x
        result = temperature_scale([30.0, 70.0], T=2.0)
        assert abs(result[0] + result[1] - 100.0) < 0.001


# ---------------------------------------------------------------------------
# 3. platt_scale
# ---------------------------------------------------------------------------


class TestPlattScale:
    """Tests for platt_scale() — Platt scaling (logistic calibration)."""

    def test_identity_with_standard_logit_params(self):
        # a=1, b=0 with input p=s/100 → sigmoid(p) ≠ p in general, but
        # for p=0.5 → sigmoid(0.5) = 0.622 — just test it runs without error
        scores = [10.0, 50.0, 90.0]
        result = platt_scale(scores, a=1.0, b=0.0)
        assert len(result) == 3
        for v in result:
            assert 0.0 <= v <= 100.0

    def test_output_range_0_100(self):
        scores = [0.0, 25.0, 50.0, 75.0, 100.0]
        result = platt_scale(scores, a=1.5, b=-0.3)
        for v in result:
            assert 0.0 <= v <= 100.0

    def test_monotonic_for_positive_a(self):
        scores = [10.0, 30.0, 50.0, 70.0, 90.0]
        result = platt_scale(scores, a=2.0, b=0.0)
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1]

    def test_empty_input_returns_empty(self):
        assert platt_scale([], a=1.0, b=0.0) == []

    def test_large_negative_b_shifts_down(self):
        scores = [50.0]
        r_no_shift = platt_scale(scores, a=1.0, b=0.0)
        r_neg_shift = platt_scale(scores, a=1.0, b=-5.0)
        assert r_neg_shift[0] < r_no_shift[0]


# ---------------------------------------------------------------------------
# 4. compute_ece
# ---------------------------------------------------------------------------


class TestComputeECE:
    """Tests for compute_ece() — Expected Calibration Error."""

    def test_empty_input_returns_zero(self):
        assert compute_ece([], []) == 0.0

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            compute_ece([0.5, 0.8], [True])

    def test_perfect_calibration_returns_zero(self):
        # Perfect calibration: predicted prob == empirical accuracy in each bin.
        # Use pred=1.0 (last bin) for all-correct samples so acc=1.0 == conf=1.0.
        pred_probs = [1.0] * 10
        correct = [True] * 10
        ece = compute_ece(pred_probs, correct)
        assert ece == pytest.approx(0.0, abs=1e-5)

    def test_over_confident_has_positive_ece(self):
        # Predict 0.9 for everything but only half are correct
        pred_probs = [0.9] * 10
        correct = [True] * 5 + [False] * 5
        ece = compute_ece(pred_probs, correct)
        assert ece > 0.0

    def test_perfectly_wrong_has_large_ece(self):
        # Always predict 1.0 but always wrong
        pred_probs = [1.0] * 10
        correct = [False] * 10
        ece = compute_ece(pred_probs, correct)
        assert ece == pytest.approx(1.0, abs=1e-5)

    def test_ece_in_0_1_range(self):
        pred_probs = [0.1, 0.3, 0.5, 0.7, 0.9]
        correct = [False, False, True, True, True]
        ece = compute_ece(pred_probs, correct)
        assert 0.0 <= ece <= 1.0

    def test_single_sample(self):
        ece = compute_ece([0.8], [True])
        # |1.0 - 0.8| * (1/1) = 0.2
        assert ece == pytest.approx(0.2, abs=1e-5)

    def test_n_bins_parameter(self):
        pred_probs = [0.1, 0.3, 0.5, 0.7, 0.9]
        correct = [False, True, True, True, True]
        ece5 = compute_ece(pred_probs, correct, n_bins=5)
        ece10 = compute_ece(pred_probs, correct, n_bins=10)
        # Both must be valid floats in [0, 1]; they may differ
        assert 0.0 <= ece5 <= 1.0
        assert 0.0 <= ece10 <= 1.0


# ---------------------------------------------------------------------------
# 5. compute_brier
# ---------------------------------------------------------------------------


class TestComputeBrier:
    """Tests for compute_brier() — Brier score."""

    def test_empty_input_returns_zero(self):
        assert compute_brier([], []) == 0.0

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            compute_brier([0.5], [True, False])

    def test_perfect_predictions_return_zero(self):
        # Always predict 1.0 and always correct
        brier = compute_brier([1.0] * 5, [True] * 5)
        assert brier == pytest.approx(0.0, abs=1e-5)

    def test_worst_case_returns_one(self):
        # Always predict 1.0 but always wrong
        brier = compute_brier([1.0] * 5, [False] * 5)
        assert brier == pytest.approx(1.0, abs=1e-5)

    def test_random_guess_at_half(self):
        # Predicting 0.5 for everything: Brier = 0.25
        brier = compute_brier([0.5] * 10, [True] * 5 + [False] * 5)
        assert brier == pytest.approx(0.25, abs=1e-5)

    def test_brier_in_0_1_range(self):
        probs = [0.1, 0.4, 0.6, 0.9, 0.3]
        correct = [False, True, True, True, False]
        brier = compute_brier(probs, correct)
        assert 0.0 <= brier <= 1.0

    def test_single_sample_correct(self):
        # pred=0.8, correct=True → (0.8 - 1.0)^2 = 0.04
        brier = compute_brier([0.8], [True])
        assert brier == pytest.approx(0.04, abs=1e-5)

    def test_single_sample_wrong(self):
        # pred=0.8, correct=False → (0.8 - 0.0)^2 = 0.64
        brier = compute_brier([0.8], [False])
        assert brier == pytest.approx(0.64, abs=1e-5)

    def test_lower_is_better(self):
        # Good predictions should have lower Brier than bad ones
        good = compute_brier([0.9, 0.1], [True, False])
        bad = compute_brier([0.1, 0.9], [True, False])
        assert good < bad


# ---------------------------------------------------------------------------
# 6. semantic_entropy
# ---------------------------------------------------------------------------


class TestSemanticEntropy:
    """Tests for semantic_entropy() — Nature 2024 / arXiv:2406.15927."""

    def test_empty_returns_zero(self):
        assert semantic_entropy([]) == 0.0

    def test_all_same_cluster_returns_zero(self):
        # All answers in cluster 0 → P(0)=1.0 → H = 0
        assert semantic_entropy([0, 0, 0, 0, 0]) == pytest.approx(0.0)

    def test_all_distinct_clusters_maximum_entropy(self):
        # Each answer in its own cluster → uniform distribution → H = log(N)
        clusters = list(range(4))
        h = semantic_entropy(clusters)
        expected = math.log(4)
        assert h == pytest.approx(expected, abs=1e-5)

    def test_two_equal_clusters_half_bit(self):
        # 2 clusters, 2 samples each → H = log(2)
        h = semantic_entropy([0, 0, 1, 1])
        assert h == pytest.approx(math.log(2), abs=1e-5)

    def test_entropy_increases_with_diversity(self):
        # More distinct clusters → higher entropy
        h_low = semantic_entropy([0, 0, 0, 1])  # mostly one cluster
        h_high = semantic_entropy([0, 1, 2, 3])  # all distinct
        assert h_low < h_high

    def test_single_sample(self):
        # P(0) = 1 → H = 0
        assert semantic_entropy([0]) == pytest.approx(0.0)

    def test_non_zero_cluster_ids_work(self):
        # Cluster IDs need not start at 0
        h = semantic_entropy([5, 5, 7, 7])
        assert h == pytest.approx(math.log(2), abs=1e-5)

    def test_entropy_is_non_negative(self):
        for clusters in [[0], [0, 1], [0, 0, 1, 2], [3, 3, 3]]:
            assert semantic_entropy(clusters) >= 0.0


# ---------------------------------------------------------------------------
# 7. cluster_by_lexical
# ---------------------------------------------------------------------------


class TestClusterByLexical:
    """Tests for cluster_by_lexical() — greedy Jaccard-based clustering."""

    def test_empty_input_returns_empty(self):
        assert cluster_by_lexical([]) == []

    def test_single_item_cluster_zero(self):
        result = cluster_by_lexical(["hello world"])
        assert result == [0]

    def test_identical_answers_same_cluster(self):
        answers = ["the cat sat on the mat", "the cat sat on the mat"]
        result = cluster_by_lexical(answers)
        assert result[0] == result[1]

    def test_paraphrases_grouped_together(self):
        # High overlap → should be in the same cluster
        a1 = "deep learning is a subset of machine learning"
        a2 = "deep learning is part of machine learning subset"
        result = cluster_by_lexical([a1, a2], threshold=0.4)
        assert result[0] == result[1], "Paraphrases should cluster together"

    def test_unrelated_answers_distinct_clusters(self):
        a1 = "the capital of France is Paris"
        a2 = "photosynthesis converts sunlight into glucose"
        result = cluster_by_lexical([a1, a2], threshold=0.6)
        assert result[0] != result[1]

    def test_output_length_matches_input(self):
        answers = ["foo bar", "baz qux", "foo bar baz", "hello world"]
        result = cluster_by_lexical(answers)
        assert len(result) == len(answers)

    def test_cluster_ids_are_integers(self):
        result = cluster_by_lexical(["a b c", "d e f"])
        for cid in result:
            assert isinstance(cid, int)

    def test_threshold_0_groups_all(self):
        # threshold=0.0 → every answer matches the first cluster
        answers = ["completely different", "totally unrelated", "nothing in common here"]
        result = cluster_by_lexical(answers, threshold=0.0)
        assert all(c == 0 for c in result)

    def test_threshold_1_splits_all(self):
        # threshold=1.0 → only exact duplicates cluster; distinct answers split
        answers = ["foo bar", "baz qux", "hello world"]
        result = cluster_by_lexical(answers, threshold=1.0)
        assert len(set(result)) == 3

    def test_high_entropy_from_distinct_clusters(self):
        # Each distinct answer → distinct cluster → high entropy
        answers = ["alpha beta", "gamma delta", "epsilon zeta", "eta theta"]
        clusters = cluster_by_lexical(answers, threshold=0.9)
        h = semantic_entropy(clusters)
        assert h > 0.0

    def test_low_entropy_from_paraphrases(self):
        # Near-identical answers → one cluster → entropy near 0
        base = "machine learning is a powerful technique"
        answers = [
            base,
            "machine learning is a powerful technique indeed",
            "machine learning is a technique powerful in nature",
        ]
        clusters = cluster_by_lexical(answers, threshold=0.3)
        h = semantic_entropy(clusters)
        # Should be 0 (all in one cluster) or very low
        assert h < math.log(2)


# ---------------------------------------------------------------------------
# 8. CLI subcommands
# ---------------------------------------------------------------------------


class TestCLISubcommands:
    """Tests for --prune / --ece / --brier / --semantic-entropy CLI flags."""

    def test_prune_cli(self, capsys):
        sys.argv = [
            "synod-parser",
            "--prune",
            "claude:1.5",
            "gemini:0.8",
            "openai:1.2",
        ]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "edges_kept" in output
        assert "edges_pruned" in output
        assert "pruned_fraction" in output
        assert "threshold" in output

    def test_prune_cli_keeps_above_mean(self, capsys):
        # mean = (1.5 + 0.8 + 1.2) / 3 = 1.167; kept: claude(1.5), openai(1.2)
        sys.argv = [
            "synod-parser",
            "--prune",
            "claude:1.5",
            "gemini:0.8",
            "openai:1.2",
        ]
        with pytest.raises(SystemExit):
            synod_parser.main()
        output = json.loads(capsys.readouterr().out)
        assert "claude" in output["edges_kept"]
        assert "gemini" in output["edges_pruned"]

    def test_ece_cli(self, capsys):
        # perfect calibration: pred=1.0 all correct → acc=1.0 == conf=1.0 → ECE=0
        sys.argv = ["synod-parser", "--ece"] + ["1.0:true"] * 10
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "ece" in output
        assert output["ece"] == pytest.approx(0.0, abs=1e-5)

    def test_ece_cli_over_confident(self, capsys):
        # 0.9 predictions but only 50% correct → ECE > 0
        sys.argv = ["synod-parser", "--ece"] + ["0.9:true"] * 5 + ["0.9:false"] * 5
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["ece"] > 0.0

    def test_brier_cli(self, capsys):
        sys.argv = ["synod-parser", "--brier", "0.9:true", "0.1:false", "0.8:true"]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "brier" in output
        assert 0.0 <= output["brier"] <= 1.0

    def test_brier_cli_perfect(self, capsys):
        sys.argv = ["synod-parser", "--brier"] + ["1.0:true"] * 5
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["brier"] == pytest.approx(0.0, abs=1e-5)

    def test_semantic_entropy_cli_all_same(self, capsys):
        sys.argv = ["synod-parser", "--semantic-entropy", "0", "0", "0", "0"]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "semantic_entropy" in output
        assert output["semantic_entropy"] == pytest.approx(0.0)

    def test_semantic_entropy_cli_all_distinct(self, capsys):
        sys.argv = ["synod-parser", "--semantic-entropy", "0", "1", "2", "3"]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["semantic_entropy"] == pytest.approx(math.log(4), abs=1e-5)
