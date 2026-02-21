#!/usr/bin/env python3
"""
Mistral AI CLI with robust timeout handling, streaming, and retry logic.

Usage:
  echo "prompt" | mistral-cli [options]
  mistral-cli "prompt" [options]
  mistral-cli --model medium --temperature 0.5 "prompt"

Models:
  - large: mistral-large-latest (최고 추론, 120s timeout)
  - medium: mistral-medium-3 (균형, 코딩 강점, 90s timeout)
  - small: mistral-small-latest (비용 효율, 60s timeout)
  - codestral: codestral-latest (코드 특화, 90s timeout)
  - devstral: devstral-2 (소프트웨어 엔지니어링, 90s timeout)
"""

import argparse
import os
import sys

# Check if Mistral CLI is enabled BEFORE importing heavy dependencies
if not os.environ.get("SYNOD_ENABLE_MISTRAL"):
    sys.stderr.write(
        "[Mistral CLI] 비활성화 상태입니다.\n"
        "활성화하려면: export SYNOD_ENABLE_MISTRAL=1\n"
        "또는 OpenRouter를 통해 사용: openrouter-cli --model mistral\n"
    )
    sys.exit(2)

# Suppress warnings
import warnings

warnings.filterwarnings("ignore")

try:
    import httpx
    from mistralai import Mistral
except ImportError:
    print("Error: mistralai not installed. Run: pip install mistralai", file=sys.stderr)
    sys.exit(1)

# Import base provider
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_provider import BaseProvider


class MistralProvider(BaseProvider):
    """Mistral AI CLI provider with streaming support."""

    PROVIDER = "mistral"
    API_KEY_ENV = "MISTRAL_API_KEY"
    MODEL_MAP = {
        "large": "mistral-large-latest",
        "medium": "mistral-medium-3",
        "small": "mistral-small-latest",
        "codestral": "codestral-latest",
        "devstral": "devstral-2",
    }
    DEFAULT_MODEL = "medium"

    # Default timeout per model (seconds)
    DEFAULT_TIMEOUT = {
        "large": 120,
        "medium": 90,
        "small": 60,
        "codestral": 90,
        "devstral": 90,
    }

    def create_client(self, timeout_ms: int):
        """Create Mistral client with custom httpx timeout."""
        api_key = self.validate_api_key()
        timeout_seconds = timeout_ms / 1000
        timeout_config = httpx.Timeout(
            connect=5.0, read=float(timeout_seconds), write=5.0, pool=5.0
        )
        http_client = httpx.Client(timeout=timeout_config)
        return Mistral(api_key=api_key, http_client=http_client)

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using Mistral API with streaming support."""
        args = kwargs.get("args")
        use_streaming = not args.no_stream if hasattr(args, "no_stream") else True
        temperature = args.temperature if hasattr(args, "temperature") else 0.7

        messages = [{"role": "user", "content": prompt}]

        if use_streaming:
            # Streaming mode - prints directly to stdout and returns accumulated response
            stream = client.chat.stream(model=model, messages=messages, temperature=temperature)
            full_response = ""
            for chunk in stream:
                if chunk.data.choices[0].delta.content:
                    content = chunk.data.choices[0].delta.content
                    full_response += content
                    print(content, end="", flush=True)
            print()  # Final newline
            return full_response
        else:
            # Non-streaming mode
            response = client.chat.complete(model=model, messages=messages, temperature=temperature)
            return response.choices[0].message.content

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add Mistral-specific arguments."""
        parser.add_argument(
            "-m",
            "--model",
            choices=["large", "medium", "small", "codestral", "devstral"],
            default="medium",
            help="Model to use (default: medium)",
        )
        parser.add_argument(
            "--temperature",
            type=float,
            default=0.7,
            help="Temperature for generation (default: 0.7)",
        )
        parser.add_argument(
            "--no-stream",
            action="store_true",
            help="Disable streaming (not recommended for long prompts)",
        )

    def get_timeout_ms(self, args, model_key: str, default_ms: int = 300_000) -> int:
        """Override to use model-specific default timeouts."""
        # Use model-specific default timeout if not provided
        if not (hasattr(args, "timeout") and args.timeout):
            default_ms = self.DEFAULT_TIMEOUT.get(model_key, 90) * 1000

        return super().get_timeout_ms(args, model_key, default_ms)

    def run(self):
        """Override run to add enable gate check."""
        # Enable gate already checked at module level, just call parent
        super().run()


if __name__ == "__main__":
    MistralProvider().run()
