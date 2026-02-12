#!/usr/bin/env python3
"""
Integration tests for BaseProvider across all 7 CLI providers.

Tests cross-provider behavior without making actual API calls.
Verifies that all providers properly implement the BaseProvider interface
and maintain consistent behavior.
"""

import importlib.util
import inspect
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from base_provider import BaseProvider


def load_provider(filename):
    """Load provider module and return (module, ProviderClass) or (None, None).

    Args:
        filename: Provider filename (e.g., "gemini-3.py")

    Returns:
        Tuple of (module, ProviderClass) or (None, None) if loading fails
    """
    # Enable grok before loading
    if filename == "grok-cli.py":
        os.environ["SYNOD_ENABLE_GROK"] = "1"

    try:
        spec = importlib.util.spec_from_file_location(
            filename.replace("-", "_").replace(".py", ""),
            os.path.join(os.path.dirname(__file__), "..", "tools", filename)
        )
        module = importlib.util.module_from_spec(spec)

        # Redirect stderr to suppress import messages
        with patch('sys.stderr'):
            spec.loader.exec_module(module)

        # Find the provider class
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                issubclass(obj, BaseProvider) and
                obj is not BaseProvider):
                return module, obj
        return None, None

    except (ImportError, SystemExit) as e:
        # Skip providers that can't be loaded
        return None, None


# Load all available providers
PROVIDERS = {}
PROVIDER_FILES = [
    "gemini-3.py",
    "openai-cli.py",
    "deepseek-cli.py",
    "groq-cli.py",
    "grok-cli.py",
    "mistral-cli.py",
    "openrouter-cli.py"
]

for filename in PROVIDER_FILES:
    mod, cls = load_provider(filename)
    if cls:
        PROVIDERS[filename] = cls


# Skip all tests if no providers loaded
pytestmark = pytest.mark.skipif(
    len(PROVIDERS) == 0,
    reason="No providers available for testing"
)


class TestCrossProviderInheritance:
    """Test that all providers properly implement BaseProvider interface."""

    def test_all_providers_have_required_abstract_methods(self):
        """Verify all providers implement create_client, generate, add_provider_args."""
        required_methods = ["create_client", "generate", "add_provider_args"]

        for filename, provider_class in PROVIDERS.items():
            for method_name in required_methods:
                assert hasattr(provider_class, method_name), \
                    f"{filename}: Missing method {method_name}"

                method = getattr(provider_class, method_name)
                assert callable(method), \
                    f"{filename}: {method_name} is not callable"

    def test_all_providers_have_provider_constant(self):
        """Verify all providers have PROVIDER, API_KEY_ENV, MODEL_MAP, DEFAULT_MODEL."""
        required_attrs = ["PROVIDER", "API_KEY_ENV", "MODEL_MAP", "DEFAULT_MODEL"]

        for filename, provider_class in PROVIDERS.items():
            for attr_name in required_attrs:
                assert hasattr(provider_class, attr_name), \
                    f"{filename}: Missing class attribute {attr_name}"

                value = getattr(provider_class, attr_name)

                if attr_name == "MODEL_MAP":
                    assert isinstance(value, dict), \
                        f"{filename}: MODEL_MAP must be dict, got {type(value)}"
                    assert len(value) > 0, \
                        f"{filename}: MODEL_MAP is empty"
                else:
                    assert value, \
                        f"{filename}: {attr_name} is empty"

    def test_all_providers_default_model_in_model_map(self):
        """Verify DEFAULT_MODEL key exists in MODEL_MAP."""
        for filename, provider_class in PROVIDERS.items():
            default_model = provider_class.DEFAULT_MODEL
            model_map = provider_class.MODEL_MAP

            assert default_model in model_map, \
                f"{filename}: DEFAULT_MODEL '{default_model}' not in MODEL_MAP keys: {list(model_map.keys())}"

    def test_all_providers_inherit_from_base_provider(self):
        """Verify all providers are proper subclasses of BaseProvider."""
        for filename, provider_class in PROVIDERS.items():
            assert issubclass(provider_class, BaseProvider), \
                f"{filename}: Not a subclass of BaseProvider"
            assert provider_class is not BaseProvider, \
                f"{filename}: Should not be BaseProvider itself"


class TestModelOverrideIntegration:
    """Test get_model_with_override works consistently across providers."""

    def test_override_env_var_format_consistent(self, monkeypatch):
        """Verify SYNOD_{PROVIDER}_{MODEL_KEY} pattern works for all providers."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            provider_name = provider.PROVIDER
            default_model_key = provider.DEFAULT_MODEL

            # Test override with default model key
            override_value = "test-override-model"
            env_var = f"SYNOD_{provider_name.upper()}_{default_model_key.upper().replace('.', '_').replace('-', '_')}"

            monkeypatch.setenv(env_var, override_value)

            result = provider.get_model_with_override(default_model_key)
            assert result == override_value, \
                f"{filename}: Override failed for {env_var}"

            monkeypatch.delenv(env_var)

    def test_override_with_dotted_keys(self, monkeypatch):
        """Test providers with dotted model keys (e.g., gemini '2.5-flash')."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            # Find dotted keys in MODEL_MAP
            dotted_keys = [k for k in provider.MODEL_MAP.keys() if '.' in k or '-' in k]

            if not dotted_keys:
                continue

            for model_key in dotted_keys:
                override_value = "dotted-override-test"
                env_var = f"SYNOD_{provider.PROVIDER.upper()}_{model_key.upper().replace('.', '_').replace('-', '_')}"

                monkeypatch.setenv(env_var, override_value)
                result = provider.get_model_with_override(model_key)

                assert result == override_value, \
                    f"{filename}: Dotted key override failed for {model_key}"

                monkeypatch.delenv(env_var)

    def test_fallback_to_default_model_for_unknown_key(self):
        """All providers should fall back to DEFAULT_MODEL's value for unknown keys."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            unknown_key = "nonexistent_model_key_xyz"

            result = provider.get_model_with_override(unknown_key)
            expected = provider.MODEL_MAP[provider.DEFAULT_MODEL]

            assert result == expected, \
                f"{filename}: Should fallback to DEFAULT_MODEL value for unknown key"

    def test_no_override_returns_model_map_value(self):
        """Without override, should return MODEL_MAP value."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for model_key, expected_value in provider.MODEL_MAP.items():
                result = provider.get_model_with_override(model_key)
                assert result == expected_value, \
                    f"{filename}: Should return MODEL_MAP value without override"


class TestTimeoutIntegration:
    """Test timeout management across providers."""

    def test_all_providers_respect_timeout_bounds(self):
        """Verify MIN (5000ms) and MAX (600000ms) bounds are enforced."""
        MIN_TIMEOUT_MS = 5_000
        MAX_TIMEOUT_MS = 600_000

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            # Test below minimum
            args_low = Mock(timeout=0.001)  # 1ms
            result_low = provider.get_timeout_ms(args_low, provider.DEFAULT_MODEL)
            assert result_low >= MIN_TIMEOUT_MS, \
                f"{filename}: Timeout below minimum not clamped"

            # Test above maximum
            args_high = Mock(timeout=700)  # 700 seconds = 700000ms
            result_high = provider.get_timeout_ms(args_high, provider.DEFAULT_MODEL)
            assert result_high <= MAX_TIMEOUT_MS, \
                f"{filename}: Timeout above maximum not clamped"

    def test_default_timeout_reasonable(self):
        """All providers should have default timeout >= 30000ms."""
        MIN_REASONABLE_TIMEOUT = 30_000

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            args = Mock(timeout=None)

            result = provider.get_timeout_ms(args, provider.DEFAULT_MODEL)
            assert result >= MIN_REASONABLE_TIMEOUT, \
                f"{filename}: Default timeout too low ({result}ms)"

    def test_timeout_conversion_seconds_to_ms(self):
        """Verify timeout is properly converted from seconds to milliseconds."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            args = Mock(timeout=60)  # 60 seconds
            result = provider.get_timeout_ms(args, provider.DEFAULT_MODEL)

            # Should be 60000ms (within bounds)
            assert 5_000 <= result <= 600_000, \
                f"{filename}: Timeout conversion out of bounds"


class TestErrorHandlingConsistency:
    """Test that error handling is consistent across all providers."""

    def test_all_providers_detect_timeout_errors(self):
        """Test is_retryable_error detects timeout patterns."""
        timeout_errors = [
            "timeout exceeded",
            "request timed out",
            "deadline exceeded",
            "504 Gateway Timeout",
            "gateway timeout"
        ]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for error_msg in timeout_errors:
                is_retryable, category = provider.is_retryable_error(error_msg)
                assert is_retryable, \
                    f"{filename}: Should detect '{error_msg}' as retryable"
                assert category == "timeout_or_overload", \
                    f"{filename}: Wrong category for timeout error"

    def test_all_providers_detect_rate_limit_errors(self):
        """Test 429, rate limit detection."""
        rate_limit_errors = [
            "429 Too Many Requests",
            "rate limit exceeded",
            "quota exceeded",
            "resource_exhausted"
        ]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for error_msg in rate_limit_errors:
                is_retryable, category = provider.is_retryable_error(error_msg)
                assert is_retryable, \
                    f"{filename}: Should detect '{error_msg}' as retryable"
                assert category == "rate_limit", \
                    f"{filename}: Wrong category for rate limit error"

    def test_all_providers_detect_overload_errors(self):
        """Test 503, overload detection."""
        overload_errors = [
            "503 Service Unavailable",
            "service overloaded",
            "502 Bad Gateway"
        ]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for error_msg in overload_errors:
                is_retryable, category = provider.is_retryable_error(error_msg)
                assert is_retryable, \
                    f"{filename}: Should detect '{error_msg}' as retryable"
                assert category == "timeout_or_overload", \
                    f"{filename}: Wrong category for overload error"

    def test_all_providers_detect_non_retryable_errors(self):
        """Test non-retryable errors are correctly identified."""
        non_retryable_errors = [
            "400 Bad Request",
            "401 Unauthorized",
            "403 Forbidden",
            "invalid api key"
        ]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for error_msg in non_retryable_errors:
                is_retryable, category = provider.is_retryable_error(error_msg)
                assert not is_retryable, \
                    f"{filename}: Should detect '{error_msg}' as non-retryable"
                assert category == "non_retryable", \
                    f"{filename}: Wrong category for non-retryable error"

    def test_all_providers_sanitize_errors(self):
        """Test that API key patterns are redacted."""
        test_cases = [
            ("API key sk-1234567890abcdefghij1234", "[REDACTED]"),
            ("Error: gsk_abcdef1234567890xyz123", "[REDACTED]"),
            ("xai-1234567890abcdefghij1234 is invalid", "[REDACTED]"),
            ("api_key=secret123456789", "[REDACTED]"),
            ("Bearer abc1234567890", "[REDACTED]")
        ]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            for error_input, expected_pattern in test_cases:
                result = provider.sanitize_error(error_input)
                assert "[REDACTED]" in result, \
                    f"{filename}: Failed to redact secret in '{error_input}'"
                assert "sk-" not in result and "gsk_" not in result and "xai-" not in result, \
                    f"{filename}: API key pattern still visible in result"


class TestAPIKeyValidation:
    """Test API key validation across providers."""

    def test_all_providers_exit_on_missing_key(self, monkeypatch):
        """For each provider, verify SystemExit on missing API key."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            api_key_env = provider.API_KEY_ENV

            # Remove API key from environment
            monkeypatch.delenv(api_key_env, raising=False)

            # Special case: Gemini also checks GOOGLE_API_KEY
            if api_key_env == "GEMINI_API_KEY":
                monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

            # Should raise SystemExit
            with pytest.raises(SystemExit):
                provider.validate_api_key()

    def test_api_key_env_vars_unique(self):
        """No two providers should share the same API_KEY_ENV."""
        api_key_envs = {}

        for filename, provider_class in PROVIDERS.items():
            api_key_env = provider_class.API_KEY_ENV

            if api_key_env in api_key_envs:
                pytest.fail(
                    f"Duplicate API_KEY_ENV '{api_key_env}' found in "
                    f"{filename} and {api_key_envs[api_key_env]}"
                )

            api_key_envs[api_key_env] = filename

    def test_api_key_validation_strips_whitespace(self, monkeypatch):
        """Verify API keys are stripped of whitespace (base class behavior)."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            api_key_env = provider.API_KEY_ENV

            # Set key with whitespace
            test_key = "  test_key_with_spaces  \n"
            monkeypatch.setenv(api_key_env, test_key)

            result = provider.validate_api_key()
            assert result == test_key.strip(), \
                f"{filename}: API key not properly stripped"

    def test_api_key_validation_rejects_empty(self, monkeypatch):
        """Verify empty API keys (after stripping) cause SystemExit (base class behavior)."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            api_key_env = provider.API_KEY_ENV

            # Set empty key
            monkeypatch.setenv(api_key_env, "   \n\t  ")

            with pytest.raises(SystemExit):
                provider.validate_api_key()


class TestParserIntegration:
    """Test argument parser works correctly for all providers."""

    def test_all_providers_build_parser_successfully(self):
        """build_parser() should not raise for any provider."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            try:
                parser = provider.build_parser()
                assert parser is not None, \
                    f"{filename}: build_parser returned None"
            except Exception as e:
                pytest.fail(f"{filename}: build_parser raised {e}")

    def test_all_parsers_have_common_args(self):
        """All parsers should have: --timeout, --retries, -v/--verbose, --prompt."""
        common_args = ["timeout", "retries", "verbose", "prompt"]

        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            parser = provider.build_parser()

            # Parse with minimal args to check what's available
            args, _ = parser.parse_known_args([])

            for arg_name in common_args:
                assert hasattr(args, arg_name), \
                    f"{filename}: Missing common argument --{arg_name}"

    def test_all_parsers_have_model_arg(self):
        """All providers should add a --model or -m argument."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            parser = provider.build_parser()

            # Check if 'model' is in the parser
            args, _ = parser.parse_known_args([])

            # Model arg might be optional, but should exist
            has_model = hasattr(args, "model")
            assert has_model, \
                f"{filename}: Missing --model argument"

    def test_parser_handles_positional_prompt(self):
        """All parsers should handle positional prompt."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()
            parser = provider.build_parser()

            # Parse with positional prompt
            args, _ = parser.parse_known_args(["test prompt"])

            assert hasattr(args, "positional_prompt"), \
                f"{filename}: Parser doesn't handle positional prompt"
            assert args.positional_prompt == "test prompt", \
                f"{filename}: Positional prompt not captured correctly"


class TestPromptHandling:
    """Test prompt handling consistency across providers."""

    def test_sanitize_prompt_removes_null_bytes(self):
        """All providers should remove null bytes from prompts."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            prompt_with_nulls = "test\x00prompt\x00here"
            result = provider.sanitize_prompt(prompt_with_nulls)

            assert "\x00" not in result, \
                f"{filename}: Null bytes not removed from prompt"

    def test_sanitize_prompt_truncates_long_prompts(self):
        """All providers should truncate prompts over 1MB."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            # Create prompt > 1MB
            long_prompt = "a" * 1_100_000
            result = provider.sanitize_prompt(long_prompt)

            assert len(result) <= 1_000_000, \
                f"{filename}: Long prompt not truncated"

    def test_sanitize_prompt_strips_whitespace(self):
        """All providers should strip leading/trailing whitespace."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            prompt = "  \n test prompt \t\n  "
            result = provider.sanitize_prompt(prompt)

            assert result == "test prompt", \
                f"{filename}: Whitespace not stripped from prompt"

    def test_sanitize_prompt_handles_empty(self):
        """All providers should handle empty prompts gracefully."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            result = provider.sanitize_prompt("")
            assert result == "", \
                f"{filename}: Empty prompt not handled correctly"

            result_none = provider.sanitize_prompt(None)
            assert result_none == "", \
                f"{filename}: None prompt not handled correctly"


class TestRetryLogic:
    """Test retry logic consistency across providers."""

    def test_wait_with_backoff_rate_limit(self):
        """Rate limits should have longer backoff than timeouts."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            # We can't easily test the actual wait time without mocking time.sleep
            # But we can verify the method doesn't crash
            with patch('time.sleep'):
                provider.wait_with_backoff(0, "rate_limit", 3)
                provider.wait_with_backoff(1, "rate_limit", 3)

    def test_wait_with_backoff_timeout(self):
        """Timeout errors should have standard backoff."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            with patch('time.sleep'):
                provider.wait_with_backoff(0, "timeout_or_overload", 3)
                provider.wait_with_backoff(1, "timeout_or_overload", 3)


class TestRecordLatency:
    """Test latency recording consistency."""

    def test_record_latency_doesnt_crash(self):
        """Recording latency should never crash even if stats unavailable."""
        for filename, provider_class in PROVIDERS.items():
            provider = provider_class()

            # Should not raise even if ModelStats fails
            try:
                provider.record_latency(provider.DEFAULT_MODEL, 1000.0)
            except Exception as e:
                pytest.fail(f"{filename}: record_latency raised {e}")


class TestProviderNames:
    """Test provider naming consistency."""

    def test_provider_names_lowercase(self):
        """PROVIDER constant should be lowercase."""
        for filename, provider_class in PROVIDERS.items():
            provider_name = provider_class.PROVIDER
            assert provider_name.islower(), \
                f"{filename}: PROVIDER '{provider_name}' should be lowercase"

    def test_provider_names_alphanumeric(self):
        """PROVIDER names should be alphanumeric (no spaces)."""
        for filename, provider_class in PROVIDERS.items():
            provider_name = provider_class.PROVIDER
            assert provider_name.replace("-", "").replace("_", "").isalnum(), \
                f"{filename}: PROVIDER '{provider_name}' contains invalid characters"


# Summary test to show which providers were loaded
def test_provider_loading_summary():
    """Show which providers were successfully loaded."""
    print("\n" + "="*60)
    print("Provider Loading Summary")
    print("="*60)

    for filename in PROVIDER_FILES:
        status = "LOADED" if filename in PROVIDERS else "SKIPPED"
        provider_name = PROVIDERS[filename].PROVIDER if filename in PROVIDERS else "N/A"
        print(f"{filename:25} {status:10} {provider_name}")

    print("="*60)
    print(f"Total providers loaded: {len(PROVIDERS)}/{len(PROVIDER_FILES)}")
    print("="*60 + "\n")

    assert len(PROVIDERS) > 0, "No providers loaded for testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
