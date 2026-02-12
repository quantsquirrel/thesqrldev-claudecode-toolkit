#!/usr/bin/env python3
"""Analysis and reporting for Synod benchmark results"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from evaluator import StatisticalAnalyzer
from rich.console import Console
from rich.table import Table


@dataclass
class ComparisonResult:
    method_a: str
    method_b: str
    accuracy_a: float
    accuracy_b: float
    difference: float
    chi2: float
    p_value: float
    significant: bool


class BenchmarkAnalyzer:
    """Analyze and compare benchmark results"""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.console = Console()
        self.analyzer = StatisticalAnalyzer()

    def load_results(self, filename: str) -> dict[str, Any]:
        """Load results from JSON file"""
        path = self.results_dir / filename
        with open(path) as f:
            return json.load(f)

    def compare_methods(
        self, results_a: list[bool], results_b: list[bool], name_a: str, name_b: str
    ) -> ComparisonResult:
        """Compare two methods statistically"""
        acc_a = sum(results_a) / len(results_a)
        acc_b = sum(results_b) / len(results_b)

        chi2, p_value = self.analyzer.mcnemar_test(results_a, results_b)

        return ComparisonResult(
            method_a=name_a,
            method_b=name_b,
            accuracy_a=acc_a,
            accuracy_b=acc_b,
            difference=acc_b - acc_a,
            chi2=chi2,
            p_value=p_value,
            significant=p_value < 0.05,
        )

    def generate_summary_table(self, all_results: dict[str, list[dict]]) -> Table:
        """Generate rich table comparing all methods"""
        table = Table(title="Benchmark Results Summary")

        table.add_column("Method", style="cyan")
        table.add_column("Accuracy", justify="right")
        table.add_column("95% CI", justify="right")
        table.add_column("Correct/Total", justify="right")
        table.add_column("Avg Cost", justify="right")
        table.add_column("Avg Time", justify="right")

        for method, results in all_results.items():
            is_correct = [r["is_correct"] for r in results]
            metrics = self.analyzer.calculate_accuracy_with_ci(is_correct)

            avg_cost = np.mean([r.get("cost_usd", 0) for r in results])
            avg_time = np.mean([r.get("elapsed_seconds", 0) for r in results])

            table.add_row(
                method,
                f"{metrics.accuracy * 100:.1f}%",
                f"[{metrics.ci_lower * 100:.1f}%, {metrics.ci_upper * 100:.1f}%]",
                f"{metrics.correct_count}/{metrics.total_count}",
                f"${avg_cost:.4f}",
                f"{avg_time:.1f}s",
            )

        return table

    def generate_markdown_report(
        self, all_results: dict[str, list[dict]], benchmark_name: str = "GSM8K"
    ) -> str:
        """Generate markdown report"""

        lines = [
            "# Synod v3.0 Benchmark Report",
            "",
            f"**Benchmark**: {benchmark_name}",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            "| Method | Accuracy | 95% CI | Cost/Question |",
            "|--------|----------|--------|---------------|",
        ]

        method_metrics = {}
        for method, results in all_results.items():
            is_correct = [r["is_correct"] for r in results]
            metrics = self.analyzer.calculate_accuracy_with_ci(is_correct)
            avg_cost = np.mean([r.get("cost_usd", 0) for r in results])

            method_metrics[method] = (metrics, is_correct)

            lines.append(
                f"| {method} | {metrics.accuracy * 100:.1f}% | "
                f"[{metrics.ci_lower * 100:.1f}%, {metrics.ci_upper * 100:.1f}%] | "
                f"${avg_cost:.4f} |"
            )

        # Statistical comparisons
        lines.extend(
            [
                "",
                "## Statistical Comparisons (McNemar Test)",
                "",
                "| Comparison | Δ Accuracy | χ² | p-value | Significant? |",
                "|------------|------------|-----|---------|--------------|",
            ]
        )

        methods = list(all_results.keys())
        if "synod" in [m.lower() for m in methods]:
            synod_key = [m for m in methods if "synod" in m.lower()][0]
            synod_correct = method_metrics[synod_key][1]

            for method in methods:
                if method != synod_key:
                    comparison = self.compare_methods(
                        method_metrics[method][1], synod_correct, method, synod_key
                    )
                    sig_marker = "✓" if comparison.significant else "✗"
                    lines.append(
                        f"| {method} vs {synod_key} | "
                        f"{comparison.difference * 100:+.1f}% | "
                        f"{comparison.chi2:.2f} | "
                        f"{comparison.p_value:.4f} | "
                        f"{sig_marker} |"
                    )

        # Cost analysis
        total_questions = len(list(all_results.values())[0])
        synod_cost = np.mean([r.get("cost_usd", 0) for r in all_results.get("synod", [])])

        lines.extend(
            [
                "",
                "## Cost Analysis",
                "",
                f"- **Questions evaluated**: {total_questions}",
                f"- **Synod cost/question**: ${synod_cost:.4f}",
                f"- **Projected Phase 1 cost** (300 questions): ${synod_cost * 300:.2f}",
                f"- **Projected Phase 2 cost** (800 questions): ${synod_cost * 800:.2f}",
                "",
                "## Conclusion",
                "",
            ]
        )

        # Auto-generate conclusion
        if "synod" in [m.lower() for m in methods]:
            synod_acc = method_metrics[synod_key][0].accuracy
            best_baseline = max(
                [(m, method_metrics[m][0].accuracy) for m in methods if m != synod_key],
                key=lambda x: x[1],
            )
            diff = (synod_acc - best_baseline[1]) * 100

            if diff > 2:
                lines.append(
                    f"Synod outperforms the best baseline ({best_baseline[0]}) by **{diff:.1f}%**."
                )
            elif diff > 0:
                lines.append(
                    f"Synod shows marginal improvement over {best_baseline[0]} (+{diff:.1f}%)."
                )
            else:
                lines.append(f"Synod does not outperform {best_baseline[0]} ({diff:.1f}%).")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("results_dir", help="Directory containing results JSON files")
    parser.add_argument("--output", "-o", help="Output markdown file")
    parser.add_argument("--benchmark", default="GSM8K", help="Benchmark name")
    args = parser.parse_args()

    analyzer = BenchmarkAnalyzer(args.results_dir)

    # Load all result files
    results_dir = Path(args.results_dir)
    all_results = {}

    for json_file in results_dir.glob("*.json"):
        data = json.loads(json_file.read_text())
        method_name = json_file.stem.replace("_results", "")
        all_results[method_name] = data.get("results", [])

    if not all_results:
        print("No results found!")
        return

    # Display table
    table = analyzer.generate_summary_table(all_results)
    analyzer.console.print(table)

    # Generate report
    report = analyzer.generate_markdown_report(all_results, args.benchmark)

    if args.output:
        Path(args.output).write_text(report)
        print(f"\nReport saved to {args.output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
