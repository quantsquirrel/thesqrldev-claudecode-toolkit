#!/usr/bin/env python3
"""GSM8K Benchmark Runner for Synod v3.0

Evaluates Synod's math reasoning capabilities on the GSM8K dataset.
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
    from datasets import load_dataset
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install with: pip install -r requirements.txt")
    exit(1)


@dataclass
class BenchmarkResult:
    """Result for a single GSM8K question"""

    question_id: int
    question: str
    expected_answer: str
    synod_response: str
    extracted_answer: Optional[str]
    is_correct: bool
    elapsed_seconds: float
    gemini_confidence: Optional[int] = None
    openai_confidence: Optional[int] = None
    trust_scores: Optional[dict[str, float]] = None
    error: Optional[str] = None
    retry_count: int = 0


def load_gsm8k_sample(n: int, seed: int) -> list[dict]:
    """Load N samples from GSM8K test set with fixed seed for reproducibility"""
    print(f"Loading GSM8K dataset (sample_size={n}, seed={seed})...")
    dataset = load_dataset("gsm8k", "main", split="test")
    # Shuffle with seed and take n samples
    dataset = dataset.shuffle(seed=seed).select(range(min(n, len(dataset))))
    return list(dataset)


def extract_answer_from_gsm8k(text: str) -> str:
    """Extract numeric answer after #### from GSM8K format"""
    match = re.search(r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)", text)
    if match:
        return match.group(1).replace(",", "")
    return ""


def extract_answer_from_response(response: str) -> Optional[str]:
    """Extract numeric answer from Synod response

    Tries multiple patterns to find the final answer:
    1. GSM8K format (####)
    2. Explicit answer markers
    3. Conclusion keywords
    4. Bold numbers (markdown)
    5. Standalone numbers at the end
    """
    patterns = [
        r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)",  # GSM8K format
        r"(?:answer|답|정답|final answer)[:\s]*(-?\d+(?:,\d+)*(?:\.\d+)?)",  # Explicit
        r"(?:therefore|thus|so|따라서|그러므로)[,\s]*.*?(-?\d+(?:,\d+)*(?:\.\d+)?)",  # Conclusion
        r"\*\*(-?\d+(?:,\d+)*(?:\.\d+)?)\*\*",  # Bold number
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            # Return last match (likely the final answer)
            return matches[-1].replace(",", "")

    # Fallback: find any standalone number at end (last 200 chars)
    tail = response[-200:] if len(response) > 200 else response
    numbers = re.findall(r"(?<!\d)(-?\d+(?:\.\d+)?)(?!\d)", tail)
    if numbers:
        return numbers[-1]

    return None


def parse_confidence_score(response: str, agent: str) -> Optional[int]:
    """Extract confidence score from agent response"""
    pattern = r'<confidence\s+score="(\d+)"'
    match = re.search(pattern, response)
    if match:
        return int(match.group(1))
    return None


def call_synod_solver(
    question: str, config: dict, retry_attempt: int = 0
) -> tuple[str, float, dict[str, Any]]:
    """Call Synod solver round (simplified version for benchmarking)

    This implements a lightweight solver round with Claude + Gemini + OpenAI,
    similar to Synod's Phase 1, but without the full debate rounds to save time/cost.

    Returns: (response_text, elapsed_time, metadata)
    """
    start = time.time()

    # Get model configurations from config
    gemini_model = config["models"]["gemini"]  # e.g., "gemini-2.0-flash"
    openai_model = config["models"]["openai"]["primary"]  # e.g., "gpt-4o"

    # Map to CLI model names
    gemini_cli_model = "flash" if "flash" in gemini_model else "pro"
    openai_cli_model = "gpt4o" if "gpt4o" in openai_model else "o3"

    # Create temp directory for this question
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Prepare prompts
        base_prompt = f"""Solve this math problem step-by-step.
Show your work clearly and provide the final answer.

Problem:
{question}

REQUIRED: End your response with the final answer in this format:
#### <number>

Example:
#### 42
"""

        gemini_prompt_file = temp_path / "gemini-prompt.txt"
        openai_prompt_file = temp_path / "openai-prompt.txt"

        gemini_prompt_file.write_text(base_prompt)
        openai_prompt_file.write_text(base_prompt)

        # Execute Gemini and OpenAI in parallel
        gemini_output = temp_path / "gemini-response.txt"
        openai_output = temp_path / "openai-response.txt"
        gemini_exit = temp_path / "gemini-exit-code"
        openai_exit = temp_path / "openai-exit-code"

        # Determine thinking/reasoning level based on retry
        thinking_level = "medium" if retry_attempt == 0 else "low"

        # Get tool paths
        tools_dir = Path(__file__).parent.parent / "tools"
        gemini_tool = tools_dir / "gemini-3.py"
        openai_tool = tools_dir / "openai-cli.py"

        # Check if tools exist
        if not gemini_tool.exists():
            raise FileNotFoundError(f"Gemini tool not found at {gemini_tool}")
        if not openai_tool.exists():
            raise FileNotFoundError(f"OpenAI tool not found at {openai_tool}")

        # Launch parallel processes
        gemini_cmd = [
            str(gemini_tool),
            "--model",
            gemini_cli_model,
            "--thinking",
            thinking_level,
            "--temperature",
            "0.7",
        ]

        openai_cmd = [str(openai_tool), "--model", openai_cli_model]

        try:
            # Run Gemini
            with open(gemini_prompt_file) as stdin_f, open(gemini_output, "w") as stdout_f:
                gemini_proc = subprocess.Popen(
                    gemini_cmd, stdin=stdin_f, stdout=stdout_f, stderr=subprocess.PIPE, text=True
                )

            # Run OpenAI
            with open(openai_prompt_file) as stdin_f, open(openai_output, "w") as stdout_f:
                openai_proc = subprocess.Popen(
                    openai_cmd, stdin=stdin_f, stdout=stdout_f, stderr=subprocess.PIPE, text=True
                )

            # Wait for both with timeout
            timeout_seconds = config["execution"]["timeout_seconds"]
            try:
                gemini_returncode = gemini_proc.wait(timeout=timeout_seconds)
                gemini_exit.write_text(str(gemini_returncode))
            except subprocess.TimeoutExpired:
                gemini_proc.kill()
                gemini_exit.write_text("timeout")

            try:
                openai_returncode = openai_proc.wait(timeout=timeout_seconds)
                openai_exit.write_text(str(openai_returncode))
            except subprocess.TimeoutExpired:
                openai_proc.kill()
                openai_exit.write_text("timeout")

            # Read responses
            gemini_response = gemini_output.read_text() if gemini_output.exists() else ""
            openai_response = openai_output.read_text() if openai_output.exists() else ""

            # Parse answers
            gemini_answer = extract_answer_from_response(gemini_response)
            openai_answer = extract_answer_from_response(openai_response)

            # Parse confidence scores if available
            gemini_conf = parse_confidence_score(gemini_response, "gemini")
            openai_conf = parse_confidence_score(openai_response, "openai")

            # Synthesize final response (prefer answer that appears in both, or use first available)
            if gemini_answer and openai_answer:
                if gemini_answer == openai_answer:
                    final_answer = gemini_answer
                    synthesis = f"CONSENSUS: Both models agree on {final_answer}"
                else:
                    # Disagreement - use Gemini as tiebreaker for math
                    final_answer = gemini_answer
                    synthesis = f"DISAGREEMENT: Gemini says {gemini_answer}, OpenAI says {openai_answer}. Using Gemini."
            elif gemini_answer:
                final_answer = gemini_answer
                synthesis = f"Gemini only: {final_answer}"
            elif openai_answer:
                final_answer = openai_answer
                synthesis = f"OpenAI only: {final_answer}"
            else:
                final_answer = None
                synthesis = "No answer extracted from either model"

            # Construct combined response
            combined_response = f"""## Synod Solver Round

### Gemini Response:
{gemini_response[:500]}...

### OpenAI Response:
{openai_response[:500]}...

### Synthesis:
{synthesis}

#### {final_answer if final_answer else "UNKNOWN"}
"""

            metadata = {
                "gemini_confidence": gemini_conf,
                "openai_confidence": openai_conf,
                "gemini_answer": gemini_answer,
                "openai_answer": openai_answer,
                "agreement": gemini_answer == openai_answer
                if (gemini_answer and openai_answer)
                else None,
            }

            elapsed = time.time() - start
            return combined_response, elapsed, metadata

        except Exception as e:
            elapsed = time.time() - start
            raise Exception(f"Synod solver failed: {e}") from e


def run_single_question(
    question_data: dict, question_id: int, config: dict, max_retries: int = 3
) -> BenchmarkResult:
    """Run Synod on a single GSM8K question with retry logic"""

    question = question_data["question"]
    expected = extract_answer_from_gsm8k(question_data["answer"])

    retry_count = 0
    last_error = None

    for attempt in range(max_retries):
        try:
            response, elapsed, metadata = call_synod_solver(question, config, retry_attempt=attempt)
            extracted = extract_answer_from_response(response)

            # Normalize answers for comparison (remove decimal points if .0)
            expected_norm = expected.rstrip("0").rstrip(".") if "." in expected else expected
            extracted_norm = (
                extracted.rstrip("0").rstrip(".") if (extracted and "." in extracted) else extracted
            )

            is_correct = extracted_norm == expected_norm

            return BenchmarkResult(
                question_id=question_id,
                question=question,
                expected_answer=expected,
                synod_response=response,
                extracted_answer=extracted,
                is_correct=is_correct,
                elapsed_seconds=elapsed,
                gemini_confidence=metadata.get("gemini_confidence"),
                openai_confidence=metadata.get("openai_confidence"),
                trust_scores=metadata,
                retry_count=attempt,
            )

        except Exception as e:
            last_error = str(e)
            retry_count = attempt + 1

            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Max retries exceeded
                return BenchmarkResult(
                    question_id=question_id,
                    question=question,
                    expected_answer=expected,
                    synod_response="",
                    extracted_answer=None,
                    is_correct=False,
                    elapsed_seconds=0,
                    error=last_error,
                    retry_count=retry_count,
                )

    # Should never reach here
    return BenchmarkResult(
        question_id=question_id,
        question=question,
        expected_answer=expected,
        synod_response="",
        extracted_answer=None,
        is_correct=False,
        elapsed_seconds=0,
        error="Unknown error",
        retry_count=retry_count,
    )


def run_benchmark(config_path: str, output_dir: str, resume_from: int = 0):
    """Run the GSM8K benchmark

    Args:
        config_path: Path to config.yaml
        output_dir: Output directory for results
        resume_from: Question ID to resume from (0 = start from beginning)
    """

    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Check if GSM8K is enabled
    if not config["benchmarks"]["gsm8k"]["enabled"]:
        print("GSM8K benchmark is disabled in config. Set 'enabled: true' to run.")
        return

    # Verify API keys
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Baselines using Claude will fail.")

    # Load samples
    samples = load_gsm8k_sample(
        config["benchmarks"]["gsm8k"]["sample_size"], config["benchmarks"]["gsm8k"]["seed"]
    )

    # Prepare output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results_file = output_path / "results.json"

    # Load existing results if resuming
    results = []
    if resume_from > 0 and results_file.exists():
        with open(results_file) as f:
            existing_data = json.load(f)
            results = existing_data.get("results", [])
        print(f"Resuming from question {resume_from} ({len(results)} completed)")

    correct = sum(1 for r in results if r.get("is_correct", False))
    total_time = sum(r.get("elapsed_seconds", 0) for r in results)

    # Progress bar starting from resume point
    samples_to_process = samples[resume_from:]
    pbar = tqdm(
        enumerate(samples_to_process, start=resume_from),
        desc="Running GSM8K",
        total=len(samples),
        initial=resume_from,
    )

    try:
        for i, sample in pbar:
            # Run question
            result = run_single_question(
                sample, i, config, max_retries=config["execution"]["retry_attempts"]
            )

            if result.is_correct:
                correct += 1

            total_time += result.elapsed_seconds

            results.append(asdict(result))

            # Update progress bar
            accuracy = correct / (i + 1) * 100
            avg_time = total_time / (i + 1)
            pbar.set_postfix({"acc": f"{accuracy:.1f}%", "avg_time": f"{avg_time:.1f}s"})

            # Save incrementally
            output_data = {
                "config": config,
                "results": results,
                "summary": {
                    "total": i + 1,
                    "correct": correct,
                    "accuracy": accuracy,
                    "avg_time_per_question": avg_time,
                    "total_time": total_time,
                },
                "timestamp": datetime.now().isoformat(),
            }

            with open(results_file, "w") as f:
                json.dump(output_data, f, indent=2)

            # Rate limiting delay
            delay = config["execution"]["delay_between_requests"]
            if delay > 0 and i < len(samples) - 1:
                time.sleep(delay)

    except KeyboardInterrupt:
        print(f"\n\nBenchmark interrupted. Results saved to {results_file}")
        print(f"Resume with: python run_gsm8k.py --resume {len(results)}")
        return

    # Final summary
    print(f"\n{'=' * 60}")
    print("GSM8K Benchmark Complete")
    print(f"{'=' * 60}")
    print(f"Total Questions: {len(samples)}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {correct / len(samples) * 100:.2f}%")
    print(f"Average Time: {total_time / len(samples):.2f}s per question")
    print(f"Total Time: {total_time / 60:.1f} minutes")
    print(f"\nResults saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Run GSM8K benchmark for Synod v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark
  python run_gsm8k.py

  # Use custom config
  python run_gsm8k.py --config custom-config.yaml

  # Resume from question 50
  python run_gsm8k.py --resume 50

  # Custom output directory
  python run_gsm8k.py --output results/experiment-1
""",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Config file path (default: config.yaml)"
    )
    parser.add_argument(
        "--output", default="results/gsm8k", help="Output directory (default: results/gsm8k)"
    )
    parser.add_argument(
        "--resume",
        type=int,
        default=0,
        help="Resume from question ID (default: 0 = start from beginning)",
    )

    args = parser.parse_args()

    # Verify config exists
    if not Path(args.config).exists():
        print(f"Error: Config file not found: {args.config}")
        return 1

    run_benchmark(args.config, args.output, resume_from=args.resume)
    return 0


if __name__ == "__main__":
    exit(main())
