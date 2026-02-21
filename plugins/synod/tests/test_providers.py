"""
Tests for provider-specific CLI configurations and class attributes.

Tests provider class attributes WITHOUT requiring SDK imports by using
importlib to load modules and handling ImportError gracefully.
"""

import importlib.util
import os
import sys

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from base_provider import BaseProvider


def try_load_provider(filename):
    """Load a provider module, returning (module, provider_class) or (None, None) on import error.

    Args:
        filename: Name of the provider file (e.g., "deepseek-cli.py")

    Returns:
        Tuple of (module, provider_class) or (None, None) if import fails
    """
    try:
        tools_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
        filepath = os.path.join(tools_dir, filename)

        # Check providers/extended/ if not found in tools/
        if not os.path.exists(filepath):
            filepath = os.path.join(tools_dir, "providers", "extended", filename)

        spec = importlib.util.spec_from_file_location(filename, filepath)
        if spec is None or spec.loader is None:
            return None, None

        module = importlib.util.module_from_spec(spec)

        # Execute module
        spec.loader.exec_module(module)

        # Find the Provider class (subclass of BaseProvider, but not BaseProvider itself)
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseProvider)
                and obj is not BaseProvider
            ):
                return module, obj

        return module, None
    except (ImportError, SystemExit) as e:
        # SystemExit can happen if enable gate fails (grok, mistral)
        return None, None


class TestGeminiProvider:
    """Tests for Gemini provider configuration."""

    @pytest.fixture
    def provider_class(self):
        """Load Gemini provider class."""
        _, provider = try_load_provider("gemini-3.py")
        if provider is None:
            pytest.skip("google-genai package not installed or module load failed")
        return provider

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "gemini"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "GEMINI_API_KEY"

    def test_model_map_has_required_models(self, provider_class):
        """Test MODEL_MAP contains expected models."""
        assert "flash" in provider_class.MODEL_MAP
        assert "pro" in provider_class.MODEL_MAP
        assert "2.5-flash" in provider_class.MODEL_MAP
        assert "2.5-pro" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "flash"

    def test_thinking_map_exists(self, provider_class):
        """Test THINKING_MAP attribute exists."""
        assert hasattr(provider_class, "THINKING_MAP")
        assert "minimal" in provider_class.THINKING_MAP
        assert "low" in provider_class.THINKING_MAP
        assert "medium" in provider_class.THINKING_MAP
        assert "high" in provider_class.THINKING_MAP

    def test_retry_levels_exists(self, provider_class):
        """Test RETRY_LEVELS attribute exists."""
        assert hasattr(provider_class, "RETRY_LEVELS")
        assert isinstance(provider_class.RETRY_LEVELS, list)


class TestOpenAIProvider:
    """Tests for OpenAI provider configuration."""

    @pytest.fixture
    def provider_class(self):
        """Load OpenAI provider class."""
        _, provider = try_load_provider("openai-cli.py")
        if provider is None:
            pytest.skip("openai package not installed or module load failed")
        return provider

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "openai"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "OPENAI_API_KEY"

    def test_model_map_has_required_models(self, provider_class):
        """Test MODEL_MAP contains expected models."""
        assert "gpt4o" in provider_class.MODEL_MAP
        assert "o3" in provider_class.MODEL_MAP
        assert "o4mini" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "gpt4o"

    def test_o_series_models_list(self, provider_class):
        """Test O_SERIES_MODELS attribute exists."""
        assert hasattr(provider_class, "O_SERIES_MODELS")
        assert "o3" in provider_class.O_SERIES_MODELS
        assert "o4mini" in provider_class.O_SERIES_MODELS

    def test_timeout_config_exists(self, provider_class):
        """Test TIMEOUT_CONFIG attribute exists."""
        assert hasattr(provider_class, "TIMEOUT_CONFIG")
        assert isinstance(provider_class.TIMEOUT_CONFIG, dict)

    def test_reasoning_levels_exists(self, provider_class):
        """Test REASONING_LEVELS attribute exists."""
        assert hasattr(provider_class, "REASONING_LEVELS")
        assert provider_class.REASONING_LEVELS == ["high", "medium", "low"]


class TestDeepSeekProvider:
    """Tests for DeepSeek provider configuration."""

    @pytest.fixture
    def provider_class(self):
        """Load DeepSeek provider class."""
        _, provider = try_load_provider("deepseek-cli.py")
        if provider is None:
            pytest.skip("openai package not installed or module load failed")
        return provider

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "deepseek"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "DEEPSEEK_API_KEY"

    def test_model_map_has_chat_and_reasoner(self, provider_class):
        """Test MODEL_MAP contains chat and reasoner models."""
        assert "chat" in provider_class.MODEL_MAP
        assert "reasoner" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "chat"

    def test_reasoner_models_list(self, provider_class):
        """Test REASONER_MODELS attribute exists."""
        assert hasattr(provider_class, "REASONER_MODELS")
        assert "reasoner" in provider_class.REASONER_MODELS

    def test_timeout_config_exists(self, provider_class):
        """Test TIMEOUT_CONFIG attribute exists."""
        assert hasattr(provider_class, "TIMEOUT_CONFIG")
        assert isinstance(provider_class.TIMEOUT_CONFIG, dict)

    def test_reasoning_levels_exists(self, provider_class):
        """Test REASONING_LEVELS attribute exists."""
        assert hasattr(provider_class, "REASONING_LEVELS")
        assert provider_class.REASONING_LEVELS == ["high", "medium", "low"]


class TestGroqProvider:
    """Tests for Groq provider configuration."""

    @pytest.fixture
    def provider_class(self):
        """Load Groq provider class."""
        _, provider = try_load_provider("groq-cli.py")
        if provider is None:
            pytest.skip("openai package not installed or module load failed")
        return provider

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "groq"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "GROQ_API_KEY"

    def test_model_map_has_required_models(self, provider_class):
        """Test MODEL_MAP contains expected models."""
        assert "8b" in provider_class.MODEL_MAP
        assert "70b" in provider_class.MODEL_MAP
        assert "mixtral" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "8b"

    def test_timeout_config_exists(self, provider_class):
        """Test TIMEOUT_CONFIG attribute exists."""
        assert hasattr(provider_class, "TIMEOUT_CONFIG")
        assert isinstance(provider_class.TIMEOUT_CONFIG, dict)

    def test_model_map_values_are_llama_or_mixtral(self, provider_class):
        """Test that model values point to llama or mixtral models."""
        for model_name in provider_class.MODEL_MAP.values():
            assert "llama" in model_name.lower() or "mixtral" in model_name.lower()


class TestGrokProvider:
    """Tests for Grok (xAI) provider configuration.

    Note: Requires SYNOD_ENABLE_GROK=1 environment variable.
    """

    @pytest.fixture
    def provider_class(self):
        """Load Grok provider class with enable gate."""
        # Set enable gate before import
        original_value = os.environ.get("SYNOD_ENABLE_GROK")
        os.environ["SYNOD_ENABLE_GROK"] = "1"

        try:
            _, provider = try_load_provider("grok-cli.py")
            if provider is None:
                pytest.skip("openai package not installed or module load failed")
            return provider
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("SYNOD_ENABLE_GROK", None)
            else:
                os.environ["SYNOD_ENABLE_GROK"] = original_value

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "grok"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "XAI_API_KEY"

    def test_model_map_has_required_models(self, provider_class):
        """Test MODEL_MAP contains expected models."""
        assert "fast" in provider_class.MODEL_MAP
        assert "grok4" in provider_class.MODEL_MAP
        assert "mini" in provider_class.MODEL_MAP
        assert "vision" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "fast"

    def test_timeout_config_exists(self, provider_class):
        """Test TIMEOUT_CONFIG attribute exists."""
        assert hasattr(provider_class, "TIMEOUT_CONFIG")
        assert isinstance(provider_class.TIMEOUT_CONFIG, dict)

    def test_model_map_values_are_grok_models(self, provider_class):
        """Test that model values point to grok models."""
        for model_name in provider_class.MODEL_MAP.values():
            assert "grok" in model_name.lower()

    def test_enable_gate_blocks_without_env(self):
        """Test that module exits if SYNOD_ENABLE_GROK is not set."""
        # Ensure env var is not set
        original_value = os.environ.get("SYNOD_ENABLE_GROK")
        os.environ.pop("SYNOD_ENABLE_GROK", None)

        try:
            _, provider = try_load_provider("grok-cli.py")
            # Should return None due to SystemExit(2)
            assert provider is None
        finally:
            if original_value is not None:
                os.environ["SYNOD_ENABLE_GROK"] = original_value


class TestMistralProvider:
    """Tests for Mistral provider configuration.

    Note: Requires SYNOD_ENABLE_MISTRAL=1 environment variable.
    """

    @pytest.fixture
    def provider_class(self):
        """Load Mistral provider class with enable gate."""
        # Set enable gate before import
        original_value = os.environ.get("SYNOD_ENABLE_MISTRAL")
        os.environ["SYNOD_ENABLE_MISTRAL"] = "1"

        try:
            _, provider = try_load_provider("mistral-cli.py")
            if provider is None:
                pytest.skip("mistralai package not installed or module load failed")
            return provider
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("SYNOD_ENABLE_MISTRAL", None)
            else:
                os.environ["SYNOD_ENABLE_MISTRAL"] = original_value

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "mistral"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "MISTRAL_API_KEY"

    def test_model_map_has_required_models(self, provider_class):
        """Test MODEL_MAP contains expected models."""
        assert "large" in provider_class.MODEL_MAP
        assert "medium" in provider_class.MODEL_MAP
        assert "small" in provider_class.MODEL_MAP
        assert "codestral" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "medium"

    def test_default_timeout_exists(self, provider_class):
        """Test DEFAULT_TIMEOUT attribute exists."""
        assert hasattr(provider_class, "DEFAULT_TIMEOUT")
        assert isinstance(provider_class.DEFAULT_TIMEOUT, dict)

    def test_model_map_values_are_mistral_models(self, provider_class):
        """Test that model values point to mistral models."""
        for model_name in provider_class.MODEL_MAP.values():
            assert "mistral" in model_name.lower() or "codestral" in model_name.lower() or "devstral" in model_name.lower()

    def test_enable_gate_blocks_without_env(self):
        """Test that module exits if SYNOD_ENABLE_MISTRAL is not set."""
        # Ensure env var is not set
        original_value = os.environ.get("SYNOD_ENABLE_MISTRAL")
        os.environ.pop("SYNOD_ENABLE_MISTRAL", None)

        try:
            _, provider = try_load_provider("mistral-cli.py")
            # Should return None due to SystemExit(2)
            assert provider is None
        finally:
            if original_value is not None:
                os.environ["SYNOD_ENABLE_MISTRAL"] = original_value


class TestOpenRouterProvider:
    """Tests for OpenRouter provider configuration."""

    @pytest.fixture
    def provider_class(self):
        """Load OpenRouter provider class."""
        _, provider = try_load_provider("openrouter-cli.py")
        if provider is None:
            pytest.skip("openai package not installed or module load failed")
        return provider

    def test_provider_name(self, provider_class):
        """Test PROVIDER attribute is set correctly."""
        assert provider_class.PROVIDER == "openrouter"

    def test_api_key_env(self, provider_class):
        """Test API_KEY_ENV attribute is set correctly."""
        assert provider_class.API_KEY_ENV == "OPENROUTER_API_KEY"

    def test_model_map_has_multiple_providers(self, provider_class):
        """Test MODEL_MAP contains models from multiple providers."""
        assert "claude" in provider_class.MODEL_MAP
        assert "gemini" in provider_class.MODEL_MAP
        assert "llama" in provider_class.MODEL_MAP
        assert "mistral" in provider_class.MODEL_MAP
        assert "deepseek" in provider_class.MODEL_MAP
        assert "grok" in provider_class.MODEL_MAP

    def test_default_model(self, provider_class):
        """Test DEFAULT_MODEL is set."""
        assert provider_class.DEFAULT_MODEL == "claude"

    def test_default_headers_exist(self, provider_class):
        """Test DEFAULT_HEADERS attribute exists."""
        assert hasattr(provider_class, "DEFAULT_HEADERS")
        assert isinstance(provider_class.DEFAULT_HEADERS, dict)
        assert "HTTP-Referer" in provider_class.DEFAULT_HEADERS
        assert "X-Title" in provider_class.DEFAULT_HEADERS


class TestProviderInheritance:
    """Tests that all providers properly inherit from BaseProvider."""

    def test_all_providers_inherit_from_base(self):
        """Test that all loaded providers are subclasses of BaseProvider."""
        provider_files = [
            "gemini-3.py",
            "openai-cli.py",
            "deepseek-cli.py",
            "groq-cli.py",
            "openrouter-cli.py",
        ]

        for filename in provider_files:
            _, provider = try_load_provider(filename)
            if provider is not None:
                assert issubclass(provider, BaseProvider)

    def test_grok_inherits_with_enable_gate(self):
        """Test Grok provider inheritance with enable gate."""
        original_value = os.environ.get("SYNOD_ENABLE_GROK")
        os.environ["SYNOD_ENABLE_GROK"] = "1"

        try:
            _, provider = try_load_provider("grok-cli.py")
            if provider is not None:
                assert issubclass(provider, BaseProvider)
        finally:
            if original_value is None:
                os.environ.pop("SYNOD_ENABLE_GROK", None)
            else:
                os.environ["SYNOD_ENABLE_GROK"] = original_value

    def test_mistral_inherits_with_enable_gate(self):
        """Test Mistral provider inheritance with enable gate."""
        original_value = os.environ.get("SYNOD_ENABLE_MISTRAL")
        os.environ["SYNOD_ENABLE_MISTRAL"] = "1"

        try:
            _, provider = try_load_provider("mistral-cli.py")
            if provider is not None:
                assert issubclass(provider, BaseProvider)
        finally:
            if original_value is None:
                os.environ.pop("SYNOD_ENABLE_MISTRAL", None)
            else:
                os.environ["SYNOD_ENABLE_MISTRAL"] = original_value


class TestProviderAbstractMethods:
    """Tests that providers implement required abstract methods."""

    def test_gemini_implements_abstract_methods(self):
        """Test Gemini provider implements all abstract methods."""
        _, provider = try_load_provider("gemini-3.py")
        if provider is None:
            pytest.skip("Gemini provider not available")

        assert hasattr(provider, "create_client")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "add_provider_args")
        assert callable(getattr(provider, "create_client"))
        assert callable(getattr(provider, "generate"))
        assert callable(getattr(provider, "add_provider_args"))

    def test_openai_implements_abstract_methods(self):
        """Test OpenAI provider implements all abstract methods."""
        _, provider = try_load_provider("openai-cli.py")
        if provider is None:
            pytest.skip("OpenAI provider not available")

        assert hasattr(provider, "create_client")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "add_provider_args")

    def test_deepseek_implements_abstract_methods(self):
        """Test DeepSeek provider implements all abstract methods."""
        _, provider = try_load_provider("deepseek-cli.py")
        if provider is None:
            pytest.skip("DeepSeek provider not available")

        assert hasattr(provider, "create_client")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "add_provider_args")

    def test_groq_implements_abstract_methods(self):
        """Test Groq provider implements all abstract methods."""
        _, provider = try_load_provider("groq-cli.py")
        if provider is None:
            pytest.skip("Groq provider not available")

        assert hasattr(provider, "create_client")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "add_provider_args")

    def test_openrouter_implements_abstract_methods(self):
        """Test OpenRouter provider implements all abstract methods."""
        _, provider = try_load_provider("openrouter-cli.py")
        if provider is None:
            pytest.skip("OpenRouter provider not available")

        assert hasattr(provider, "create_client")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "add_provider_args")
