#!/usr/bin/env python3
"""
Groq CLI with robust timeout handling and retry logic.

Usage:
  echo "prompt" | groq-cli [--model MODEL]
  groq-cli "prompt" [--model MODEL]
  groq-cli --prompt "prompt" [--model MODEL]

Models: 8b (default), 70b, mixtral
Timeout: 자동 설정 (8b: 30s, 70b: 45s, mixtral: 60s)

Examples:
  echo "2+2는?" | groq-cli
  echo "긴 문서 요약" | groq-cli --model mixtral
  groq-cli "간단한 질문" --model 8b
  groq-cli --prompt "간단한 질문" --model 70b
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


class GroqProvider(BaseProvider):
    """Groq provider with streaming output."""

    PROVIDER = "groq"
    API_KEY_ENV = "GROQ_API_KEY"
    MODEL_MAP = {
        "8b": "llama-3.1-8b-instant",
        "70b": "llama-3.1-70b-versatile",
        "mixtral": "mixtral-8x7b-32768",
    }
    DEFAULT_MODEL = "8b"

    # Timeout configuration (seconds) - Groq is super fast!
    TIMEOUT_CONFIG = {
        "8b": 30,
        "70b": 45,
        "mixtral": 60,
    }

    def create_client(self, timeout_ms: int):
        """Create Groq client with timeout."""
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
        )

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using Groq API with streaming."""
        # Build request params
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,  # Groq is faster with streaming
        }

        # Generate response with streaming
        response = client.chat.completions.create(**request_params)

        full_response = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content

        print()  # Final newline

        if full_response:
            return full_response
        else:
            raise Exception("Empty response")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add Groq-specific arguments."""
        parser.add_argument(
            "--model",
            "-m",
            choices=["8b", "70b", "mixtral"],
            default="8b",
            help="사용할 모델 (기본값: 8b)",
        )


if __name__ == "__main__":
    GroqProvider().run()
