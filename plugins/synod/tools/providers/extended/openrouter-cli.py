#!/usr/bin/env python3
"""
OpenRouter CLI with multi-model support and robust timeout handling.

Usage:
  echo "prompt" | openrouter-cli [--model MODEL]
  openrouter-cli "prompt" [--model MODEL]
  openrouter-cli --prompt "prompt" [--model MODEL]

Models: claude (default), gemini, llama, mistral, qwen, deepseek, grok

Examples:
  echo "2+2는?" | openrouter-cli
  echo "복잡한 질문" | openrouter-cli --model gemini
  openrouter-cli "간단한 질문" --model claude
  openrouter-cli --prompt "간단한 질문" --model llama
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
from base_provider import BaseProvider


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider with custom headers."""

    PROVIDER = "openrouter"
    API_KEY_ENV = "OPENROUTER_API_KEY"
    MODEL_MAP = {
        "claude": "anthropic/claude-sonnet-4",
        "gemini": "google/gemini-2.5-flash-preview-05-20",
        "llama": "meta-llama/llama-3.3-70b-instruct",
        "mistral": "mistralai/mistral-large-2411",
        "qwen": "qwen/qwen-2.5-72b-instruct",
        "deepseek": "deepseek/deepseek-chat-v3-0324",
        "grok": "x-ai/grok-2-1212",
    }
    DEFAULT_MODEL = "claude"

    # OpenRouter required headers
    DEFAULT_HEADERS = {
        "HTTP-Referer": "https://github.com/quantsquirrel/claude-synod-debate",
        "X-Title": "Synod CLI",
    }

    def create_client(self, timeout_ms: int):
        """Create OpenRouter client with timeout and custom headers."""
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(
            api_key=api_key.strip(),
            base_url="https://openrouter.ai/api/v1",
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
            default_headers=self.DEFAULT_HEADERS,
        )

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using OpenRouter API."""
        # Build request params
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Non-streaming request
        response = client.chat.completions.create(**request_params)

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            raise Exception("Empty response from API")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add OpenRouter-specific arguments."""
        parser.add_argument(
            "--model",
            "-m",
            choices=list(self.MODEL_MAP.keys()),
            default="claude",
            help="사용할 모델 (기본값: claude)",
        )


if __name__ == "__main__":
    OpenRouterProvider().run()
