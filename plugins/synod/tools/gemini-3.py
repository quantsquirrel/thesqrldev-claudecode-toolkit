#!/usr/bin/env python3
"""
Gemini 3 CLI with robust timeout handling, streaming, and adaptive retry.

Usage:
  echo "prompt" | gemini-3 [options]
  gemini-3 "prompt" [options]
  gemini-3 --model flash --thinking high "prompt"

Models: flash (default), pro
Thinking: minimal, low, medium (default), high
"""

import argparse
import os
import sys

# Suppress warnings
import warnings

warnings.filterwarnings("ignore")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai not installed. Run: pip install google-genai", file=sys.stderr)
    sys.exit(1)

# Import base provider
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_provider import BaseProvider


class GeminiProvider(BaseProvider):
    """Gemini 3 CLI provider with thinking budget and adaptive retry."""

    PROVIDER = "gemini"
    API_KEY_ENV = "GEMINI_API_KEY"
    MODEL_MAP = {
        "flash": "gemini-3-flash-preview",
        "pro": "gemini-3-pro-preview",
        "2.5-flash": "gemini-2.5-flash",
        "2.5-pro": "gemini-2.5-pro",
    }
    DEFAULT_MODEL = "flash"

    # Thinking budget mapping (tokens)
    THINKING_MAP = {
        "minimal": 50,
        "low": 200,
        "medium": 500,
        "high": 2000,
        "max": 10000,
    }

    # Retry levels (progressive downgrade)
    RETRY_LEVELS = ["high", "medium", "low", "minimal"]

    def validate_api_key(self) -> str:
        """Validate API key with GOOGLE_API_KEY fallback."""
        # GOOGLE_API_KEY fallback: GEMINI_API_KEY 미설정 시 복사
        if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
        return super().validate_api_key()

    def create_client(self, timeout_ms: int):
        """Create Gemini client with timeout."""
        api_key = self.validate_api_key()
        return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using Gemini API with streaming support."""
        args = kwargs.get("args")
        thinking_level = args.thinking if hasattr(args, "thinking") else "medium"
        use_streaming = not args.no_stream if hasattr(args, "no_stream") else True
        temperature = args.temperature if hasattr(args, "temperature") else 0.7

        thinking_budget = self.THINKING_MAP.get(thinking_level, 500)
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
            temperature=temperature,
        )

        if use_streaming:
            # Streaming mode - prevents timeout for long responses
            stream = client.models.generate_content_stream(
                model=model, contents=prompt, config=config
            )
            full_response = ""
            for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
            return full_response
        else:
            # Non-streaming mode
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            return response.text

    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add Gemini-specific arguments."""
        parser.add_argument(
            "-m",
            "--model",
            choices=["flash", "pro", "2.5-flash", "2.5-pro"],
            default="flash",
            help="Model to use (default: flash)",
        )
        parser.add_argument(
            "-t",
            "--thinking",
            choices=["minimal", "low", "medium", "high", "max"],
            default="medium",
            help="Thinking level (default: medium)",
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
        parser.add_argument(
            "--no-adaptive",
            action="store_true",
            help="Disable adaptive retry (thinking level downgrade)",
        )

    def generate_with_retry(
        self, client, model: str, prompt: str, max_retries: int = 3, **kwargs
    ) -> str:
        """Generate with adaptive retry - downgrades thinking level on timeout."""
        args = kwargs.get("args")
        thinking_level = args.thinking if hasattr(args, "thinking") else "medium"
        adaptive = not args.no_adaptive if hasattr(args, "no_adaptive") else True

        current_level = thinking_level
        current_level_idx = (
            self.RETRY_LEVELS.index(current_level) if current_level in self.RETRY_LEVELS else 1
        )

        for attempt in range(max_retries):
            try:
                # Update thinking level in kwargs for generate()
                if hasattr(args, "thinking"):
                    args.thinking = current_level
                return self.generate(client, model, prompt, **kwargs)

            except Exception as e:
                error_str = str(e)
                is_retryable, error_category = self.is_retryable_error(error_str)

                if is_retryable and attempt < max_retries - 1:
                    # Try to downgrade thinking level on timeout/overload
                    if (
                        error_category == "timeout_or_overload"
                        and adaptive
                        and current_level_idx < len(self.RETRY_LEVELS) - 1
                    ):
                        current_level_idx += 1
                        current_level = self.RETRY_LEVELS[current_level_idx]
                        print(
                            f"[Retry {attempt + 1}/{max_retries}] Timeout - downgrading thinking to '{current_level}'",
                            file=sys.stderr,
                        )

                    self.wait_with_backoff(attempt, error_category, max_retries)
                    continue
                else:
                    print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
                    sys.exit(1)

        print(f"Error: Max retries ({max_retries}) exceeded", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    GeminiProvider().run()
