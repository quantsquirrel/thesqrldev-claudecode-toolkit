"""Tests for synod-setup.py routing defaults."""

import importlib.util
from pathlib import Path


def load_setup_module():
    module_path = Path(__file__).parent.parent / "tools" / "synod-setup.py"
    spec = importlib.util.spec_from_file_location("synod_setup", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestSynodSetupRouting:
    def test_default_wrappers_include_agy_and_cliproxy(self):
        setup = load_setup_module()

        assert setup.PRIMARY_CLI_TOOLS["agy-cli"] == "agy-cli"
        assert setup.PRIMARY_CLI_TOOLS["cliproxy-cli"] == "cliproxy-cli.py"
        assert setup.LEGACY_FALLBACK_CLI_TOOLS["gemini-3"] == "gemini-3.py"
        assert setup.LEGACY_FALLBACK_CLI_TOOLS["openai-cli"] == "openai-cli.py"
        assert setup.CLI_TOOLS["gemini-3"] == "gemini-3.py"
        assert setup.CLI_TOOLS["openai-cli"] == "openai-cli.py"

    def test_setup_does_not_require_retired_gemini_direct_dependency(self):
        setup = load_setup_module()

        assert "google-genai" not in setup.REQUIRED_PACKAGES
        assert setup.OPTIONAL_FALLBACK_PACKAGES["google-genai"] == "google.genai"
        assert setup.REQUIRED_PACKAGES["openai"] == "openai"
        assert setup.REQUIRED_PACKAGES["httpx"] == "httpx"

    def test_default_model_tests_use_local_bridges(self):
        setup = load_setup_module()

        assert setup.MODELS_TO_TEST["gemini"]["cli"] == "agy-cli"
        assert setup.MODELS_TO_TEST["gemini"]["models"] == ["3.5-flash"]
        assert setup.MODELS_TO_TEST["gemini"]["env_key"] is None

        assert setup.MODELS_TO_TEST["openai"]["cli"] == "cliproxy-cli.py"
        assert setup.MODELS_TO_TEST["openai"]["models"] == ["gpt55fast"]
        assert setup.MODELS_TO_TEST["openai"]["env_key"] == "CLIPROXY_API_KEY"
        assert setup.MODELS_TO_TEST["openai"]["optional_env_key"] is True

    def test_setup_targets_exercise_gemini_35_flash_and_cliproxy(self):
        setup = load_setup_module()

        assert ("gemini", "3.5-flash") in setup.TEST_TARGETS
        assert ("openai", "gpt55fast") in setup.TEST_TARGETS
        assert ("gemini", "pro") not in setup.TEST_TARGETS
        assert ("openai", "o3") not in setup.TEST_TARGETS

    def test_model_matrix_preserves_previous_defaults_as_legacy_fallbacks(self):
        import json

        matrix_path = Path(__file__).parent.parent / "config" / "model_matrix.json"
        matrix = json.loads(matrix_path.read_text())

        assert matrix["tiers"]["standard"][0]["cli"] == "agy-cli"
        assert matrix["tiers"]["standard"][1]["cli"] == "cliproxy-cli"
        assert matrix["legacy_fallbacks"]["standard"][0] == {
            "provider": "gemini",
            "cli": "gemini-3",
            "model": "pro",
            "thinking": "medium",
            "timeout_sec": 120,
        }
        assert matrix["legacy_fallbacks"]["standard"][1] == {
            "provider": "openai",
            "cli": "openai-cli",
            "model": "o3",
            "reasoning": "medium",
            "timeout_sec": 120,
        }

    def test_key_check_accepts_local_bridge_providers_without_cloud_api_keys(self):
        setup = load_setup_module()

        assert setup.check_api_key("gemini")[0] is True
        assert setup.check_api_key("openai")[0] is True
