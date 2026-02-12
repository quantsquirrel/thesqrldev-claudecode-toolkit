#!/usr/bin/env python3
"""
Classification Accuracy Benchmark for synod-classifier.py

Tests the classifier against 50 predefined test cases across 5 modes.
Target accuracy: >90%
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Test cases: 50 total across 5 modes
TEST_CASES = [
    # Review (12)
    {"prompt": "이 코드 리뷰해줘", "expected": "review"},
    {"prompt": "PR 리뷰 부탁해", "expected": "review"},
    {"prompt": "코드 검토해줘", "expected": "review"},
    {"prompt": "버그 찾아줘", "expected": "review"},
    {"prompt": "개선점 알려줘", "expected": "review"},
    {"prompt": "피드백 좀 줘", "expected": "review"},
    {"prompt": "Review this code please", "expected": "review"},
    {"prompt": "문제점 찾아줘", "expected": "review"},
    {"prompt": "코드 확인해줘", "expected": "review"},
    {"prompt": "이 함수 리뷰해줘", "expected": "review"},
    {"prompt": "코드 품질 검토", "expected": "review"},
    {"prompt": "리팩토링 포인트 찾아줘", "expected": "review"},

    # Design (12)
    {"prompt": "API 설계해줘", "expected": "design"},
    {"prompt": "시스템 아키텍처 만들어줘", "expected": "design"},
    {"prompt": "DB 스키마 설계", "expected": "design"},
    {"prompt": "Design the architecture", "expected": "design"},
    {"prompt": "구조 설계해줘", "expected": "design"},
    {"prompt": "마이크로서비스 아키텍처", "expected": "design"},
    {"prompt": "ERD 설계 부탁", "expected": "design"},
    {"prompt": "클래스 구조 설계", "expected": "design"},
    {"prompt": "API 구조 잡아줘", "expected": "design"},
    {"prompt": "시스템 설계 도와줘", "expected": "design"},
    {"prompt": "인터페이스 설계", "expected": "design"},
    {"prompt": "모듈 구조 설계", "expected": "design"},

    # Debug (12)
    {"prompt": "에러 수정해줘", "expected": "debug"},
    {"prompt": "버그 고쳐줘", "expected": "debug"},
    {"prompt": "왜 안되는지 모르겠어", "expected": "debug"},
    {"prompt": "작동이 안됨", "expected": "debug"},
    {"prompt": "Debug this error", "expected": "debug"},
    {"prompt": "Exception 발생", "expected": "debug"},
    {"prompt": "실패하는 이유가 뭐야", "expected": "debug"},
    {"prompt": "오류 해결해줘", "expected": "debug"},
    {"prompt": "이거 왜 fail이야", "expected": "debug"},
    {"prompt": "에러 메시지 분석", "expected": "debug"},
    {"prompt": "디버그 도와줘", "expected": "debug"},
    {"prompt": "버그 원인 분석", "expected": "debug"},

    # Idea (10)
    {"prompt": "아이디어 좀 줘", "expected": "idea"},
    {"prompt": "브레인스토밍 하자", "expected": "idea"},
    {"prompt": "어떻게 하면 좋을까", "expected": "idea"},
    {"prompt": "대안 제시해줘", "expected": "idea"},
    {"prompt": "Suggest some ideas", "expected": "idea"},
    {"prompt": "방법 좀 알려줘", "expected": "idea"},
    {"prompt": "제안해줘", "expected": "idea"},
    {"prompt": "아이디어 있어?", "expected": "idea"},
    {"prompt": "창의적인 방법 뭐 있을까", "expected": "idea"},
    {"prompt": "다른 접근법 제안", "expected": "idea"},

    # General (4)
    {"prompt": "안녕", "expected": "general"},
    {"prompt": "Hello", "expected": "general"},
    {"prompt": "뭐해?", "expected": "general"},
    {"prompt": "오늘 날씨 어때", "expected": "general"},
]


def run_classifier(classifier_path: Path, prompt: str) -> str:
    """Run the classifier and return the predicted mode."""
    try:
        result = subprocess.run(
            ["python3", str(classifier_path), prompt],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            print(f"Error running classifier: {result.stderr}")
            return "error"

        # The classifier outputs JSON with mode, confidence, etc.
        # Parse JSON and extract the "mode" field
        output = result.stdout.strip()
        try:
            data = json.loads(output)
            return data.get("mode", "error")
        except json.JSONDecodeError:
            # If not valid JSON, return the raw output for debugging
            return output

    except subprocess.TimeoutExpired:
        print(f"Classifier timed out for prompt: {prompt}")
        return "timeout"
    except Exception as e:
        print(f"Exception running classifier: {e}")
        return "error"


def run_benchmark(classifier_path: Path) -> Tuple[int, int, List[Dict]]:
    """
    Run all test cases and return (correct_count, total_count, failures).
    """
    correct = 0
    total = len(TEST_CASES)
    failures = []

    print(f"\nRunning {total} test cases...\n")

    for i, case in enumerate(TEST_CASES, 1):
        prompt = case["prompt"]
        expected = case["expected"]

        actual = run_classifier(classifier_path, prompt)

        if actual == expected:
            correct += 1
            status = "✓"
        else:
            status = "✗"
            failures.append({
                "prompt": prompt,
                "expected": expected,
                "actual": actual
            })

        print(f"[{i:2d}/{total}] {status} {prompt[:40]:40s} | Expected: {expected:8s} | Got: {actual:8s}")

    return correct, total, failures


def print_results(correct: int, total: int, failures: List[Dict]) -> None:
    """Print benchmark results."""
    accuracy = (correct / total) * 100

    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Total test cases: {total}")
    print(f"Correct: {correct}")
    print(f"Failed: {len(failures)}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Target: 90.00%")

    if accuracy >= 90:
        print("\n✓ PASS: Accuracy meets or exceeds target (≥90%)")
    else:
        print("\n✗ FAIL: Accuracy below target (<90%)")

    if failures:
        print("\n" + "-" * 80)
        print("FAILURES:")
        print("-" * 80)
        for i, failure in enumerate(failures, 1):
            print(f"\n{i}. Prompt: {failure['prompt']}")
            print(f"   Expected: {failure['expected']}")
            print(f"   Got:      {failure['actual']}")

    print("\n" + "=" * 80)


def main() -> int:
    """Main entry point."""
    # Locate the classifier
    classifier_path = Path("/Users/ahnjundaram_g/dev/tools/claude-synod-debate/tools/synod-classifier.py")

    if not classifier_path.exists():
        print(f"Error: Classifier not found at {classifier_path}")
        return 1

    print(f"Using classifier: {classifier_path}")

    # Run benchmark
    correct, total, failures = run_benchmark(classifier_path)

    # Print results
    print_results(correct, total, failures)

    # Return exit code based on accuracy
    accuracy = (correct / total) * 100
    return 0 if accuracy >= 90 else 1


if __name__ == "__main__":
    sys.exit(main())
