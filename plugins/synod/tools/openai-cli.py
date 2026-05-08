#!/usr/bin/env python3
"""
OpenAI CLI with robust timeout handling and adaptive retry.

Usage:
  echo "prompt" | openai-cli [--model MODEL] [--reasoning LEVEL]
  openai-cli "prompt" [--model MODEL] [--reasoning LEVEL]
  openai-cli --prompt "prompt" [--model MODEL] [--reasoning LEVEL]

Models: gpt54mini (default), gpt4o, o3, o4mini, gpt54, gpt5mini, gpt55
Reasoning: low, medium (default), high (o-series + GPT-5-family models)

Examples:
  echo "2+2는?" | openai-cli
  echo "복잡한 수학" | openai-cli --model o3 --reasoning high
  openai-cli "간단한 질문" --model gpt54mini
  openai-cli --prompt "차세대 모델" --model gpt55 --reasoning high
"""

import argparse
import os
import sys

try:
    import httpx
    from openai import OpenAI
except ImportError:
    sys.stderr.write("Error: openai 패키지가 설치되지 않았습니다.\n")
    sys.stderr.write("설치: pip install openai\n")
    sys.exit(1)

# Import BaseProvider
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_provider import BaseProvider  # noqa: E402


class OpenAIProvider(BaseProvider):
    """OpenAI provider with adaptive reasoning downgrade."""

    PROVIDER = "openai"
    API_KEY_ENV = "OPENAI_API_KEY"
    MODEL_MAP = {
        "gpt4o": "gpt-4o",
        "o3": "o3",
        "o4mini": "o4-mini",
        "gpt54": "gpt-5.4",
        "gpt5mini": "gpt-5-mini",
        "gpt54mini": "gpt-5.4-mini",
        "gpt55": "gpt-5.5",
    }
    DEFAULT_MODEL = "gpt54mini"

    # Reasoning models support reasoning_effort
    REASONING_MODELS = ["o3", "o4mini", "gpt54", "gpt5mini", "gpt54mini", "gpt55"]

    # Timeout configuration (seconds). Values calibrated against measured p50/max latency
    # across 5-problem GSM8K-style A/B (2026-05-07): values are P50 × 30 to absorb tail.
    TIMEOUT_CONFIG = {
        ("gpt4o", "low"): 60,
        ("gpt4o", "medium"): 60,
        ("gpt4o", "high"): 60,
        ("o3", "low"): 120,
        ("o3", "medium"): 180,
        ("o3", "high"): 300,
        ("o4mini", "low"): 60,
        ("o4mini", "medium"): 90,
        ("o4mini", "high"): 120,
        ("gpt54", "low"): 90,
        ("gpt54", "medium"): 120,
        ("gpt54", "high"): 180,
        ("gpt5mini", "low"): 45,
        ("gpt5mini", "medium"): 60,
        ("gpt5mini", "high"): 90,
        ("gpt54mini", "low"): 60,
        ("gpt54mini", "medium"): 90,
        ("gpt54mini", "high"): 120,
        ("gpt55", "low"): 90,
        ("gpt55", "medium"): 120,
        ("gpt55", "high"): 180,
    }

    # Reasoning levels for downgrade
    REASONING_LEVELS = ["high", "medium", "low"]

    def get_timeout_ms(self, args, model_key: str, default_ms: int = 300_000) -> int:
        """Use model/reasoning-specific timeout defaults when no timeout is supplied."""
        reasoning = args.reasoning if hasattr(args, "reasoning") else "medium"
        configured_timeout = self.TIMEOUT_CONFIG.get((model_key, reasoning))
        if configured_timeout is not None:
            default_ms = configured_timeout * 1000
        return super().get_timeout_ms(args, model_key, default_ms=default_ms)

    def create_client(self, timeout_ms: int):
        """Create OpenAI client with timeout."""
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(api_key=api_key.strip(), timeout=httpx.Timeout(timeout_sec, connect=10.0))

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        args = kwargs.get("args")
        reasoning = args.reasoning if hasattr(args, "reasoning") else "medium"

        # Build request params
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Extract model key for REASONING_MODELS check
        model_key = None
        for key, value in self.MODEL_MAP.items():
            if value == model:
                model_key = key
                break

        # Add reasoning_effort for reasoning models
        if model_key in self.REASONING_MODELS:
            request_params["reasoning_effort"] = reasoning

        # Generate response
        response = client.chat.completions.create(**request_params)

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            raise Exception("Empty response")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add OpenAI-specific arguments."""
        parser.add_argument(
            "--model",
            "-m",
            choices=["gpt4o", "o3", "o4mini", "gpt54", "gpt5mini", "gpt54mini", "gpt55"],
            default="gpt54mini",
            help="사용할 모델 (기본값: gpt54mini)",
        )
        parser.add_argument(
            "--reasoning",
            "-r",
            choices=["low", "medium", "high"],
            default="medium",
            help="Reasoning 레벨 - reasoning 지원 모델 전용 (기본값: medium)",
        )
        parser.add_argument(
            "--no-adaptive",
            action="store_true",
            help="적응형 재시도 비활성화 (reasoning 레벨 다운그레이드 안함)",
        )

    def generate_with_retry(
        self, client, model: str, prompt: str, max_retries: int = 3, **kwargs
    ) -> str:
        """Generate with adaptive reasoning downgrade on timeout."""
        args = kwargs.get("args")
        adaptive = not (hasattr(args, "no_adaptive") and args.no_adaptive)
        reasoning = args.reasoning if hasattr(args, "reasoning") else "medium"

        # Extract model key from model name
        model_key = None
        for key, value in self.MODEL_MAP.items():
            if value == model:
                model_key = key
                break

        current_reasoning = reasoning
        current_idx = (
            self.REASONING_LEVELS.index(current_reasoning)
            if current_reasoning in self.REASONING_LEVELS
            else 1
        )

        for attempt in range(max_retries):
            try:
                # Update args with current reasoning
                if hasattr(args, "reasoning"):
                    args.reasoning = current_reasoning

                return self.generate(client, model, prompt, **kwargs)

            except Exception as e:
                error_str = str(e)
                is_retryable, error_category = self.is_retryable_error(error_str)

                if is_retryable and attempt < max_retries - 1:
                    # Try adaptive downgrade for reasoning models on timeout/overload
                    if (
                        adaptive
                        and error_category == "timeout_or_overload"
                        and model_key in self.REASONING_MODELS
                        and current_idx < len(self.REASONING_LEVELS) - 1
                    ):
                        current_idx += 1
                        current_reasoning = self.REASONING_LEVELS[current_idx]
                        print(
                            f"[Retry {attempt + 1}/{max_retries}] Timeout - downgrading reasoning to '{current_reasoning}'",
                            file=sys.stderr,
                        )
                    else:
                        self.wait_with_backoff(attempt, error_category, max_retries)
                    continue
                else:
                    print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
                    sys.exit(1)

        print(f"Error: Max retries ({max_retries}) exceeded", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    OpenAIProvider().run()
