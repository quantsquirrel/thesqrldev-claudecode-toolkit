#!/usr/bin/env python3
"""Quick test of security features in BaseProvider."""

import sys
import os

# Add tools directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_provider import BaseProvider
import argparse


class TestProvider(BaseProvider):
    """Test implementation of BaseProvider."""

    PROVIDER = "test"
    API_KEY_ENV = "TEST_API_KEY"
    MODEL_MAP = {"default": "test-model"}
    DEFAULT_MODEL = "default"

    def create_client(self, timeout_ms: int):
        return None

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        return "test response"

    def add_provider_args(self, parser: argparse.ArgumentParser):
        pass


def test_sanitize_prompt():
    """Test prompt sanitization."""
    print("Testing sanitize_prompt()...")
    provider = TestProvider()

    # Test 1: Strip whitespace
    assert provider.sanitize_prompt("  hello  ") == "hello"
    print("  ✓ Strips whitespace")

    # Test 2: Remove null bytes
    assert provider.sanitize_prompt("hello\x00world") == "helloworld"
    print("  ✓ Removes null bytes")

    # Test 3: Empty input
    assert provider.sanitize_prompt("") == ""
    assert provider.sanitize_prompt(None) == ""
    print("  ✓ Handles empty input")

    # Test 4: Long prompt (would trigger warning in real use)
    long_prompt = "a" * 2_000_000
    result = provider.sanitize_prompt(long_prompt)
    assert len(result) == 1_000_000
    print("  ✓ Truncates long prompts")

    print("✓ All prompt sanitization tests passed!\n")


def test_sanitize_error():
    """Test error sanitization."""
    print("Testing sanitize_error()...")
    provider = TestProvider()

    # Test 1: Remove OpenAI-style keys
    error = "API error with key sk-1234567890abcdefghij1234567890"
    result = provider.sanitize_error(error)
    assert "sk-" not in result
    assert "[REDACTED]" in result
    print("  ✓ Removes sk-* keys")

    # Test 2: Remove Google-style keys
    error = "Authentication failed: gsk_abcdefghijklmnopqrstuvwxyz1234567890"
    result = provider.sanitize_error(error)
    assert "gsk_" not in result
    assert "[REDACTED]" in result
    print("  ✓ Removes gsk_* keys")

    # Test 3: Remove xAI-style keys
    error = "Invalid token xai-abcdefghijklmnopqrstuvwxyz"
    result = provider.sanitize_error(error)
    assert "xai-" not in result
    assert "[REDACTED]" in result
    print("  ✓ Removes xai-* keys")

    # Test 4: Truncate long errors
    long_error = "Error: " + ("x" * 600)
    result = provider.sanitize_error(long_error)
    assert len(result) <= 520  # 500 + "... (truncated)"
    print("  ✓ Truncates long errors")

    # Test 5: Handle None/empty
    assert provider.sanitize_error("") == "Unknown error"
    assert provider.sanitize_error(None) == "Unknown error"
    print("  ✓ Handles empty errors")

    print("✓ All error sanitization tests passed!\n")


def test_timeout_bounds():
    """Test timeout bounds checking."""
    print("Testing timeout bounds...")
    provider = TestProvider()

    # Mock args object
    class Args:
        timeout = None
        verbose = False

    args = Args()

    # Test 1: Normal timeout
    timeout = provider.get_timeout_ms(args, "default", default_ms=30_000)
    assert 5_000 <= timeout <= 600_000
    print("  ✓ Normal timeout within bounds")

    # Test 2: Too low (would be clamped)
    args.timeout = 2  # 2 seconds = 2000ms
    timeout = provider.get_timeout_ms(args, "default")
    assert timeout == 5_000
    print("  ✓ Clamps low timeout to minimum")

    # Test 3: Too high (would be clamped)
    args.timeout = 1000  # 1000 seconds = 1,000,000ms
    timeout = provider.get_timeout_ms(args, "default")
    assert timeout == 600_000
    print("  ✓ Clamps high timeout to maximum")

    print("✓ All timeout bounds tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Security Features Test Suite")
    print("=" * 60 + "\n")

    test_sanitize_prompt()
    test_sanitize_error()
    test_timeout_bounds()

    print("=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
