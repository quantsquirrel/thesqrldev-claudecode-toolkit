#!/usr/bin/env python3
"""
Base provider class for Synod AI CLI tools.

Extracts common patterns from all provider CLIs:
- API key validation
- Model override via environment variables
- Retry logic with exponential backoff
- ModelStats integration (latency tracking, adaptive timeout)
- Argument parsing
- Input handling (stdin/args/positional)
- Security: input sanitization, key validation, error sanitization
"""

import argparse
import os
import random
import re
import sys
import time
from abc import ABC, abstractmethod

# Import model stats for latency tracking
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from model_stats import ModelStats

    _stats_available = True
except ImportError:
    _stats_available = False


class BaseProvider(ABC):
    """Abstract base class for Synod AI provider CLIs."""

    # Subclass must set these class attributes
    PROVIDER: str = ""  # e.g., "gemini", "openai"
    API_KEY_ENV: str = ""  # e.g., "GEMINI_API_KEY"
    MODEL_MAP: dict = {}  # e.g., {"flash": "gemini-3-flash-preview"}
    DEFAULT_MODEL: str = ""  # e.g., "flash"

    @abstractmethod
    def create_client(self, timeout_ms: int):
        """Create provider-specific client with timeout.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Provider-specific client instance
        """
        pass

    @abstractmethod
    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Generate response using provider-specific API.

        Args:
            client: Provider-specific client
            model: Model name (full name, not key)
            prompt: User prompt
            **kwargs: Provider-specific arguments

        Returns:
            Generated response text
        """
        pass

    @abstractmethod
    def add_provider_args(self, parser: argparse.ArgumentParser):
        """Add provider-specific arguments to parser.

        Args:
            parser: ArgumentParser to add arguments to
        """
        pass

    def get_model_with_override(self, model_key: str) -> str:
        """Get model name with optional environment variable override.

        Environment variable format: SYNOD_{PROVIDER}_{MODEL_KEY}
        Example: SYNOD_GEMINI_FLASH=custom-model-name

        Args:
            model_key: Short model key (e.g., "flash", "gpt4o")

        Returns:
            Full model name (from MODEL_MAP or override)
        """
        env_var = f"SYNOD_{self.PROVIDER.upper()}_{model_key.upper().replace('.', '_').replace('-', '_')}"
        override = os.environ.get(env_var)
        if override:
            print(f"[Override] Using {override} (via {env_var})", file=sys.stderr)
            return override
        return self.MODEL_MAP.get(model_key, self.MODEL_MAP.get(self.DEFAULT_MODEL, ""))

    def validate_api_key(self) -> str:
        """Validate and return API key from environment.

        Enhanced validation:
        - Checks key is not empty/whitespace
        - Strips whitespace from key
        - Checks minimum length (10 chars)
        - Warns on suspicious characters (spaces, newlines)

        Returns:
            API key string (stripped of whitespace)

        Raises:
            SystemExit: If API key is invalid
        """
        api_key = os.environ.get(self.API_KEY_ENV)
        if not api_key:
            print(f"Error: {self.API_KEY_ENV} environment variable not set", file=sys.stderr)
            sys.exit(1)

        # Strip whitespace
        api_key = api_key.strip()

        # Check if empty after stripping
        if not api_key:
            print(f"Error: {self.API_KEY_ENV} is empty or only whitespace", file=sys.stderr)
            sys.exit(1)

        # Check minimum length (API keys are typically 30+ chars)
        if len(api_key) < 10:
            print(f"Warning: API key is suspiciously short (less than 10 characters)", file=sys.stderr)

        # Check for suspicious characters (spaces, newlines, tabs)
        if any(char in api_key for char in [' ', '\n', '\r', '\t']):
            print(f"Warning: API key contains suspicious whitespace characters", file=sys.stderr)

        return api_key

    def sanitize_prompt(self, prompt: str) -> str:
        """Sanitize user prompt for security.

        Removes potentially dangerous content:
        - Strips leading/trailing whitespace
        - Removes null bytes
        - Limits length to 1MB (1,000,000 chars)

        Args:
            prompt: Raw prompt string

        Returns:
            Sanitized prompt string (always returns something safe, never crashes)
        """
        if not prompt:
            return ""

        # Strip whitespace
        prompt = prompt.strip()

        # Remove null bytes
        prompt = prompt.replace('\x00', '')

        # Limit to 1MB with warning
        MAX_PROMPT_LENGTH = 1_000_000
        if len(prompt) > MAX_PROMPT_LENGTH:
            print(
                f"Warning: Prompt truncated from {len(prompt)} to {MAX_PROMPT_LENGTH} characters",
                file=sys.stderr
            )
            prompt = prompt[:MAX_PROMPT_LENGTH]

        return prompt

    def get_prompt(self, args, remaining: list) -> str:
        """Get prompt from args, remaining args, or stdin.

        Priority: stdin > --prompt > positional_prompt > remaining args

        Args:
            args: Parsed arguments
            remaining: Remaining unparsed arguments

        Returns:
            Prompt string

        Raises:
            SystemExit: If no prompt is provided
        """
        prompt = None

        # Try stdin first (if not a TTY)
        if not sys.stdin.isatty():
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                prompt = stdin_content

        # Fall back to command-line arguments
        if not prompt:
            if hasattr(args, "prompt") and args.prompt:
                prompt = args.prompt
            elif hasattr(args, "positional_prompt") and args.positional_prompt:
                prompt = args.positional_prompt
            elif remaining:
                prompt = " ".join(remaining)

        if not prompt:
            print("Error: No prompt provided", file=sys.stderr)
            sys.exit(1)

        return self.sanitize_prompt(prompt)

    def get_timeout_ms(self, args, model_key: str, default_ms: int = 300_000) -> int:
        """Get timeout in milliseconds with adaptive support and bounds checking.

        If SYNOD_V2_ADAPTIVE_TIMEOUT=1 and sufficient stats exist,
        uses P99+epsilon timeout from historical data.

        Timeout bounds:
        - Minimum: 5,000ms (5 seconds)
        - Maximum: 600,000ms (10 minutes)

        Args:
            args: Parsed arguments
            model_key: Model key for stats lookup
            default_ms: Default timeout in milliseconds

        Returns:
            Timeout in milliseconds (clamped to bounds)
        """
        MIN_TIMEOUT_MS = 5_000  # 5 seconds
        MAX_TIMEOUT_MS = 600_000  # 10 minutes

        # Start with provided timeout or default
        if hasattr(args, "timeout") and args.timeout:
            timeout_ms = args.timeout * 1000
        else:
            timeout_ms = default_ms

        # Apply adaptive timeout if enabled
        if _stats_available and os.environ.get("SYNOD_V2_ADAPTIVE_TIMEOUT", "0") == "1":
            stats = ModelStats()
            if stats.has_sufficient_data(self.PROVIDER, model_key):
                timeout_ms = int(stats.get_dynamic_timeout(self.PROVIDER, model_key))
                if hasattr(args, "verbose") and args.verbose:
                    print(f"[Adaptive] Timeout: {timeout_ms}ms (P99+epsilon)", file=sys.stderr)

        # Apply bounds with warnings
        original_timeout = timeout_ms
        if timeout_ms < MIN_TIMEOUT_MS:
            timeout_ms = MIN_TIMEOUT_MS
            print(
                f"Warning: Timeout too low ({original_timeout}ms), clamped to minimum {MIN_TIMEOUT_MS}ms",
                file=sys.stderr
            )
        elif timeout_ms > MAX_TIMEOUT_MS:
            timeout_ms = MAX_TIMEOUT_MS
            print(
                f"Warning: Timeout too high ({original_timeout}ms), clamped to maximum {MAX_TIMEOUT_MS}ms",
                file=sys.stderr
            )

        return timeout_ms

    def record_latency(self, model_key: str, latency_ms: float):
        """Record latency to model stats.

        Args:
            model_key: Model key for stats recording
            latency_ms: Latency in milliseconds
        """
        if _stats_available:
            try:
                ModelStats().record_latency(self.PROVIDER, model_key, latency_ms)
            except Exception:
                pass  # Don't fail on stats recording errors

    def sanitize_error(self, error: str) -> str:
        """Sanitize error messages to prevent API key leakage.

        Security measures:
        - Truncates to 500 characters max
        - Removes common API key patterns (sk-*, gsk_*, xai-*, etc.)
        - Always returns a safe string, never crashes

        Args:
            error: Raw error message

        Returns:
            Sanitized error message (safe to display)
        """
        if not error:
            return "Unknown error"

        # Truncate to max length
        MAX_ERROR_LENGTH = 500
        if len(error) > MAX_ERROR_LENGTH:
            error = error[:MAX_ERROR_LENGTH] + "... (truncated)"

        # Remove common API key patterns
        # Patterns: sk-*, gsk_*, xai-*, api_key=*, token=*, bearer *, key: *
        patterns = [
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI/Anthropic style
            r'gsk_[a-zA-Z0-9]{20,}',  # Google style
            r'xai-[a-zA-Z0-9]{20,}',  # xAI/Grok style
            r'api[_-]?key[=:]\s*[\'"]?[a-zA-Z0-9_-]{10,}[\'"]?',  # api_key= or api-key:
            r'token[=:]\s*[\'"]?[a-zA-Z0-9_-]{10,}[\'"]?',  # token=
            r'bearer\s+[a-zA-Z0-9_-]{10,}',  # Bearer tokens
            r'key[=:]\s*[\'"]?[a-zA-Z0-9_-]{20,}[\'"]?',  # key=
        ]

        for pattern in patterns:
            error = re.sub(pattern, '[REDACTED]', error, flags=re.IGNORECASE)

        return error

    def is_retryable_error(self, error_str: str) -> tuple[bool, str]:
        """Check if error is retryable and return error category.

        Args:
            error_str: Error message string

        Returns:
            Tuple of (is_retryable, error_category)
            Categories: "timeout_or_overload", "rate_limit", "non_retryable"
        """
        error_str_lower = error_str.lower()

        is_timeout = any(
            x in error_str_lower
            for x in ["timeout", "timed out", "deadline", "504", "gateway"]
        )
        is_rate_limit = any(
            x in error_str_lower for x in ["429", "rate", "quota", "resource_exhausted"]
        )
        is_overloaded = any(
            x in error_str_lower for x in ["503", "overloaded", "unavailable", "502"]
        )

        if is_timeout or is_overloaded:
            return True, "timeout_or_overload"
        elif is_rate_limit:
            return True, "rate_limit"
        else:
            return False, "non_retryable"

    def wait_with_backoff(self, attempt: int, error_category: str, max_retries: int):
        """Wait with exponential backoff.

        Rate limits get longer backoff (2^(attempt+2)) than timeouts (2^attempt).

        Args:
            attempt: Current attempt number (0-indexed)
            error_category: Error category from is_retryable_error
            max_retries: Maximum number of retries
        """
        if error_category == "rate_limit":
            wait_time = (2 ** (attempt + 2)) + random.random()
            print(
                f"[Retry {attempt + 1}/{max_retries}] Rate limited - waiting {wait_time:.1f}s",
                file=sys.stderr,
            )
        else:
            wait_time = (2**attempt) + random.random()
            print(f"[Retry {attempt + 1}/{max_retries}] Retrying...", file=sys.stderr)

        time.sleep(wait_time)

    def build_parser(self) -> argparse.ArgumentParser:
        """Build argument parser with common arguments.

        Returns:
            ArgumentParser with common + provider-specific arguments
        """
        parser = argparse.ArgumentParser(
            description=f"{self.PROVIDER.title()} CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Common arguments
        parser.add_argument(
            "positional_prompt", nargs="?", default=None, metavar="prompt", help="Prompt text"
        )
        parser.add_argument(
            "--prompt", "-p", default=None, help="Prompt (can also use positional)"
        )
        parser.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
        parser.add_argument("--retries", type=int, default=3, help="Max retries (default: 3)")
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

        # Let subclass add provider-specific args
        self.add_provider_args(parser)

        return parser

    def generate_with_retry(
        self, client, model: str, prompt: str, max_retries: int = 3, **kwargs
    ) -> str:
        """Generate with retry logic.

        Subclasses can override for custom retry behavior (e.g., adaptive downgrade).

        Args:
            client: Provider-specific client
            model: Model name
            prompt: User prompt
            max_retries: Maximum number of retries
            **kwargs: Provider-specific arguments

        Returns:
            Generated response text

        Raises:
            SystemExit: On non-retryable error or max retries exceeded
        """
        for attempt in range(max_retries):
            try:
                return self.generate(client, model, prompt, **kwargs)
            except Exception as e:
                error_str = str(e)
                error_type_name = type(e).__name__

                is_retryable, error_category = self.is_retryable_error(error_str)

                if is_retryable and attempt < max_retries - 1:
                    self.wait_with_backoff(attempt, error_category, max_retries)
                    continue
                else:
                    # Sanitize error message before printing
                    safe_error = self.sanitize_error(error_str)
                    print(f"Error: {error_type_name}: {safe_error}", file=sys.stderr)
                    sys.exit(1)

        print(f"Error: Max retries ({max_retries}) exceeded", file=sys.stderr)
        sys.exit(1)

    def run(self):
        """Main entry point for CLI execution.

        Flow:
        1. Parse arguments
        2. Get prompt from args/stdin
        3. Validate API key
        4. Get timeout (with adaptive support)
        5. Create client
        6. Generate with retry
        7. Record latency
        8. Print response
        """
        parser = self.build_parser()
        args, remaining = parser.parse_known_args()

        # Get prompt
        prompt = self.get_prompt(args, remaining)

        # Validate API key
        api_key = self.validate_api_key()

        # Get model key
        model_key = args.model if hasattr(args, "model") else self.DEFAULT_MODEL

        # Get timeout
        timeout_ms = self.get_timeout_ms(args, model_key)

        # Create client
        client = self.create_client(timeout_ms)

        # Get model name with override
        model_name = self.get_model_with_override(model_key)

        if args.verbose:
            print(f"Provider: {self.PROVIDER}", file=sys.stderr)
            print(f"Model: {model_name}", file=sys.stderr)
            print(f"Timeout: {timeout_ms / 1000:.0f}s", file=sys.stderr)

        # Generate with retry and latency tracking
        start_time = time.time()
        max_retries = args.retries if hasattr(args, "retries") else 3
        response = self.generate_with_retry(
            client, model_name, prompt, max_retries=max_retries, args=args
        )

        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        self.record_latency(model_key, latency_ms)

        # Print response
        print(response)


if __name__ == "__main__":
    print("This is a base class. Import and subclass it in your provider CLI.", file=sys.stderr)
    sys.exit(1)
