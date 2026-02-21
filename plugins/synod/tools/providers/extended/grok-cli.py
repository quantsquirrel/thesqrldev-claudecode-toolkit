#!/usr/bin/env python3
"""
xAI Grok CLI with robust timeout handling and adaptive retry.

Usage:
  echo "prompt" | grok-cli [--model MODEL]
  grok-cli "prompt" [--model MODEL]
  grok-cli --prompt "prompt" [--model MODEL]

Models: fast (default), grok4, mini, vision
Timeout: auto-selected based on model

Examples:
  echo "2+2는?" | grok-cli
  echo "복잡한 질문" | grok-cli --model grok4
  grok-cli "간단한 질문" --model fast
  grok-cli --prompt "이미지 분석" --model vision
"""

import argparse
import os
import sys

# Check if Grok CLI is enabled BEFORE importing heavy dependencies
if not os.environ.get("SYNOD_ENABLE_GROK"):
    sys.stderr.write(
        "[Grok CLI] 비활성화 상태입니다.\n"
        "활성화하려면: export SYNOD_ENABLE_GROK=1\n"
        "또는 OpenRouter를 통해 사용: openrouter-cli --model grok\n"
    )
    sys.exit(2)

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


class GrokProvider(BaseProvider):
    """xAI Grok provider with enable gate."""

    PROVIDER = "grok"
    API_KEY_ENV = "XAI_API_KEY"
    MODEL_MAP = {
        "fast": "grok-4-fast",
        "grok4": "grok-4",
        "mini": "grok-3-mini",
        "vision": "grok-2-vision-1212",
    }
    DEFAULT_MODEL = "fast"

    # Timeout configuration (seconds)
    TIMEOUT_CONFIG = {
        "fast": 60,
        "mini": 60,
        "grok4": 120,
        "vision": 90,
    }

    def create_client(self, timeout_ms: int):
        """Create xAI Grok client with timeout."""
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.x.ai/v1",
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
        )

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using xAI Grok API."""
        # Build request params
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        # Generate response
        response = client.chat.completions.create(**request_params)

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            raise Exception("Empty response")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add Grok-specific arguments."""
        parser.add_argument(
            "--model",
            "-m",
            choices=["fast", "grok4", "mini", "vision"],
            default="fast",
            help="사용할 모델 (기본값: fast)",
        )

    def run(self):
        """Override run() to add enable gate check."""
        # Enable gate is already checked at module level (lines 26-33)
        # Just call parent run()
        super().run()


if __name__ == "__main__":
    GrokProvider().run()
