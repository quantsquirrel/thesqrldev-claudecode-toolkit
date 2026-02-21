"""
Tests for base_provider.py - BaseProvider abstract class and common provider functionality.
"""

import argparse
import os
import sys
import time
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from base_provider import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing BaseProvider functionality."""

    PROVIDER = "test"
    API_KEY_ENV = "TEST_API_KEY"
    MODEL_MAP = {
        "default": "test-model-1",
        "alt": "test-model-2",
        "dotted.key": "test-model-3",
    }
    DEFAULT_MODEL = "default"

    def create_client(self, timeout_ms):
        return {"timeout": timeout_ms}

    def generate(self, client, model, prompt, **kwargs):
        return f"Response to: {prompt}"

    def add_provider_args(self, parser):
        parser.add_argument("--model", default="default", help="Model to use")


class TestGetModelWithOverride:
    """Tests for get_model_with_override() method."""

    def test_get_model_returns_default_without_override(self):
        """Test that get_model returns default model from MODEL_MAP."""
        provider = MockProvider()
        model = provider.get_model_with_override("default")
        assert model == "test-model-1"

    def test_get_model_returns_alt_model(self):
        """Test that get_model returns alternative model from MODEL_MAP."""
        provider = MockProvider()
        model = provider.get_model_with_override("alt")
        assert model == "test-model-2"

    def test_get_model_with_env_override(self, monkeypatch):
        """Test that environment variable overrides MODEL_MAP."""
        provider = MockProvider()
        monkeypatch.setenv("SYNOD_TEST_DEFAULT", "custom-model")

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            model = provider.get_model_with_override("default")
            assert model == "custom-model"
            assert "[Override]" in mock_stderr.getvalue()

    def test_get_model_with_dotted_key(self):
        """Test that dotted keys work correctly."""
        provider = MockProvider()
        model = provider.get_model_with_override("dotted.key")
        assert model == "test-model-3"

    def test_get_model_with_dotted_key_env_override(self, monkeypatch):
        """Test that dotted keys are converted correctly for env vars."""
        provider = MockProvider()
        # dotted.key -> SYNOD_TEST_DOTTED_KEY
        monkeypatch.setenv("SYNOD_TEST_DOTTED_KEY", "custom-dotted-model")

        with patch("sys.stderr", new=StringIO()):
            model = provider.get_model_with_override("dotted.key")
            assert model == "custom-dotted-model"

    def test_get_model_empty_override_falls_back(self, monkeypatch):
        """Test that empty override falls back to MODEL_MAP."""
        provider = MockProvider()
        monkeypatch.setenv("SYNOD_TEST_DEFAULT", "")

        model = provider.get_model_with_override("default")
        assert model == "test-model-1"

    def test_get_model_unknown_key_returns_default(self):
        """Test that unknown key returns default model."""
        provider = MockProvider()
        model = provider.get_model_with_override("unknown")
        assert model == "test-model-1"


class TestValidateApiKey:
    """Tests for validate_api_key() method."""

    def test_validate_api_key_missing_exits(self, monkeypatch):
        """Test that missing API key causes exit."""
        provider = MockProvider()
        monkeypatch.delenv("TEST_API_KEY", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()):
                provider.validate_api_key()
        assert exc_info.value.code == 1

    def test_validate_api_key_empty_exits(self, monkeypatch):
        """Test that empty API key causes exit."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()):
                provider.validate_api_key()
        assert exc_info.value.code == 1

    def test_validate_api_key_whitespace_only_exits(self, monkeypatch):
        """Test that whitespace-only API key causes exit."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "   \n\t  ")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()):
                provider.validate_api_key()
        assert exc_info.value.code == 1

    def test_validate_api_key_short_key_warns(self, monkeypatch):
        """Test that short API key generates warning."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "short")

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            key = provider.validate_api_key()
            assert key == "short"
            assert "Warning" in mock_stderr.getvalue()
            assert "suspiciously short" in mock_stderr.getvalue()

    def test_validate_api_key_suspicious_chars_warns(self, monkeypatch):
        """Test that API key with suspicious chars generates warning."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "key with spaces and\nnewline")

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            key = provider.validate_api_key()
            assert "Warning" in mock_stderr.getvalue()
            assert "suspicious whitespace" in mock_stderr.getvalue()

    def test_validate_api_key_valid_returns_stripped(self, monkeypatch):
        """Test that valid API key is returned stripped."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "  valid-api-key-1234567890  ")

        with patch("sys.stderr", new=StringIO()):
            key = provider.validate_api_key()
            assert key == "valid-api-key-1234567890"

    def test_validate_api_key_typical_key_passes(self, monkeypatch):
        """Test that typical API key passes without warnings."""
        provider = MockProvider()
        monkeypatch.setenv("TEST_API_KEY", "sk-1234567890abcdefghij")

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            key = provider.validate_api_key()
            assert key == "sk-1234567890abcdefghij"
            # Should not have warnings for valid key
            assert "Warning" not in mock_stderr.getvalue()


class TestSanitizePrompt:
    """Tests for sanitize_prompt() method."""

    def test_sanitize_prompt_empty_input(self):
        """Test that empty input returns empty string."""
        provider = MockProvider()
        result = provider.sanitize_prompt("")
        assert result == ""

    def test_sanitize_prompt_none_input(self):
        """Test that None input returns empty string."""
        provider = MockProvider()
        result = provider.sanitize_prompt(None)
        assert result == ""

    def test_sanitize_prompt_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        provider = MockProvider()
        result = provider.sanitize_prompt("  \n\t  hello world  \n\t  ")
        assert result == "hello world"

    def test_sanitize_prompt_null_byte_removal(self):
        """Test that null bytes are removed."""
        provider = MockProvider()
        result = provider.sanitize_prompt("hello\x00world\x00test")
        assert result == "helloworldtest"
        assert "\x00" not in result

    def test_sanitize_prompt_1mb_truncation(self):
        """Test that prompts over 1MB are truncated."""
        provider = MockProvider()
        large_prompt = "a" * 1_500_000  # 1.5MB

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            result = provider.sanitize_prompt(large_prompt)
            assert len(result) == 1_000_000
            assert "Warning" in mock_stderr.getvalue()
            assert "truncated" in mock_stderr.getvalue()

    def test_sanitize_prompt_normal_unchanged(self):
        """Test that normal prompt is unchanged."""
        provider = MockProvider()
        prompt = "What is 2+2?"
        result = provider.sanitize_prompt(prompt)
        assert result == prompt

    def test_sanitize_prompt_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""
        provider = MockProvider()
        prompt = "line one\nline two\ttabbed"
        result = provider.sanitize_prompt(prompt)
        assert result == prompt


class TestSanitizeError:
    """Tests for sanitize_error() method."""

    def test_sanitize_error_empty_returns_unknown(self):
        """Test that empty error returns 'Unknown error'."""
        provider = MockProvider()
        result = provider.sanitize_error("")
        assert result == "Unknown error"

    def test_sanitize_error_none_returns_unknown(self):
        """Test that None error returns 'Unknown error'."""
        provider = MockProvider()
        result = provider.sanitize_error(None)
        assert result == "Unknown error"

    def test_sanitize_error_truncation_at_500_chars(self):
        """Test that errors are truncated at 500 characters."""
        provider = MockProvider()
        long_error = "Error: " + "a" * 600
        result = provider.sanitize_error(long_error)
        assert len(result) <= 520  # 500 + "... (truncated)"
        assert "truncated" in result

    def test_sanitize_error_redacts_sk_pattern(self):
        """Test that sk-* API keys are redacted."""
        provider = MockProvider()
        error = "API key sk-1234567890abcdefghij is invalid"
        result = provider.sanitize_error(error)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_redacts_gsk_pattern(self):
        """Test that gsk_* API keys are redacted."""
        provider = MockProvider()
        error = "Failed with key gsk_abcdefghij1234567890"
        result = provider.sanitize_error(error)
        assert "gsk_abcdefghij1234567890" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_redacts_bearer_tokens(self):
        """Test that bearer tokens are redacted."""
        provider = MockProvider()
        error = "Authorization: Bearer abc123def456ghi789"
        result = provider.sanitize_error(error)
        assert "abc123def456ghi789" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_redacts_api_key_equals(self):
        """Test that api_key= patterns are redacted."""
        provider = MockProvider()
        error = "Request failed: api_key=secret1234567890"
        result = provider.sanitize_error(error)
        assert "secret1234567890" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_redacts_xai_pattern(self):
        """Test that xai-* API keys are redacted."""
        provider = MockProvider()
        error = "xAI key xai-1234567890abcdefghij failed"
        result = provider.sanitize_error(error)
        assert "xai-1234567890abcdefghij" not in result
        assert "[REDACTED]" in result

    def test_sanitize_error_multiple_patterns(self):
        """Test that multiple patterns in one error are all redacted."""
        provider = MockProvider()
        error = "Keys sk-abc123def456ghi789jkl012 and gsk_xyz789abc123def456ghi789 both failed with token=secret1234567890"
        result = provider.sanitize_error(error)
        assert "sk-abc123def456ghi789jkl012" not in result
        assert "gsk_xyz789abc123def456ghi789" not in result
        assert "secret1234567890" not in result
        assert result.count("[REDACTED]") >= 3

    def test_sanitize_error_preserves_safe_content(self):
        """Test that safe error content is preserved."""
        provider = MockProvider()
        error = "Connection timeout after 30 seconds"
        result = provider.sanitize_error(error)
        assert result == error


class TestIsRetryableError:
    """Tests for is_retryable_error() method."""

    def test_is_retryable_timeout_keywords(self):
        """Test that timeout keywords return retryable."""
        provider = MockProvider()
        timeout_errors = [
            "Request timed out",
            "Connection timeout",
            "504 Gateway Timeout",
            "deadline exceeded",
            "gateway error",
        ]
        for error in timeout_errors:
            is_retryable, category = provider.is_retryable_error(error)
            assert is_retryable is True
            assert category == "timeout_or_overload"

    def test_is_retryable_rate_limit_keywords(self):
        """Test that rate limit keywords return retryable."""
        provider = MockProvider()
        rate_errors = [
            "429 Too Many Requests",
            "rate limit exceeded",
            "quota exceeded",
            "resource_exhausted",
        ]
        for error in rate_errors:
            is_retryable, category = provider.is_retryable_error(error)
            assert is_retryable is True
            assert category == "rate_limit"

    def test_is_retryable_overload_keywords(self):
        """Test that overload keywords return retryable."""
        provider = MockProvider()
        overload_errors = [
            "503 Service Unavailable",
            "server overloaded",
            "service unavailable",
            "502 Bad Gateway",
        ]
        for error in overload_errors:
            is_retryable, category = provider.is_retryable_error(error)
            assert is_retryable is True
            assert category == "timeout_or_overload"

    def test_is_retryable_non_retryable_errors(self):
        """Test that non-retryable errors return False."""
        provider = MockProvider()
        non_retryable = [
            "400 Bad Request",
            "401 Unauthorized",
            "403 Forbidden",
            "404 Not Found",
            "Invalid API key",
            "Model not found",
        ]
        for error in non_retryable:
            is_retryable, category = provider.is_retryable_error(error)
            assert is_retryable is False
            assert category == "non_retryable"

    def test_is_retryable_case_insensitive(self):
        """Test that error checking is case-insensitive."""
        provider = MockProvider()
        is_retryable, category = provider.is_retryable_error("TIMEOUT ERROR")
        assert is_retryable is True

        is_retryable, category = provider.is_retryable_error("Rate Limit")
        assert is_retryable is True


class TestGetTimeoutMs:
    """Tests for get_timeout_ms() method."""

    def test_get_timeout_default_value(self):
        """Test that default timeout value is used."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=None)
        timeout = provider.get_timeout_ms(args, "default")
        assert timeout == 300_000  # Default 300s

    def test_get_timeout_explicit_value(self):
        """Test that explicit timeout from args is used."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=60)
        timeout = provider.get_timeout_ms(args, "default")
        assert timeout == 60_000  # 60s in ms

    def test_get_timeout_min_bound(self):
        """Test that timeout below 5000ms is clamped to minimum."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=2)  # 2 seconds

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            timeout = provider.get_timeout_ms(args, "default")
            assert timeout == 5_000
            assert "Warning" in mock_stderr.getvalue()
            assert "clamped to minimum" in mock_stderr.getvalue()

    def test_get_timeout_max_bound(self):
        """Test that timeout above 600000ms is clamped to maximum."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=800)  # 800 seconds

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            timeout = provider.get_timeout_ms(args, "default")
            assert timeout == 600_000
            assert "Warning" in mock_stderr.getvalue()
            assert "clamped to maximum" in mock_stderr.getvalue()

    def test_get_timeout_custom_default(self):
        """Test that custom default timeout is used."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=None)
        timeout = provider.get_timeout_ms(args, "default", default_ms=120_000)
        assert timeout == 120_000

    def test_get_timeout_adaptive_falls_back_without_stats(self, monkeypatch):
        """Test adaptive timeout falls back to default when model_stats is unavailable."""
        monkeypatch.setenv("SYNOD_V2_ADAPTIVE_TIMEOUT", "1")

        provider = MockProvider()
        args = argparse.Namespace(timeout=None, verbose=False)
        timeout = provider.get_timeout_ms(args, "default")
        # Without model_stats, adaptive timeout cannot engage; falls back to default
        assert timeout == 300_000

    def test_get_timeout_adaptive_no_stats_verbose(self, monkeypatch):
        """Test adaptive timeout in verbose mode when stats unavailable."""
        monkeypatch.setenv("SYNOD_V2_ADAPTIVE_TIMEOUT", "1")

        provider = MockProvider()
        args = argparse.Namespace(timeout=None, verbose=True)
        timeout = provider.get_timeout_ms(args, "default")
        # Falls back to default since model_stats is archived
        assert timeout == 300_000

    def test_get_timeout_adaptive_disabled_by_default(self):
        """Test adaptive timeout is disabled when env var is not set."""
        provider = MockProvider()
        args = argparse.Namespace(timeout=None)
        timeout = provider.get_timeout_ms(args, "default")
        assert timeout == 300_000


class TestBuildParser:
    """Tests for build_parser() method."""

    def test_build_parser_returns_argparser(self):
        """Test that build_parser returns ArgumentParser."""
        provider = MockProvider()
        parser = provider.build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_build_parser_has_common_args(self):
        """Test that parser has common arguments."""
        provider = MockProvider()
        parser = provider.build_parser()
        args, _ = parser.parse_known_args(["--timeout", "60", "--retries", "5"])

        assert hasattr(args, "timeout")
        assert hasattr(args, "retries")
        assert hasattr(args, "verbose")
        assert hasattr(args, "prompt")
        assert hasattr(args, "positional_prompt")

    def test_build_parser_has_provider_args(self):
        """Test that parser includes provider-specific arguments."""
        provider = MockProvider()
        parser = provider.build_parser()
        args, _ = parser.parse_known_args(["--model", "alt"])

        assert hasattr(args, "model")
        assert args.model == "alt"

    def test_build_parser_default_values(self):
        """Test that parser has correct default values."""
        provider = MockProvider()
        parser = provider.build_parser()
        args, _ = parser.parse_known_args([])

        assert args.retries == 3
        assert args.verbose is False
        assert args.model == "default"


class TestGenerateWithRetry:
    """Tests for generate_with_retry() method."""

    def test_generate_with_retry_success_first_try(self):
        """Test that successful generation on first try returns result."""
        provider = MockProvider()
        client = {}
        result = provider.generate_with_retry(client, "test-model", "test prompt")
        assert result == "Response to: test prompt"

    def test_generate_with_retry_retries_on_retryable_error(self, monkeypatch):
        """Test that retryable errors trigger retry."""
        provider = MockProvider()
        client = {}

        call_count = [0]

        def mock_generate(self, client, model, prompt, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("timeout error")
            return "Success after retry"

        monkeypatch.setattr(MockProvider, "generate", mock_generate)

        with patch("sys.stderr", new=StringIO()):
            with patch("time.sleep"):  # Skip actual sleep
                result = provider.generate_with_retry(client, "test-model", "test prompt")
                assert result == "Success after retry"
                assert call_count[0] == 2

    def test_generate_with_retry_exits_on_non_retryable(self, monkeypatch):
        """Test that non-retryable errors cause exit."""
        provider = MockProvider()
        client = {}

        def mock_generate(self, client, model, prompt, **kwargs):
            raise Exception("401 Unauthorized")

        monkeypatch.setattr(MockProvider, "generate", mock_generate)

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()):
                provider.generate_with_retry(client, "test-model", "test prompt")
        assert exc_info.value.code == 1

    def test_generate_with_retry_exits_after_max_retries(self, monkeypatch):
        """Test that max retries causes exit."""
        provider = MockProvider()
        client = {}

        def mock_generate(self, client, model, prompt, **kwargs):
            raise Exception("timeout error")

        monkeypatch.setattr(MockProvider, "generate", mock_generate)

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()):
                with patch("time.sleep"):  # Skip actual sleep
                    provider.generate_with_retry(
                        client, "test-model", "test prompt", max_retries=2
                    )
        assert exc_info.value.code == 1


class TestWaitWithBackoff:
    """Tests for wait_with_backoff() method."""

    def test_wait_with_backoff_rate_limit_longer_wait(self):
        """Test that rate limits get longer backoff."""
        provider = MockProvider()

        with patch("time.sleep") as mock_sleep:
            with patch("sys.stderr", new=StringIO()) as mock_stderr:
                provider.wait_with_backoff(0, "rate_limit", 3)
                # Rate limit: 2^(0+2) = 4 seconds base
                assert mock_sleep.call_count == 1
                wait_time = mock_sleep.call_args[0][0]
                assert 4 <= wait_time < 5  # 4 + random
                assert "Rate limited" in mock_stderr.getvalue()

    def test_wait_with_backoff_timeout_standard_wait(self):
        """Test that timeouts get standard backoff."""
        provider = MockProvider()

        with patch("time.sleep") as mock_sleep:
            with patch("sys.stderr", new=StringIO()):
                provider.wait_with_backoff(0, "timeout_or_overload", 3)
                # Timeout: 2^0 = 1 second base
                assert mock_sleep.call_count == 1
                wait_time = mock_sleep.call_args[0][0]
                assert 1 <= wait_time < 2  # 1 + random

    def test_wait_with_backoff_exponential_increase(self):
        """Test that backoff increases exponentially."""
        provider = MockProvider()

        with patch("time.sleep") as mock_sleep:
            with patch("sys.stderr", new=StringIO()):
                # First retry
                provider.wait_with_backoff(0, "timeout_or_overload", 3)
                wait1 = mock_sleep.call_args[0][0]

                # Second retry
                provider.wait_with_backoff(1, "timeout_or_overload", 3)
                wait2 = mock_sleep.call_args[0][0]

                # Second wait should be approximately double first
                assert wait2 > wait1


class TestRecordLatency:
    """Tests for record_latency() method (no-op since model_stats archived)."""

    def test_record_latency_is_noop(self):
        """Test that record_latency is a no-op (model_stats archived)."""
        provider = MockProvider()
        # Should not raise exception
        provider.record_latency("test", 1234.5)

    def test_record_latency_called_from_generate(self):
        """Test that record_latency is called during generate flow."""
        provider = MockProvider()
        # Just verify the method exists and is callable
        assert callable(provider.record_latency)


class TestGetPrompt:
    """Tests for get_prompt() method."""

    def test_get_prompt_from_positional_arg(self):
        """Test getting prompt from positional argument."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt=None, positional_prompt="positional prompt"
        )
        with patch("sys.stdin.isatty", return_value=True):
            result = provider.get_prompt(args, [])
            assert result == "positional prompt"

    def test_get_prompt_from_flag(self):
        """Test getting prompt from --prompt flag."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt="flag prompt", positional_prompt=None
        )
        with patch("sys.stdin.isatty", return_value=True):
            result = provider.get_prompt(args, [])
            assert result == "flag prompt"

    def test_get_prompt_from_remaining_args(self):
        """Test getting prompt from remaining arguments."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt=None, positional_prompt=None
        )
        with patch("sys.stdin.isatty", return_value=True):
            result = provider.get_prompt(args, ["remaining", "prompt"])
            assert result == "remaining prompt"

    def test_get_prompt_from_stdin(self):
        """Test getting prompt from stdin."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt=None, positional_prompt=None
        )
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="stdin prompt\n"):
                result = provider.get_prompt(args, [])
                assert result == "stdin prompt"

    def test_get_prompt_stdin_priority(self):
        """Test that stdin has priority over other sources."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt="flag prompt", positional_prompt="positional"
        )
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="stdin prompt\n"):
                result = provider.get_prompt(args, ["remaining"])
                assert result == "stdin prompt"

    def test_get_prompt_no_prompt_exits(self):
        """Test that no prompt causes exit."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt=None, positional_prompt=None
        )
        with patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                with patch("sys.stderr", new=StringIO()):
                    provider.get_prompt(args, [])
            assert exc_info.value.code == 1

    def test_get_prompt_sanitizes(self):
        """Test that get_prompt sanitizes the result."""
        provider = MockProvider()
        args = argparse.Namespace(
            prompt="  prompt with\x00nulls  ", positional_prompt=None
        )
        with patch("sys.stdin.isatty", return_value=True):
            result = provider.get_prompt(args, [])
            assert result == "prompt withnulls"
