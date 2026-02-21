#!/usr/bin/env python3
"""
DeepSeek CLI with robust timeout handling and adaptive retry.

Usage:
  echo "prompt" | deepseek-cli [--model MODEL] [--reasoning LEVEL]
  deepseek-cli "prompt" [--model MODEL] [--reasoning LEVEL]
  deepseek-cli --prompt "prompt" [--model MODEL] [--reasoning LEVEL]

Models: chat (default), reasoner
Reasoning: low, medium (default), high (reasoner only)

Examples:
  echo "2+2는?" | deepseek-cli
  echo "복잡한 수학" | deepseek-cli --model reasoner --reasoning high
  deepseek-cli "간단한 질문" --model chat
  deepseek-cli --prompt "간단한 질문" --model chat
"""

import argparse
import os
import random
import sys
import time

try:
    import httpx
    from openai import OpenAI
except ImportError:
    sys.stderr.write("Error: openai 패키지가 설치되지 않았습니다.\n")
    sys.stderr.write("설치: pip install openai\n")
    sys.exit(1)

# Import BaseProvider
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_provider import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider with adaptive reasoning downgrade."""

    PROVIDER = "deepseek"
    API_KEY_ENV = "DEEPSEEK_API_KEY"
    MODEL_MAP = {"chat": "deepseek-chat", "reasoner": "deepseek-reasoner"}
    DEFAULT_MODEL = "chat"

    # Reasoner model requires streaming
    REASONER_MODELS = ["reasoner"]

    # Timeout configuration (seconds)
    TIMEOUT_CONFIG = {
        ("chat", "low"): 60,
        ("chat", "medium"): 60,
        ("chat", "high"): 120,
        ("reasoner", "low"): 180,
        ("reasoner", "medium"): 300,
        ("reasoner", "high"): 600,
    }

    # Reasoning levels for downgrade
    REASONING_LEVELS = ["high", "medium", "low"]

    def create_client(self, timeout_ms: int):
        """Create DeepSeek client with timeout."""
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.deepseek.com",
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
        )

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using DeepSeek API."""
        args = kwargs.get("args")
        reasoning = args.reasoning if hasattr(args, "reasoning") else "medium"

        # Build request params
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Extract model key for REASONER_MODELS check
        model_key = None
        for key, value in self.MODEL_MAP.items():
            if value == model:
                model_key = key
                break

        # Reasoner requires streaming and reasoning_effort
        if model_key in self.REASONER_MODELS:
            request_params["reasoning_effort"] = reasoning
            request_params["stream"] = True

            # Stream response
            stream = client.chat.completions.create(**request_params)
            content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content

            if content:
                return content
            else:
                raise Exception("Empty response")
        else:
            # Non-streaming for chat model
            response = client.chat.completions.create(**request_params)

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                raise Exception("Empty response")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add DeepSeek-specific arguments."""
        parser.add_argument(
            "--model",
            "-m",
            choices=["chat", "reasoner"],
            default="chat",
            help="사용할 모델 (기본값: chat)",
        )
        parser.add_argument(
            "--reasoning",
            "-r",
            choices=["low", "medium", "high"],
            default="medium",
            help="Reasoning 레벨 - reasoner 모델 전용 (기본값: medium)",
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
                    # Try adaptive downgrade for reasoner on timeout/overload
                    if (
                        adaptive
                        and error_category == "timeout_or_overload"
                        and model_key in self.REASONER_MODELS
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
    DeepSeekProvider().run()
