"""Tests for tools/debate_gate.py — debate-vs-vote pre-gate.

Covers:
- High agreement + high confidence -> skip_debate (flag ON only)
- Divergent primary claims -> run_debate
- All-high-conf but low claim overlap -> run_debate
- Flag OFF -> always run_debate even on perfect agreement
- n=1 -> run_debate
- Empty / malformed signals -> run_debate (fail-safe)
- Threshold override via env
- Weighted vote dominant correctness
- CLI --signals-dir loads *-parsed.json files
- Hardened guards: low trust, minority can_exit, trivial primary, low vote_confidence
"""

import importlib.util
import json
import os
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Load debate_gate (non-hyphenated, plain import also works but keep uniform
# style with test_tier_routing.py for consistency)
# ---------------------------------------------------------------------------
_gate_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "debate_gate.py"
)
_spec = importlib.util.spec_from_file_location("debate_gate", _gate_path)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# Qualifies under all hardened skip criteria:
#   agreement_score >= 0.80 (high ca + all can_exit + all high_conf -> composite high)
#   min_confidence >= 80
#   vote_confidence >= 85 (trust-weighted)
#   min_trust >= 1.0  (all trust_score=1.1+)
#   frac_can_exit >= 0.5  (all three can_exit=True)
#   primary_sufficient=True  (all primaries have >= 2 meaningful tokens)
_AGREEING_SIGNALS = [
    {
        "model": "gpt-4o",
        "confidence": 92,
        "can_exit": True,
        "semantic_focus": ["Python is faster than Ruby for CPU-bound tasks"],
        "trust_score": 1.2,
    },
    {
        "model": "gemini-flash",
        "confidence": 88,
        "can_exit": True,
        "semantic_focus": ["Python is faster than Ruby for CPU-bound tasks"],
        "trust_score": 1.0,
    },
    {
        "model": "claude-sonnet",
        "confidence": 90,
        "can_exit": True,
        "semantic_focus": ["Python faster Ruby CPU-bound tasks"],
        "trust_score": 1.1,
    },
]

_DIVERGING_SIGNALS = [
    {
        "model": "gpt-4o",
        "confidence": 90,
        "can_exit": True,
        "semantic_focus": ["Python is faster than Ruby for CPU-bound tasks"],
        "trust_score": 1.0,
    },
    {
        "model": "gemini-flash",
        "confidence": 88,
        "can_exit": False,
        "semantic_focus": ["Ruby excels at developer productivity and meta-programming"],
        "trust_score": 1.0,
    },
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure gate env vars are reset to defaults before each test."""
    for var in (
        "SYNOD_DEBATE_GATE",
        "SYNOD_GATE_AGREE_THRESHOLD",
        "SYNOD_GATE_MIN_CONF",
        "SYNOD_GATE_HIGH_CONF",
        "SYNOD_GATE_MIN_TRUST",
        "SYNOD_GATE_MIN_CANEXIT",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


# ---------------------------------------------------------------------------
# claim_agreement
# ---------------------------------------------------------------------------


class TestClaimAgreement:
    def test_identical_claims_return_one(self):
        """Identical primary claims -> Jaccard = 1.0."""
        focus = [["Python is faster than Ruby"], ["Python is faster than Ruby"]]
        assert _gate.claim_agreement(focus) == pytest.approx(1.0)

    def test_completely_different_claims_return_zero(self):
        """Completely different token sets -> Jaccard = 0.0."""
        focus = [["Python speed benchmarks"], ["Ruby metaprogramming elegance"]]
        score = _gate.claim_agreement(focus)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_partial_overlap(self):
        """Partial token overlap returns value between 0 and 1."""
        focus = [["Python is fast"], ["Python is slow"]]
        score = _gate.claim_agreement(focus)
        assert 0.0 < score < 1.0

    def test_n_less_than_2_returns_zero(self):
        """Single solver -> cannot compute pairwise -> 0.0."""
        assert _gate.claim_agreement([["Python is fast"]]) == 0.0
        assert _gate.claim_agreement([]) == 0.0

    def test_empty_focus_lists(self):
        """Empty focus lists treated as empty token sets."""
        score = _gate.claim_agreement([[], []])
        # Both empty -> Jaccard(empty, empty) = 1.0
        assert score == pytest.approx(1.0)

    def test_stopwords_stripped(self):
        """Stopwords removed before comparison."""
        # "the is a" vs "and or but" -> after stopword removal both empty
        focus = [["the is a"], ["and or but"]]
        score = _gate.claim_agreement(focus)
        # Both reduce to empty sets -> 1.0
        assert score == pytest.approx(1.0)

    def test_three_solvers_average(self):
        """Three identical solvers -> pairwise average = 1.0."""
        focus = [["fast python cpu"], ["fast python cpu"], ["fast python cpu"]]
        assert _gate.claim_agreement(focus) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# decide — gate OFF (default)
# ---------------------------------------------------------------------------


class TestDecideGateOff:
    def test_gate_off_always_run_debate(self):
        """With SYNOD_DEBATE_GATE unset, always returns run_debate."""
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["decision"] == "run_debate"

    def test_gate_off_still_computes_signals(self):
        """Even with gate off, signal components are populated for observability."""
        result = _gate.decide(_AGREEING_SIGNALS)
        assert "agreement_score" in result
        assert "signals" in result
        sigs = result["signals"]
        assert "claim_agreement" in sigs
        assert "frac_can_exit" in sigs
        assert "frac_high_conf" in sigs
        assert "min_confidence" in sigs

    def test_gate_off_rationale_mentions_flag(self):
        """Rationale explains gate is disabled."""
        result = _gate.decide(_AGREEING_SIGNALS)
        assert "SYNOD_DEBATE_GATE" in result["rationale"]

    def test_gate_off_perfect_agreement_still_run_debate(self, monkeypatch):
        """Even perfect agreement signals produce run_debate when flag is off."""
        monkeypatch.delenv("SYNOD_DEBATE_GATE", raising=False)
        perfect = [
            {
                "model": "a",
                "confidence": 99,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 99,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby"],
                "trust_score": 1.0,
            },
        ]
        result = _gate.decide(perfect)
        assert result["decision"] == "run_debate"


# ---------------------------------------------------------------------------
# decide — gate ON
# ---------------------------------------------------------------------------


class TestDecideGateOn:
    def test_high_agreement_high_conf_skip_debate(self, monkeypatch):
        """High agreement + high confidence -> skip_debate when gate is on."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["decision"] == "skip_debate"

    def test_diverging_claims_run_debate(self, monkeypatch):
        """Divergent primary claims -> run_debate even with gate on."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(_DIVERGING_SIGNALS)
        assert result["decision"] == "run_debate"

    def test_all_high_conf_but_low_claim_overlap_run_debate(self, monkeypatch):
        """High confidence but low claim overlap -> run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 95,
                "can_exit": True,
                "semantic_focus": ["Python speed benchmarks"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 95,
                "can_exit": True,
                "semantic_focus": ["Ruby metaprogramming elegance"],
                "trust_score": 1.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"

    def test_n_equals_1_run_debate(self, monkeypatch):
        """Single solver is never enough to skip debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide([_AGREEING_SIGNALS[0]])
        assert result["decision"] == "run_debate"
        assert result["n_solvers"] == 1

    def test_low_min_confidence_run_debate(self, monkeypatch):
        """Min confidence below threshold -> run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 50,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby slow"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 50,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby slow"],
                "trust_score": 1.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"

    def test_skip_decision_includes_required_keys(self, monkeypatch):
        """skip_debate result includes all required output keys."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["decision"] == "skip_debate"
        for key in (
            "decision",
            "agreement_score",
            "vote_confidence",
            "dominant_model",
            "n_solvers",
            "rationale",
            "signals",
        ):
            assert key in result

    def test_n_solvers_correct(self, monkeypatch):
        """n_solvers reflects actual number of signals."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["n_solvers"] == len(_AGREEING_SIGNALS)


# ---------------------------------------------------------------------------
# decide — fail-safe on bad input
# ---------------------------------------------------------------------------


class TestDecideFailSafe:
    def test_empty_list_run_debate(self, monkeypatch):
        """Empty signals list -> run_debate (fail-safe)."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide([])
        assert result["decision"] == "run_debate"

    def test_none_run_debate(self, monkeypatch):
        """None input -> run_debate (fail-safe)."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(None)
        assert result["decision"] == "run_debate"

    def test_malformed_signal_entry_run_debate(self, monkeypatch):
        """Non-dict signal entry -> run_debate (fail-safe)."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(["not a dict", "also not a dict"])
        assert result["decision"] == "run_debate"

    def test_fail_safe_rationale_descriptive(self, monkeypatch):
        """Fail-safe rationale describes the failure."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide([])
        assert "fail-safe" in result["rationale"]


# ---------------------------------------------------------------------------
# decide — threshold env overrides
# ---------------------------------------------------------------------------


class TestThresholdOverrides:
    def test_higher_threshold_prevents_skip(self, monkeypatch):
        """Raising agree threshold beyond current score forces run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        monkeypatch.setenv("SYNOD_GATE_AGREE_THRESHOLD", "0.99")
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["decision"] == "run_debate"

    def test_lower_threshold_allows_skip(self, monkeypatch):
        """Lowering agree threshold below current score allows skip_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        monkeypatch.setenv("SYNOD_GATE_AGREE_THRESHOLD", "0.01")
        monkeypatch.setenv("SYNOD_GATE_MIN_CONF", "1")
        monkeypatch.setenv("SYNOD_GATE_HIGH_CONF", "1")
        monkeypatch.setenv("SYNOD_GATE_MIN_TRUST", "0.0")
        signals = [
            {
                "model": "a",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 1.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "skip_debate"

    def test_min_conf_override(self, monkeypatch):
        """Raising MIN_CONF forces run_debate even when claim agreement is high."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        monkeypatch.setenv("SYNOD_GATE_MIN_CONF", "99")
        result = _gate.decide(_AGREEING_SIGNALS)
        assert result["decision"] == "run_debate"

    def test_high_conf_override_affects_frac_high_conf(self, monkeypatch):
        """Raising HIGH_CONF threshold changes frac_high_conf component."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        monkeypatch.setenv("SYNOD_GATE_HIGH_CONF", "99")
        result_high = _gate.decide(_AGREEING_SIGNALS)

        monkeypatch.setenv("SYNOD_GATE_HIGH_CONF", "50")
        result_low = _gate.decide(_AGREEING_SIGNALS)

        # With threshold=99, no solver qualifies as high-conf (all < 99)
        assert result_high["signals"]["frac_high_conf"] == 0.0
        # With threshold=50, all solvers qualify
        assert result_low["signals"]["frac_high_conf"] == 1.0


# ---------------------------------------------------------------------------
# decide — weighted vote dominant correctness
# ---------------------------------------------------------------------------


class TestWeightedVote:
    def test_dominant_model_is_highest_trust(self, monkeypatch):
        """dominant_model is the solver with highest trust_score."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "low-trust",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 0.5,
            },
            {
                "model": "high-trust",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 2.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["dominant_model"] == "high-trust"

    def test_equal_trust_dominant_model_set(self, monkeypatch):
        """With equal trust scores a dominant model is still selected."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 1.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["dominant_model"] in ("a", "b")

    def test_no_trust_score_equal_weight_fallback(self, monkeypatch):
        """Signals without trust_score fall back to equal weighting."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 80,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
            },
            {
                "model": "b",
                "confidence": 80,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
            },
        ]
        result = _gate.decide(signals)
        assert result["vote_confidence"] == pytest.approx(80.0, abs=0.5)

    def test_vote_confidence_weighted_correctly(self, monkeypatch):
        """vote_confidence is weighted average of confidences by trust_score."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        # trust: a=1, b=3 -> weights 0.25/0.75 -> expected: 0.25*60 + 0.75*100 = 90
        signals = [
            {
                "model": "a",
                "confidence": 60,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 1.0,
            },
            {
                "model": "b",
                "confidence": 100,
                "can_exit": True,
                "semantic_focus": ["Python fast ruby"],
                "trust_score": 3.0,
            },
        ]
        result = _gate.decide(signals)
        assert result["vote_confidence"] == pytest.approx(90.0, abs=0.5)


# ---------------------------------------------------------------------------
# CLI --signals-dir
# ---------------------------------------------------------------------------


class TestCLISignalsDir:
    def test_signals_dir_loads_parsed_json(self, monkeypatch, capsys):
        """--signals-dir loads *-parsed.json files and produces a decision JSON."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write two agreeing parsed JSON files (synod-parser output shape)
            for name in ("gpt-4o", "gemini-flash"):
                data = {
                    "confidence": {"score": 90, "can_exit": True},
                    "semantic_focus": ["Python is faster than Ruby for CPU-bound tasks"],
                    "trust_score": 1.0,
                }
                path = os.path.join(tmpdir, f"{name}-parsed.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            sys.argv = ["debate_gate.py", "--signals-dir", tmpdir]
            with pytest.raises(SystemExit) as exc_info:
                _gate.main()
            assert exc_info.value.code == 0

        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["n_solvers"] == 2
        assert "decision" in result

    def test_signals_dir_skips_bad_files(self, monkeypatch, capsys):
        """Bad JSON files in signals-dir are skipped; gate still returns a decision."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            # One valid file
            valid = {
                "confidence": {"score": 90, "can_exit": True},
                "semantic_focus": ["X"],
                "trust_score": 1.0,
            }
            with open(os.path.join(tmpdir, "model-a-parsed.json"), "w") as f:
                json.dump(valid, f)
            # One corrupt file
            with open(os.path.join(tmpdir, "model-b-parsed.json"), "w") as f:
                f.write("NOT JSON {{{")

            sys.argv = ["debate_gate.py", "--signals-dir", tmpdir]
            with pytest.raises(SystemExit) as exc_info:
                _gate.main()
            assert exc_info.value.code == 0

        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["decision"] == "run_debate"
        assert result["n_solvers"] == 2
        assert "fail-safe" in result["rationale"]

    def test_signals_dir_corrupt_file_forces_run_debate(self, monkeypatch, capsys):
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            valid = {
                "confidence": {"score": 95, "can_exit": True},
                "semantic_focus": ["Python is faster than Ruby for CPU-bound tasks"],
                "trust_score": 1.2,
            }
            for name in ("model-a", "model-b"):
                with open(os.path.join(tmpdir, f"{name}-parsed.json"), "w") as f:
                    json.dump(valid, f)
            with open(os.path.join(tmpdir, "model-c-parsed.json"), "w") as f:
                f.write("NOT JSON {{{")

            sys.argv = ["debate_gate.py", "--signals-dir", tmpdir]
            with pytest.raises(SystemExit) as exc_info:
                _gate.main()
            assert exc_info.value.code == 0

        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["decision"] == "run_debate"
        assert "fail-safe" in result["rationale"]

    def test_cli_signals_json_inline(self, monkeypatch, capsys):
        """--signals-json with inline JSON produces a decision."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        payload = json.dumps(_AGREEING_SIGNALS)
        sys.argv = ["debate_gate.py", "--signals-json", payload]
        with pytest.raises(SystemExit) as exc_info:
            _gate.main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["decision"] == "skip_debate"

    def test_cli_empty_dir_run_debate(self, monkeypatch, capsys):
        """Empty signals-dir (no *-parsed.json) -> run_debate (fail-safe)."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            sys.argv = ["debate_gate.py", "--signals-dir", tmpdir]
            with pytest.raises(SystemExit) as exc_info:
                _gate.main()
            assert exc_info.value.code == 0

        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["decision"] == "run_debate"

    def test_cli_malformed_json_run_debate(self, monkeypatch, capsys):
        """Malformed --signals-json -> run_debate (fail-safe)."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        sys.argv = ["debate_gate.py", "--signals-json", "NOT JSON {{{"]
        with pytest.raises(SystemExit) as exc_info:
            _gate.main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["decision"] == "run_debate"
        assert "fail-safe" in result["rationale"]


# ---------------------------------------------------------------------------
# Hardened guard tests — each test fails exactly ONE new guard
# ---------------------------------------------------------------------------


class TestHardenedGuards:
    def _base_skip_signals(self):
        """Two solvers that satisfy ALL hardened skip criteria."""
        return [
            {
                "model": "a",
                "confidence": 92,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby CPU tasks"],
                "trust_score": 1.2,
            },
            {
                "model": "b",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby CPU benchmark"],
                "trust_score": 1.1,
            },
        ]

    def test_base_signals_skip(self, monkeypatch):
        """Baseline: base_skip_signals must actually produce skip_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        result = _gate.decide(self._base_skip_signals())
        assert result["decision"] == "skip_debate", (
            f"Baseline fixture must skip; got rationale: {result['rationale']}"
        )

    # (a) low trust -> run_debate
    def test_low_trust_forces_run_debate(self, monkeypatch):
        """High agreement + high conf but min_trust below floor -> run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = self._base_skip_signals()
        # Both solvers have trust_score=0.4, below default floor of 1.0
        for s in signals:
            s["trust_score"] = 0.4
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"
        assert "min_trust" in result["rationale"]

    # (b) minority can_exit -> run_debate
    def test_minority_can_exit_forces_run_debate(self, monkeypatch):
        """High agreement + high conf but can_exit only a minority -> run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 92,
                "can_exit": False,
                "semantic_focus": ["Python faster Ruby CPU tasks"],
                "trust_score": 1.2,
            },
            {
                "model": "b",
                "confidence": 90,
                "can_exit": False,
                "semantic_focus": ["Python faster Ruby CPU benchmark"],
                "trust_score": 1.1,
            },
            {
                "model": "c",
                "confidence": 91,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby CPU speed"],
                "trust_score": 1.0,
            },
        ]
        # frac_can_exit = 1/3 ≈ 0.33 < 0.5 default
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"
        assert "frac_can_exit" in result["rationale"]

    # (c) trivial single-token primary claims -> run_debate
    def test_trivial_primary_claims_forces_run_debate(self, monkeypatch):
        """Agreeing but trivial single-token primary claims -> run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 92,
                "can_exit": True,
                "semantic_focus": ["42"],  # single token after stopword strip
                "trust_score": 1.2,
            },
            {
                "model": "b",
                "confidence": 90,
                "can_exit": True,
                "semantic_focus": ["42"],
                "trust_score": 1.1,
            },
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"
        assert "primary_sufficient" in result["rationale"]

    # (d) vote_confidence below high_conf -> run_debate
    def test_low_vote_confidence_forces_run_debate(self, monkeypatch):
        """vote_confidence below high_conf forces run_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        # One solver has very low trust so the weighted vote falls below 85
        # trust: a=10 (conf=92), b=0.01 (conf=40) -> weighted ~= 92 still too high
        # Use a=0.01 (conf=40), b=0.01 (conf=40) -> vote_confidence=40 < 85
        signals = [
            {
                "model": "a",
                "confidence": 40,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby CPU tasks"],
                "trust_score": 0.01,
            },
            {
                "model": "b",
                "confidence": 40,
                "can_exit": True,
                "semantic_focus": ["Python faster Ruby CPU benchmark"],
                "trust_score": 0.01,
            },
        ]
        # Relax min_trust so only vote_confidence fires
        monkeypatch.setenv("SYNOD_GATE_MIN_TRUST", "0.0")
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"
        assert "vote_confidence" in result["rationale"]

    # (e) boundary: agreement exactly 0.80 with all else satisfied -> skip_debate
    def test_boundary_agreement_exactly_threshold_skips(self, monkeypatch):
        """Agreement score exactly at 0.80 threshold with all else passing -> skip_debate."""
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        # Lower the threshold to exactly match our fixture's score
        signals = self._base_skip_signals()
        result_check = _gate.decide(signals)
        actual_score = result_check["agreement_score"]
        # Set threshold to exactly the computed score
        monkeypatch.setenv("SYNOD_GATE_AGREE_THRESHOLD", str(actual_score))
        result = _gate.decide(signals)
        assert result["decision"] == "skip_debate", (
            f"Expected skip at boundary score={actual_score}, got: {result['rationale']}"
        )


# ---------------------------------------------------------------------------
# Negation regression — opposite primary claims must NOT skip the debate.
# Previously "not"/"no" were stopwords, so "X" and "not X" tokenized identically
# (agreement 1.0 -> skip_debate). Negation tokens are now preserved.
# ---------------------------------------------------------------------------


class TestNegationPreserved:
    def _sig(self, model, focus):
        return {
            "model": model,
            "confidence": 92,
            "can_exit": True,
            "semantic_focus": [focus],
            "trust_score": 1.3,
            "vote_weight": 1.0,
        }

    def test_claim_agreement_distinguishes_negation(self):
        opp = _gate.claim_agreement(
            [["Python is faster than Ruby"], ["Python is not faster than Ruby"]]
        )
        same = _gate.claim_agreement(
            [["Python is faster than Ruby"], ["Python is faster than Ruby"]]
        )
        assert opp < 1.0, f"opposite claims must not score 1.0 agreement, got {opp}"
        assert same == 1.0

    def test_opposite_claims_run_debate_even_when_gate_enabled(self, monkeypatch):
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            self._sig("gpt-4o", "Python is faster than Ruby"),
            self._sig("gemini-flash", "Python is not faster than Ruby"),
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate", result
        assert result["agreement_score"] < 1.0

    def test_contraction_negation_run_debate_when_gate_enabled(self, monkeypatch):
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            self._sig("gpt-4o", "Python is faster than Ruby"),
            self._sig("gemini-flash", "Python isn't faster than Ruby"),
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate", result
        assert result["signals"]["claim_agreement"] < 0.8

    def test_identical_claims_can_still_skip_when_gate_enabled(self, monkeypatch):
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            self._sig("gpt-4o", "Python is faster than Ruby for CPU-bound tasks"),
            self._sig("gemini-flash", "Python is faster than Ruby for CPU-bound tasks"),
            self._sig("claude-sonnet", "Python is faster than Ruby for CPU-bound tasks"),
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "skip_debate", result


class TestFailSafeBadNumbers:
    """Malformed *numeric* fields must fail-OPEN (run_debate), never traceback —
    matching the existing fail-safe for malformed shape."""

    def test_non_numeric_confidence_and_trust_no_traceback(self):
        signals = [
            {
                "model": "a",
                "confidence": "high",
                "can_exit": True,
                "semantic_focus": ["x y"],
                "trust_score": "n/a",
            },
            {
                "model": "b",
                "confidence": 95,
                "can_exit": True,
                "semantic_focus": ["x y"],
                "trust_score": 1.2,
            },
        ]
        result = _gate.decide(signals)  # must not raise
        assert result["decision"] == "run_debate"
        assert result["signals"]["min_confidence"] == 0.0

    def test_malformed_semantic_focus_item_no_traceback(self, monkeypatch):
        monkeypatch.setenv("SYNOD_DEBATE_GATE", "1")
        signals = [
            {
                "model": "a",
                "confidence": 95,
                "can_exit": True,
                "semantic_focus": [123],
                "trust_score": 1.2,
            },
            {
                "model": "b",
                "confidence": 95,
                "can_exit": True,
                "semantic_focus": ["x y"],
                "trust_score": 1.2,
            },
        ]
        result = _gate.decide(signals)
        assert result["decision"] == "run_debate"
        assert "fail-safe" in result["rationale"]

    def test_safe_float_helper(self):
        assert _gate._safe_float("12.5") == 12.5
        assert _gate._safe_float("abc") == 0.0
        assert _gate._safe_float(None, 1.0) == 1.0
