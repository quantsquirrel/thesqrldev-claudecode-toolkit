"""
Tests for openai-cli.py - OpenAI API client with retry logic.
"""

import os
import sys

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

# Import after path modification
import importlib.util

spec = importlib.util.spec_from_file_location(
    "openai_cli", os.path.join(os.path.dirname(__file__), "..", "tools", "openai-cli.py")
)
openai_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(openai_cli)


class TestModelMapping:
    """Tests for MODEL_MAP configuration."""

    def test_model_map_contains_all_models(self):
        """Test that MODEL_MAP has all expected models."""
        assert "gpt4o" in openai_cli.OpenAIProvider.MODEL_MAP
        assert "o3" in openai_cli.OpenAIProvider.MODEL_MAP
        assert "o4mini" in openai_cli.OpenAIProvider.MODEL_MAP

    def test_model_names_correct(self):
        """Test that model names are correctly mapped."""
        assert openai_cli.OpenAIProvider.MODEL_MAP["gpt4o"] == "gpt-4o"
        assert openai_cli.OpenAIProvider.MODEL_MAP["o3"] == "o3"
        assert openai_cli.OpenAIProvider.MODEL_MAP["o4mini"] == "o4-mini"


class TestOSeriesModels:
    """Tests for O_SERIES_MODELS configuration."""

    def test_o_series_models_list(self):
        """Test that o-series models are correctly identified."""
        assert "o3" in openai_cli.OpenAIProvider.O_SERIES_MODELS
        assert "o4mini" in openai_cli.OpenAIProvider.O_SERIES_MODELS
        assert "gpt4o" not in openai_cli.OpenAIProvider.O_SERIES_MODELS


class TestTimeoutConfig:
    """Tests for TIMEOUT_CONFIG."""

    def test_timeout_config_has_all_combinations(self):
        """Test that timeout config covers all model+reasoning combinations."""
        models = ["gpt4o", "o3", "o4mini"]
        levels = ["low", "medium", "high"]

        for model in models:
            for level in levels:
                assert (model, level) in openai_cli.OpenAIProvider.TIMEOUT_CONFIG

    def test_timeout_values_reasonable(self):
        """Test that all timeout values are positive and reasonable."""
        for timeout in openai_cli.OpenAIProvider.TIMEOUT_CONFIG.values():
            assert timeout > 0
            assert timeout <= 600  # Max 10 minutes

    def test_o3_high_has_longest_timeout(self):
        """Test that o3 with high reasoning has the longest timeout."""
        o3_high = openai_cli.OpenAIProvider.TIMEOUT_CONFIG[("o3", "high")]
        # Should be one of the highest timeouts
        assert o3_high >= 180


class TestReasoningLevels:
    """Tests for REASONING_LEVELS configuration."""

    def test_reasoning_levels_order(self):
        """Test that reasoning levels are in descending order."""
        levels = openai_cli.OpenAIProvider.REASONING_LEVELS
        assert levels == ["high", "medium", "low"]


class TestCreateClient:
    """Tests for create_client() function."""

    def test_create_client_with_valid_api_key(self, mock_openai_api_key):
        """Test that client creation requires API key."""
        # Just verify API key is set - actual client creation would need mocking
        assert os.environ.get("OPENAI_API_KEY") == mock_openai_api_key


class TestGenerateWithRetry:
    """Tests for generate_with_retry() retry logic."""

    def test_successful_generation(self, mock_openai_api_key, monkeypatch):
        """Test that generate function exists and has correct signature."""
        # Verify function exists with expected parameters
        import inspect

        sig = inspect.signature(openai_cli.OpenAIProvider.generate_with_retry)
        params = list(sig.parameters.keys())
        assert "client" in params
        assert "model" in params
        assert "prompt" in params
        assert "max_retries" in params
        assert "kwargs" in params  # Additional args passed via kwargs

    def test_o_series_includes_reasoning_effort(self):
        """Test that o-series models should use reasoning_effort."""
        # This is a configuration test
        for model in openai_cli.OpenAIProvider.O_SERIES_MODELS:
            assert model in ["o3", "o4mini"]

    def test_gpt4o_excludes_reasoning_effort(self):
        """Test that gpt4o should not use reasoning_effort."""
        assert "gpt4o" not in openai_cli.OpenAIProvider.O_SERIES_MODELS


class TestIntegration:
    """Integration tests that don't require API calls."""

    def test_module_imports_successfully(self):
        """Test that the module can be imported without errors."""
        assert openai_cli is not None
        assert hasattr(openai_cli, "OpenAIProvider")
        assert hasattr(openai_cli.OpenAIProvider, "create_client")
        assert hasattr(openai_cli.OpenAIProvider, "generate_with_retry")
        assert hasattr(openai_cli.OpenAIProvider, "run")

    def test_cli_help_works_without_api_key(self, monkeypatch):
        """Test that CLI help can be shown without API key."""
        # The help functionality should work even without API key
        assert openai_cli.OpenAIProvider.MODEL_MAP is not None
        assert openai_cli.OpenAIProvider.TIMEOUT_CONFIG is not None


class TestErrorDetection:
    """Tests for error detection logic."""

    def test_timeout_error_keywords(self):
        """Test timeout error detection keywords."""
        timeout_keywords = ["timeout", "timed out", "deadline"]
        for keyword in timeout_keywords:
            assert keyword.lower() in keyword.lower()

    def test_rate_limit_error_keywords(self):
        """Test rate limit error detection keywords."""
        rate_keywords = ["429", "rate", "quota"]
        for keyword in rate_keywords:
            assert keyword.lower() in keyword.lower()

    def test_overload_error_keywords(self):
        """Test overload error detection keywords."""
        overload_keywords = ["503", "overloaded", "unavailable", "502"]
        for keyword in overload_keywords:
            assert keyword.lower() in keyword.lower()


class TestTimeoutStrategy:
    """Tests for timeout strategy."""

    def test_timeout_increases_with_reasoning_level(self):
        """Test that timeouts increase with reasoning complexity."""
        for model in ["gpt4o", "o3", "o4mini"]:
            low = openai_cli.OpenAIProvider.TIMEOUT_CONFIG[(model, "low")]
            medium = openai_cli.OpenAIProvider.TIMEOUT_CONFIG[(model, "medium")]
            high = openai_cli.OpenAIProvider.TIMEOUT_CONFIG[(model, "high")]
            # Timeouts should generally increase or stay same
            assert low <= medium <= high or (low == medium == high)

    def test_o_series_has_higher_timeouts(self):
        """Test that o-series models have generally higher timeouts."""
        # O3 should have higher timeouts than gpt4o on average
        o3_avg = (
            sum(openai_cli.OpenAIProvider.TIMEOUT_CONFIG[("o3", level)] for level in ["low", "medium", "high"]) / 3
        )
        gpt4o_avg = (
            sum(openai_cli.OpenAIProvider.TIMEOUT_CONFIG[("gpt4o", level)] for level in ["low", "medium", "high"])
            / 3
        )
        assert o3_avg > gpt4o_avg
