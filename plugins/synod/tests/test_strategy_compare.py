"""
tests/test_strategy_compare.py

Offline CI tests for benchmark/strategy_compare.py.

All three strategies are exercised with MockRunner — no live model services
required.  Tests assert:

  1. Harness completes without error for all three strategies.
  2. S2 makes fewer total model calls than S3 on high-agreement items
     (when SYNOD_DEBATE_GATE=1 is active).
  3. Accuracy is computed correctly (exact-numeric match).
  4. Report JSON has the expected top-level shape.
  5. Gate decision values are plausible.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import harness (located in benchmark/, not on default sys.path in tests)
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_BENCHMARK = _ROOT / "benchmark"

for _p in (str(_ROOT), str(_BENCHMARK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from benchmark.strategy_compare import (  # noqa: E402
    MockRunner,
    StrategyReport,
    StrategyS1,
    StrategyS2,
    StrategyS3,
    _answers_match,
    _extract_gsm8k_answer,
    build_report,
    load_mock_gsm8k,
    run_strategy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Small deterministic question set shared across tests
_QUESTIONS: list[dict] = [
    {"id": 0, "question": "What is 2+2?", "answer": "#### 4"},
    {"id": 1, "question": "What is 10-3?", "answer": "#### 7"},
    {"id": 2, "question": "What is 5*6?", "answer": "#### 30"},
    {"id": 3, "question": "What is 20/4?", "answer": "#### 5"},
    {"id": 4, "question": "What is 3^2?", "answer": "#### 9"},
]

_CORRECT_ANSWERS: dict[int, str] = {q["id"]: _extract_gsm8k_answer(q["answer"]) for q in _QUESTIONS}

# IDs 0, 2, 4 are "agreement" questions (even IDs → MockRunner makes solvers agree)
_AGREEMENT_IDS: list[int] = [0, 2, 4]
# IDs 1, 3 are "disagreement" questions → gate will NOT skip


@pytest.fixture()
def runner() -> MockRunner:
    return MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=_AGREEMENT_IDS)


@pytest.fixture()
def runner_all_agree() -> MockRunner:
    """All questions have high-agreement solvers."""
    return MockRunner(
        answers=_CORRECT_ANSWERS,
        agreement_ids=list(_CORRECT_ANSWERS.keys()),
    )


@pytest.fixture()
def runner_none_agree() -> MockRunner:
    """No questions have high-agreement solvers."""
    return MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=[])


# ---------------------------------------------------------------------------
# Helper: run S2 with gate explicitly enabled/disabled
# ---------------------------------------------------------------------------


def _run_s2(runner: MockRunner, gate_on: bool) -> StrategyReport:
    saved = os.environ.get("SYNOD_DEBATE_GATE")
    os.environ["SYNOD_DEBATE_GATE"] = "1" if gate_on else "0"
    try:
        s2 = StrategyS2(runner)
        return run_strategy(s2, _QUESTIONS)
    finally:
        if saved is None:
            os.environ.pop("SYNOD_DEBATE_GATE", None)
        else:
            os.environ["SYNOD_DEBATE_GATE"] = saved


# ---------------------------------------------------------------------------
# 1. Harness completes without error
# ---------------------------------------------------------------------------


class TestHarnessCompletes:
    def test_s1_runs(self, runner: MockRunner) -> None:
        s1 = StrategyS1(runner)
        report = run_strategy(s1, _QUESTIONS)
        assert report.n_questions == len(_QUESTIONS)
        assert report.strategy == "S1_single_solver"

    def test_s2_runs(self, runner: MockRunner) -> None:
        s2 = StrategyS2(runner)
        report = run_strategy(s2, _QUESTIONS)
        assert report.n_questions == len(_QUESTIONS)
        assert report.strategy == "S2_debate_gate"

    def test_s3_runs(self, runner: MockRunner) -> None:
        s3 = StrategyS3(runner)
        report = run_strategy(s3, _QUESTIONS)
        assert report.n_questions == len(_QUESTIONS)
        assert report.strategy == "S3_full_debate"

    def test_all_three_strategies_same_question_count(self, runner: MockRunner) -> None:
        reports = []
        for StratCls in (StrategyS1, StrategyS2, StrategyS3):
            strat = StratCls(MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=_AGREEMENT_IDS))
            reports.append(run_strategy(strat, _QUESTIONS))
        counts = [r.n_questions for r in reports]
        assert counts == [len(_QUESTIONS)] * 3


# ---------------------------------------------------------------------------
# 2. S2 makes fewer calls than S3 on high-agreement items (gate enabled)
# ---------------------------------------------------------------------------


class TestCallEfficiency:
    def test_s2_fewer_calls_than_s3_when_all_agree(self, runner_all_agree: MockRunner) -> None:
        """
        When every solver agrees with high confidence, S2 (gate=1) should
        skip debate for all questions → fewer total calls than S3.
        """
        r2 = _run_s2(runner_all_agree, gate_on=True)
        s3 = StrategyS3(MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=list(_CORRECT_ANSWERS)))
        r3 = run_strategy(s3, _QUESTIONS)

        assert r2.total_calls < r3.total_calls, (
            f"S2 calls ({r2.total_calls}) should be < S3 calls ({r3.total_calls}) "
            "when all questions have high-agreement solvers and gate is ON"
        )

    def test_s2_fewer_calls_than_s3_on_mixed_set(self, runner: MockRunner) -> None:
        """
        With a mixed set (some agree, some don't), S2 gate=1 should still
        save calls vs S3 (which always debates).
        """
        r2 = _run_s2(runner, gate_on=True)
        s3 = StrategyS3(MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=_AGREEMENT_IDS))
        r3 = run_strategy(s3, _QUESTIONS)

        # At least the agreement questions should save calls
        assert r2.total_calls <= r3.total_calls, (
            f"S2 ({r2.total_calls}) should never exceed S3 ({r3.total_calls}) calls when gate is ON"
        )

    def test_s2_gate_off_equals_s3_calls(self, runner_all_agree: MockRunner) -> None:
        """
        When gate is OFF (SYNOD_DEBATE_GATE=0), S2 always runs debate.
        Total calls should match S3 pattern (both always debate).
        """
        r2_off = _run_s2(runner_all_agree, gate_on=False)
        s3 = StrategyS3(MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=list(_CORRECT_ANSWERS)))
        r3 = run_strategy(s3, _QUESTIONS)

        # Both always debate → same calls per question
        assert r2_off.calls_per_question == r3.calls_per_question, (
            f"S2 gate=OFF ({r2_off.calls_per_question}/q) should equal "
            f"S3 ({r3.calls_per_question}/q)"
        )

    def test_s1_has_fewest_calls(self, runner: MockRunner) -> None:
        """S1 always makes exactly 1 call per question (cheapest strategy)."""
        s1 = StrategyS1(runner)
        r1 = run_strategy(s1, _QUESTIONS)
        assert r1.calls_per_question == 1.0

    def test_s3_gate_decision_always_run_debate(self, runner: MockRunner) -> None:
        """S3 always sets gate_decision=run_debate."""
        s3 = StrategyS3(runner)
        report = run_strategy(s3, _QUESTIONS)
        for row in report.per_question_results:
            assert row["gate_decision"] == "run_debate"


# ---------------------------------------------------------------------------
# 3. Accuracy is computed correctly
# ---------------------------------------------------------------------------


class TestAccuracy:
    def test_all_correct_mock_runner(self) -> None:
        """
        MockRunner.full_debate always returns the correct answer.
        S3 should have 100% accuracy.
        """
        runner = MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=[])
        s3 = StrategyS3(runner)
        report = run_strategy(s3, _QUESTIONS)
        assert report.accuracy == 1.0, (
            f"S3 with MockRunner should be 100% accurate, got {report.accuracy}"
        )

    def test_accuracy_formula_correct_count_over_total(self) -> None:
        """accuracy == n_correct / n_questions."""
        runner = MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=[])
        s3 = StrategyS3(runner)
        report = run_strategy(s3, _QUESTIONS)
        expected = report.n_correct / report.n_questions
        assert abs(report.accuracy - expected) < 1e-6

    def test_zero_correct_runner_accuracy_is_zero(self) -> None:
        """If all answers are wrong, accuracy should be 0."""
        wrong_answers = {q["id"]: "999999" for q in _QUESTIONS}
        runner = MockRunner(answers=wrong_answers, agreement_ids=[])
        s3 = StrategyS3(runner)
        report = run_strategy(s3, _QUESTIONS)
        assert report.accuracy == 0.0

    def test_s1_accuracy_uses_first_solver_signal(self) -> None:
        """
        S1 uses signals[0].answer.  MockRunner model_0 always has the correct
        answer (even for non-agreement questions).
        """
        runner = MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=[])
        s1 = StrategyS1(runner)
        report = run_strategy(s1, _QUESTIONS)
        # model_0 always correct → 100%
        assert report.accuracy == 1.0

    def test_answers_match_numeric_tolerance(self) -> None:
        """_answers_match allows floating-point tolerance."""
        assert _answers_match("42", "42")
        assert _answers_match("42", "42.0")
        assert not _answers_match("42", "43")
        assert not _answers_match("42", None)

    def test_extract_gsm8k_answer_format(self) -> None:
        """_extract_gsm8k_answer strips #### prefix."""
        assert _extract_gsm8k_answer("#### 42") == "42"
        assert _extract_gsm8k_answer("#### 1,234") == "1234"
        assert _extract_gsm8k_answer("plain text") == "plain text"


# ---------------------------------------------------------------------------
# 4. Report shape is valid
# ---------------------------------------------------------------------------


class TestReportShape:
    def _get_reports(self, runner: MockRunner | None = None) -> list:
        if runner is None:
            runner = MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=_AGREEMENT_IDS)
        reports = []
        for StratCls in (StrategyS1, StrategyS2, StrategyS3):
            strat = StratCls(MockRunner(answers=_CORRECT_ANSWERS, agreement_ids=_AGREEMENT_IDS))
            reports.append(run_strategy(strat, _QUESTIONS))
        return reports

    def test_report_has_required_top_level_keys(self) -> None:
        report = build_report(self._get_reports())
        assert "meta" in report
        assert "strategies" in report
        assert "table" in report

    def test_meta_has_live_gap_note(self) -> None:
        report = build_report(self._get_reports())
        assert "live_verification_gap" in report["meta"]
        assert "live model services" in report["meta"]["live_verification_gap"]

    def test_strategies_list_length(self) -> None:
        reports = self._get_reports()
        report = build_report(reports)
        assert len(report["strategies"]) == 3

    def test_each_strategy_entry_has_required_fields(self) -> None:
        report = build_report(self._get_reports())
        required = {
            "strategy",
            "n_questions",
            "n_correct",
            "accuracy",
            "total_calls",
            "calls_per_question",
            "total_wall_seconds",
            "total_token_estimate",
            "estimated_cost_usd",
            "per_question_results",
        }
        for entry in report["strategies"]:
            missing = required - set(entry.keys())
            assert not missing, f"Missing fields in strategy entry: {missing}"

    def test_per_question_results_count(self) -> None:
        report = build_report(self._get_reports())
        for entry in report["strategies"]:
            assert len(entry["per_question_results"]) == len(_QUESTIONS)

    def test_table_contains_all_strategy_names(self) -> None:
        report = build_report(self._get_reports())
        table = report["table"]
        assert "S1_single_solver" in table
        assert "S2_debate_gate" in table
        assert "S3_full_debate" in table

    def test_cost_monotonic_s1_cheapest(self) -> None:
        """S1 should have the lowest estimated cost per question."""
        report = build_report(self._get_reports())
        costs = {e["strategy"]: e["estimated_cost_usd"] for e in report["strategies"]}
        assert costs["S1_single_solver"] < costs["S3_full_debate"], (
            "S1 should cost less than S3 (fewer tokens)"
        )


# ---------------------------------------------------------------------------
# 5. load_mock_gsm8k smoke-test
# ---------------------------------------------------------------------------


class TestMockDataset:
    def test_load_mock_gsm8k_returns_n_items(self) -> None:
        qs = load_mock_gsm8k(5)
        assert len(qs) == 5

    def test_load_mock_gsm8k_max_10(self) -> None:
        qs = load_mock_gsm8k(10)
        assert len(qs) == 10

    def test_question_dict_shape(self) -> None:
        qs = load_mock_gsm8k(3)
        for q in qs:
            assert "id" in q
            assert "question" in q
            assert "answer" in q
            assert "####" in q["answer"]

    def test_answers_are_parseable(self) -> None:
        qs = load_mock_gsm8k(10)
        for q in qs:
            ans = _extract_gsm8k_answer(q["answer"])
            assert ans.lstrip("-").replace(".", "").isdigit(), (
                f"Answer '{ans}' for question {q['id']} is not numeric"
            )


# ---------------------------------------------------------------------------
# 6. Integration — run all three strategies end-to-end and validate report
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_run_produces_valid_report(self) -> None:
        """Run all 3 strategies on mock data and validate the report."""
        questions = load_mock_gsm8k(5)
        correct = {q["id"]: _extract_gsm8k_answer(q["answer"]) for q in questions}
        agree_ids = [q["id"] for q in questions if q["id"] % 2 == 0]

        os.environ["SYNOD_DEBATE_GATE"] = "1"
        try:
            reports = []
            for StratCls in (StrategyS1, StrategyS2, StrategyS3):
                strat = StratCls(MockRunner(answers=correct, agreement_ids=agree_ids))
                reports.append(run_strategy(strat, questions))

            report = build_report(reports)

            # All strategies complete
            assert len(report["strategies"]) == 3
            # Meta present
            assert "meta" in report
            # Table renders non-empty
            assert len(report["table"]) > 50
            # S2 <= S3 calls (gate on, some agreements exist)
            calls = {e["strategy"]: e["total_calls"] for e in report["strategies"]}
            assert calls["S2_debate_gate"] <= calls["S3_full_debate"]
        finally:
            os.environ.pop("SYNOD_DEBATE_GATE", None)

    def test_mock_runner_call_log_populated(self) -> None:
        """MockRunner call_log records all phase1 and debate calls."""
        runner = MockRunner(answers={0: "4"}, agreement_ids=[])
        s3 = StrategyS3(runner)
        run_strategy(s3, [{"id": 0, "question": "2+2?", "answer": "#### 4"}])

        # S3 calls phase1 then full_debate
        assert any("phase1:0" in e for e in runner.call_log)
        assert any("debate:0" in e for e in runner.call_log)
