#!/usr/bin/env python3
"""Evaluation utilities for Synod benchmark"""

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from scipy import stats


@dataclass
class EvaluationMetrics:
    accuracy: float
    ci_lower: float
    ci_upper: float
    correct_count: int
    total_count: int
    error_count: int


class GSM8KEvaluator:
    """Evaluator for GSM8K math benchmark"""

    @staticmethod
    def extract_expected_answer(answer_text: str) -> str:
        """Extract numeric answer after #### from GSM8K format"""
        match = re.search(r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)", answer_text)
        if match:
            return match.group(1).replace(",", "")
        return ""

    @staticmethod
    def extract_model_answer(response: str) -> Optional[str]:
        """Extract numeric answer from model response"""
        patterns = [
            r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)",
            r"(?:answer|답|정답|Answer)[:\s]*(-?\d+(?:,\d+)*(?:\.\d+)?)",
            r"(?:therefore|thus|so|따라서|그러므로|Hence)[,\s]*.*?(\d+(?:,\d+)*(?:\.\d+)?)",
            r"\*\*(-?\d+(?:,\d+)*(?:\.\d+)?)\*\*",
            r"(?:=|equals?)[:\s]*(-?\d+(?:,\d+)*(?:\.\d+)?)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                return matches[-1].replace(",", "")

        # Fallback: last number in response
        numbers = re.findall(r"(?<!\d)(-?\d+(?:\.\d+)?)(?!\d)", response)
        return numbers[-1] if numbers else None

    @staticmethod
    def is_correct(expected: str, predicted: Optional[str]) -> bool:
        """Check if predicted answer matches expected"""
        if predicted is None:
            return False
        try:
            exp_num = float(expected)
            pred_num = float(predicted)
            # Allow small floating point tolerance
            return abs(exp_num - pred_num) < 0.001
        except ValueError:
            return expected.strip() == predicted.strip()


class TruthfulQAEvaluator:
    """Evaluator for TruthfulQA benchmark"""

    @staticmethod
    def evaluate_mc1(response: str, correct_idx: int, options: list[str]) -> bool:
        """Evaluate MC1 (single correct answer) format"""
        # Extract letter choice (A, B, C, D)
        match = re.search(r"\b([A-D])\b", response.upper())
        if match:
            predicted_idx = ord(match.group(1)) - ord("A")
            return predicted_idx == correct_idx

        # Fallback: check if correct option text is in response
        return options[correct_idx].lower() in response.lower()

    @staticmethod
    def evaluate_mc2(response: str, correct_indices: list[int], options: list[str]) -> float:
        """Evaluate MC2 (multiple correct answers) format"""
        # Extract all letter choices
        matches = re.findall(r"\b([A-D])\b", response.upper())
        predicted_indices = [ord(m) - ord("A") for m in matches]

        if not predicted_indices:
            return 0.0

        # Calculate precision/recall style score
        correct_set = set(correct_indices)
        predicted_set = set(predicted_indices)

        if not predicted_set:
            return 0.0

        intersection = correct_set & predicted_set
        precision = len(intersection) / len(predicted_set)
        recall = len(intersection) / len(correct_set)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)  # F1


class StatisticalAnalyzer:
    """Statistical analysis for benchmark results"""

    @staticmethod
    def calculate_accuracy_with_ci(
        results: list[bool], confidence: float = 0.95
    ) -> EvaluationMetrics:
        """Calculate accuracy with confidence interval"""
        n = len(results)
        if n == 0:
            return EvaluationMetrics(0, 0, 0, 0, 0, 0)

        correct = sum(results)
        accuracy = correct / n

        # Wilson score interval (better for small samples)
        z = stats.norm.ppf((1 + confidence) / 2)
        denominator = 1 + z**2 / n
        center = (accuracy + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt((accuracy * (1 - accuracy) + z**2 / (4 * n)) / n) / denominator

        return EvaluationMetrics(
            accuracy=accuracy,
            ci_lower=max(0, center - margin),
            ci_upper=min(1, center + margin),
            correct_count=correct,
            total_count=n,
            error_count=n - correct,
        )

    @staticmethod
    def mcnemar_test(results_a: list[bool], results_b: list[bool]) -> tuple[float, float]:
        """
        McNemar's test for paired nominal data.
        Returns (chi2 statistic, p-value)
        """
        assert len(results_a) == len(results_b)

        # Build contingency table
        # b = A wrong, B right
        # c = A right, B wrong
        b = sum(1 for a, b in zip(results_a, results_b) if not a and b)
        c = sum(1 for a, b in zip(results_a, results_b) if a and not b)

        if b + c == 0:
            return 0.0, 1.0  # No difference

        # McNemar's test with continuity correction
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
        p_value = 1 - stats.chi2.cdf(chi2, df=1)

        return chi2, p_value

    @staticmethod
    def bootstrap_ci(
        results: list[bool], n_bootstrap: int = 10000, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Bootstrap confidence interval for accuracy"""
        results = np.array(results)
        n = len(results)

        # Bootstrap resampling
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(results, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = (1 - confidence) / 2
        ci_lower = np.percentile(bootstrap_means, alpha * 100)
        ci_upper = np.percentile(bootstrap_means, (1 - alpha) * 100)

        return ci_lower, ci_upper


class CostAnalyzer:
    """Analyze costs for benchmark runs"""

    # Pricing per 1M tokens (input/output)
    PRICING = {
        "claude-sonnet-4": (3.0, 15.0),
        "gpt-4o": (2.5, 10.0),
        "o3": (10.0, 40.0),
        "gemini-flash": (0.075, 0.30),
        "gemini-pro": (1.25, 5.0),
    }

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        if model not in CostAnalyzer.PRICING:
            return 0.0

        input_price, output_price = CostAnalyzer.PRICING[model]
        return (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    @staticmethod
    def summarize_costs(results: list[dict[str, Any]]) -> dict[str, float]:
        """Summarize costs from benchmark results"""
        total_cost = sum(r.get("cost_usd", 0) for r in results)
        total_questions = len(results)

        return {
            "total_cost_usd": total_cost,
            "avg_cost_per_question": total_cost / total_questions if total_questions > 0 else 0,
            "estimated_phase1_cost": total_cost / total_questions * 300
            if total_questions > 0
            else 0,
            "estimated_phase2_cost": total_cost / total_questions * 800
            if total_questions > 0
            else 0,
        }


def evaluate_benchmark_results(results_path: str) -> dict[str, Any]:
    """Evaluate benchmark results from JSON file"""
    with open(results_path) as f:
        data = json.load(f)

    results = data["results"]

    # Extract correctness
    is_correct_list = [r["is_correct"] for r in results]

    # Calculate metrics
    analyzer = StatisticalAnalyzer()
    metrics = analyzer.calculate_accuracy_with_ci(is_correct_list)

    # Cost analysis
    cost_summary = CostAnalyzer.summarize_costs(results)

    return {
        "accuracy": metrics.accuracy,
        "accuracy_ci": (metrics.ci_lower, metrics.ci_upper),
        "correct": metrics.correct_count,
        "total": metrics.total_count,
        "errors": metrics.error_count,
        "costs": cost_summary,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("results_file", help="Path to results JSON")
    args = parser.parse_args()

    evaluation = evaluate_benchmark_results(args.results_file)
    print(json.dumps(evaluation, indent=2))
