"""Tests for difficulty-based model tier routing (v3.1).

Tests tier config functions in synod_config.py and tier output in synod-classifier.py.
TDD RED phase: these tests define the expected behavior before implementation.
"""

import importlib.util
import json
import os
import sys

import pytest


# --- Fixtures ---


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the config cache before each test."""
    import tools.synod_config as config_module
    config_module._CONFIG_CACHE = None
    yield
    config_module._CONFIG_CACHE = None


# Load classifier module (hyphenated filename requires importlib)
_classifier_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "synod-classifier.py"
)
_spec = importlib.util.spec_from_file_location("synod_classifier", _classifier_path)
_classifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_classifier)


# --- TestTierConfig: synod_config.py tier functions ---


class TestTierConfig:
    """Test tier-related functions in synod_config.py."""

    def test_tiers_section_exists_in_config(self):
        """YAML config contains a 'tiers' section."""
        from tools.synod_config import load_config
        config = load_config()
        assert "tiers" in config

    def test_tier_mapping_section_exists_in_config(self):
        """YAML config contains a 'tier_mapping' section."""
        from tools.synod_config import load_config
        config = load_config()
        assert "tier_mapping" in config

    def test_list_tiers_returns_three(self):
        """list_tiers returns exactly 3 tiers: fast, standard, deep."""
        from tools.synod_config import list_tiers
        tiers = list_tiers()
        assert isinstance(tiers, list)
        assert set(tiers) == {"fast", "standard", "deep"}

    def test_get_tier_simple_returns_fast(self):
        """complexity='simple' maps to tier='fast'."""
        from tools.synod_config import get_tier
        assert get_tier("simple") == "fast"

    def test_get_tier_medium_returns_standard(self):
        """complexity='medium' maps to tier='standard'."""
        from tools.synod_config import get_tier
        assert get_tier("medium") == "standard"

    def test_get_tier_complex_returns_deep(self):
        """complexity='complex' maps to tier='deep'."""
        from tools.synod_config import get_tier
        assert get_tier("complex") == "deep"

    def test_get_tier_unknown_returns_standard(self):
        """Unknown complexity falls back to 'standard'."""
        from tools.synod_config import get_tier
        assert get_tier("unknown") == "standard"
        assert get_tier("") == "standard"

    def test_get_tier_config_fast(self):
        """fast tier config has gemini flash and openai gpt4o."""
        from tools.synod_config import get_tier_config
        config = get_tier_config("fast")
        assert config["gemini"]["model"] == "flash"
        assert config["openai"]["model"] == "gpt4o"

    def test_get_tier_config_deep(self):
        """deep tier config has gemini pro and openai o3."""
        from tools.synod_config import get_tier_config
        config = get_tier_config("deep")
        assert config["gemini"]["model"] == "pro"
        assert config["openai"]["model"] == "o3"

    def test_get_tier_config_standard_has_no_model_overrides(self):
        """standard tier has description but no model overrides."""
        from tools.synod_config import get_tier_config
        config = get_tier_config("standard")
        assert "description" in config
        assert "gemini" not in config
        assert "openai" not in config

    def test_get_tier_config_unknown_returns_empty(self):
        """Unknown tier returns empty dict."""
        from tools.synod_config import get_tier_config
        assert get_tier_config("nonexistent") == {}

    def test_get_tiered_model_config_overrides_mode(self):
        """Tier 'fast' overrides review mode's openai from o3 to gpt4o."""
        from tools.synod_config import get_tiered_model_config
        # review mode default: openai o3, reasoning medium
        config = get_tiered_model_config("review", "openai", "fast")
        assert config["model"] == "gpt4o"

    def test_get_tiered_model_config_none_tier_preserves_mode(self):
        """tier=None preserves the original mode config."""
        from tools.synod_config import get_tiered_model_config, get_model_config
        original = get_model_config("review", "openai")
        tiered = get_tiered_model_config("review", "openai", None)
        assert tiered == original

    def test_get_tiered_model_config_standard_preserves_mode(self):
        """tier='standard' preserves the original mode config (no overrides)."""
        from tools.synod_config import get_tiered_model_config, get_model_config
        original = get_model_config("design", "gemini")
        tiered = get_tiered_model_config("design", "gemini", "standard")
        assert tiered == original

    def test_get_tiered_model_config_merges_thinking(self):
        """Tier config merges thinking/reasoning into mode config."""
        from tools.synod_config import get_tiered_model_config
        # general mode gemini: flash, thinking medium
        # deep tier gemini: pro, thinking high
        config = get_tiered_model_config("general", "gemini", "deep")
        assert config["model"] == "pro"
        assert config["thinking"] == "high"

    # --- Confidence-to-Tier Linkage (v3.2) ---

    def test_get_tier_with_confidence_high(self):
        """High confidence does not promote tier: simple stays fast."""
        from tools.synod_config import get_tier
        assert get_tier("simple", confidence=0.8) == "fast"

    def test_get_tier_with_confidence_low(self):
        """Low confidence promotes tier: simple -> standard."""
        from tools.synod_config import get_tier
        assert get_tier("simple", confidence=0.3) == "standard"

    def test_get_tier_with_confidence_medium_low(self):
        """Low confidence promotes tier: medium -> deep."""
        from tools.synod_config import get_tier
        assert get_tier("medium", confidence=0.3) == "deep"

    def test_get_tier_complex_no_promotion(self):
        """Complex is already max tier, low confidence doesn't change it."""
        from tools.synod_config import get_tier
        assert get_tier("complex", confidence=0.3) == "deep"

    def test_get_tier_no_confidence_backward_compat(self):
        """Without confidence param, behavior is unchanged (backward compat)."""
        from tools.synod_config import get_tier
        assert get_tier("simple") == "fast"
        assert get_tier("medium") == "standard"
        assert get_tier("complex") == "deep"

    def test_get_tier_confidence_threshold_from_config(self):
        """Promotion threshold comes from YAML thresholds.low_confidence."""
        from tools.synod_config import get_tier, get_threshold
        threshold = get_threshold("low_confidence", 50) / 100  # 0.5
        # Confidence just above threshold: no promotion
        assert get_tier("simple", confidence=threshold + 0.01) == "fast"
        # Confidence just below threshold: promoted
        assert get_tier("simple", confidence=threshold - 0.01) == "standard"


# --- TestClassifierTierOutput: synod-classifier.py tier output ---


class TestClassifierTierOutput:
    """Test tier field in classifier JSON output."""

    def test_main_json_includes_tier(self, capsys):
        """Main JSON output includes 'tier' field."""
        sys.argv = ["synod-classifier.py", "hello world"]
        _classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert "tier" in output

    def test_simple_prompt_tier_fast(self, capsys):
        """Short simple prompt gets tier='fast'."""
        sys.argv = ["synod-classifier.py", "hi"]
        _classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert output["tier"] == "fast"

    def test_complex_prompt_tier_deep(self, capsys):
        """Long prompt with code blocks gets tier='deep'."""
        prompt = " ".join(["word"] * 300) + "\n```python\ncode\n```\n```js\ncode\n```"
        sys.argv = ["synod-classifier.py", prompt]
        _classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert output["tier"] == "deep"

    def test_mode_only_no_tier(self, capsys):
        """--mode-only outputs plain text mode without tier."""
        sys.argv = ["synod-classifier.py", "--mode-only", "hello"]
        _classifier.main()
        output = capsys.readouterr().out.strip()
        # mode-only should be plain text, not JSON
        assert output in ("review", "design", "debug", "idea", "general")
        assert "tier" not in output
