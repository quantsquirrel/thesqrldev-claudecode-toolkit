"""
Tests for canary.py and synod-canary.py - Canary pre-sampling health checks.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from canary import (
    CANARY_MODEL_MAP,
    CANARY_PROMPT,
    CANARY_TIMEOUT_SECONDS,
    CACHE_TTL_SECONDS,
    CLI_MAP,
    CanaryCache,
    CanaryProbe,
)
from model_stats import ModelStats


class TestConstants:
    """Tests for canary constants."""

    def test_canary_prompt_is_simple(self):
        """Test that canary prompt is lightweight."""
        assert len(CANARY_PROMPT) < 100
        assert "ready" in CANARY_PROMPT.lower()

    def test_canary_timeout_is_reasonable(self):
        """Test that canary timeout is reasonable (not too long)."""
        assert CANARY_TIMEOUT_SECONDS <= 60
        assert CANARY_TIMEOUT_SECONDS >= 10

    def test_cache_ttl_is_appropriate(self):
        """Test that cache TTL is set to 5 minutes."""
        assert CACHE_TTL_SECONDS == 300

    def test_cli_map_has_all_providers(self):
        """Test that CLI_MAP includes all 7 providers."""
        expected_providers = ["gemini", "openai", "deepseek", "groq", "grok", "mistral", "openrouter"]
        for provider in expected_providers:
            assert provider in CLI_MAP

    def test_cli_map_values_are_valid_filenames(self):
        """Test that CLI_MAP values are valid Python filenames."""
        for cli_file in CLI_MAP.values():
            assert cli_file.endswith(".py")
            assert " " not in cli_file

    def test_canary_model_map_has_all_providers(self):
        """Test that each provider has a canary model."""
        for provider in CLI_MAP.keys():
            assert provider in CANARY_MODEL_MAP


class TestCanaryCache:
    """Tests for CanaryCache class."""

    def test_cache_init_creates_parent_directory(self, tmp_path):
        """Test that cache initialization creates parent directory."""
        cache_path = tmp_path / "subdir" / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))
        assert cache.cache_path.parent.exists()

    def test_cache_get_returns_none_for_missing_file(self, tmp_path):
        """Test that get returns None when cache file doesn't exist."""
        cache = CanaryCache(cache_path=str(tmp_path / "cache.json"))
        result = cache.get("gemini", "flash")
        assert result is None

    def test_cache_get_returns_none_for_missing_key(self, tmp_path):
        """Test that get returns None for missing cache key."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        # Write cache with different key
        cache.set("openai", "gpt4o", {"healthy": True})

        # Try to get different key
        result = cache.get("gemini", "flash")
        assert result is None

    def test_cache_get_returns_none_for_expired_entry(self, tmp_path):
        """Test that get returns None for expired cache entries."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        # Manually write expired cache entry
        expired_time = datetime.now() - timedelta(seconds=CACHE_TTL_SECONDS + 1)
        cache_data = {
            "gemini:flash": {
                "timestamp": expired_time.isoformat(),
                "result": {"healthy": True, "latency_ms": 100.0},
            }
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        result = cache.get("gemini", "flash")
        assert result is None

    def test_cache_get_returns_valid_entry(self, tmp_path):
        """Test that get returns valid cached entry."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        expected_result = {"healthy": True, "latency_ms": 123.4}
        cache.set("gemini", "flash", expected_result)

        result = cache.get("gemini", "flash")
        assert result == expected_result

    def test_cache_set_creates_new_entry(self, tmp_path):
        """Test that set creates new cache entry."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        result_data = {"healthy": True, "latency_ms": 100.0}
        cache.set("gemini", "flash", result_data)

        assert cache_path.exists()
        with open(cache_path) as f:
            cache_data = json.load(f)

        assert "gemini:flash" in cache_data
        assert cache_data["gemini:flash"]["result"] == result_data

    def test_cache_set_updates_existing_entry(self, tmp_path):
        """Test that set updates existing cache entry."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        # Set initial value
        cache.set("gemini", "flash", {"healthy": True, "latency_ms": 100.0})

        # Update with new value
        cache.set("gemini", "flash", {"healthy": False, "latency_ms": 5000.0})

        result = cache.get("gemini", "flash")
        assert result["healthy"] is False
        assert result["latency_ms"] == 5000.0

    def test_cache_set_preserves_other_entries(self, tmp_path):
        """Test that set preserves other cache entries."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        cache.set("gemini", "flash", {"healthy": True})
        cache.set("openai", "gpt4o", {"healthy": True})

        # Both should still exist
        assert cache.get("gemini", "flash") is not None
        assert cache.get("openai", "gpt4o") is not None

    def test_cache_set_includes_timestamp(self, tmp_path):
        """Test that set includes ISO timestamp."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        cache.set("gemini", "flash", {"healthy": True})

        with open(cache_path) as f:
            cache_data = json.load(f)

        timestamp = cache_data["gemini:flash"]["timestamp"]
        # Should be valid ISO 8601 format
        datetime.fromisoformat(timestamp)  # Should not raise

    def test_cache_handles_corrupted_json(self, tmp_path):
        """Test that cache handles corrupted JSON gracefully."""
        cache_path = tmp_path / "cache.json"
        cache = CanaryCache(cache_path=str(cache_path))

        # Write corrupted JSON
        with open(cache_path, "w") as f:
            f.write("{corrupted json")

        # Should return None instead of crashing
        result = cache.get("gemini", "flash")
        assert result is None

        # Should be able to set new entries
        cache.set("gemini", "flash", {"healthy": True})
        result = cache.get("gemini", "flash")
        assert result["healthy"] is True


class TestCanaryProbeInit:
    """Tests for CanaryProbe initialization."""

    def test_probe_init_with_stats(self, tmp_path):
        """Test probe initialization with ModelStats."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=True)
        assert probe.stats is stats
        assert probe.cache is not None

    def test_probe_init_without_cache(self, tmp_path):
        """Test probe initialization without cache."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)
        assert probe.cache is None

    def test_probe_finds_tools_directory(self, tmp_path):
        """Test that probe finds tools directory."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats)
        assert probe.tools_dir.exists()


class TestGetCliPath:
    """Tests for _get_cli_path() method."""

    def test_get_cli_path_returns_correct_path(self, tmp_path):
        """Test that _get_cli_path returns correct CLI tool path."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats)

        path = probe._get_cli_path("gemini")
        assert path.name == "gemini-3.py"
        assert "tools" in str(path)

    def test_get_cli_path_raises_for_unknown_provider(self, tmp_path):
        """Test that _get_cli_path raises ValueError for unknown provider."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats)

        with pytest.raises(ValueError, match="Unknown provider"):
            probe._get_cli_path("unknown_provider")


class TestProbeViaSubprocess:
    """Tests for _probe_via_subprocess() method."""

    def test_probe_via_subprocess_returns_healthy_on_success(self, tmp_path):
        """Test that probe returns healthy status on successful subprocess call."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        # Mock subprocess.run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ready"
        mock_result.stderr = ""

        with patch("canary.subprocess.run", return_value=mock_result):
            result = probe._probe_via_subprocess("gemini", "flash")

        assert result["healthy"] is True
        assert result["latency_ms"] > 0
        assert "response_preview" in result

    def test_probe_via_subprocess_returns_unhealthy_on_error(self, tmp_path):
        """Test that probe returns unhealthy on subprocess error."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        # Mock subprocess.run to return error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "API Error"

        with patch("canary.subprocess.run", return_value=mock_result):
            result = probe._probe_via_subprocess("gemini", "flash")

        assert result["healthy"] is False
        assert result["fallback_recommended"] is True
        assert "error" in result

    def test_probe_via_subprocess_handles_timeout(self, tmp_path):
        """Test that probe handles subprocess timeout."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        # Mock subprocess.run to raise TimeoutExpired
        with patch("canary.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = probe._probe_via_subprocess("gemini", "flash")

        assert result["healthy"] is False
        assert result["fallback_recommended"] is True
        assert "Timeout" in result["error"]

    def test_probe_via_subprocess_handles_missing_cli_tool(self, tmp_path):
        """Test that probe handles missing CLI tool gracefully."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        # Mock _get_cli_path to return non-existent path
        with patch.object(probe, "_get_cli_path", return_value=Path("/nonexistent/tool.py")):
            result = probe._probe_via_subprocess("gemini", "flash")

        assert result["healthy"] is False
        assert result["fallback_recommended"] is True
        assert "not found" in result["error"]

    def test_probe_via_subprocess_uses_correct_model(self, tmp_path):
        """Test that probe uses correct model for subprocess call."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ready"

        with patch("canary.subprocess.run", return_value=mock_result) as mock_run:
            probe._probe_via_subprocess("gemini", "flash")

            # Verify subprocess was called with correct args
            args = mock_run.call_args[0][0]
            assert "--model" in args
            assert "flash" in args

    def test_probe_via_subprocess_uses_canary_model_when_no_model_specified(self, tmp_path):
        """Test that probe uses canary default model when none specified."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ready"

        with patch("canary.subprocess.run", return_value=mock_result) as mock_run:
            probe._probe_via_subprocess("gemini", None)

            # Should use canary default model
            args = mock_run.call_args[0][0]
            expected_model = CANARY_MODEL_MAP["gemini"]
            assert expected_model in args

    def test_probe_via_subprocess_handles_general_exception(self, tmp_path):
        """Test that probe handles general exceptions."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        with patch("canary.subprocess.run", side_effect=Exception("Unknown error")):
            result = probe._probe_via_subprocess("gemini", "flash")

        assert result["healthy"] is False
        assert result["fallback_recommended"] is True
        assert "Unknown error" in result["error"]


class TestProbeMethod:
    """Tests for probe() method."""

    def test_probe_uses_cache_when_available(self, tmp_path):
        """Test that probe uses cached result when available."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=True)

        # Set cache
        cache_result = {"healthy": True, "latency_ms": 100.0}
        probe.cache.set("gemini", "flash", cache_result)

        # Probe should return cached result without calling subprocess
        with patch.object(probe, "_probe_via_subprocess") as mock_subprocess:
            result = probe.probe("gemini", "flash")

            # Subprocess should not be called
            mock_subprocess.assert_not_called()

            # Result should be from cache
            assert result["healthy"] is True
            assert result["cached"] is True

    def test_probe_skips_cache_when_not_available(self, tmp_path):
        """Test that probe executes subprocess when cache miss."""
        cache_path = tmp_path / "canary-cache.json"
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Create probe with custom cache path to ensure cache miss
        probe = CanaryProbe(stats, use_cache=True)
        probe.cache.cache_path = cache_path

        # Mock subprocess to return success
        mock_subprocess_result = {"healthy": True, "latency_ms": 200.0}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_subprocess_result):
            result = probe.probe("gemini", "flash")

            assert result["healthy"] is True
            assert result["cached"] is False

    def test_probe_without_cache_always_executes_subprocess(self, tmp_path):
        """Test that probe always executes subprocess when cache disabled."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        mock_subprocess_result = {"healthy": True, "latency_ms": 200.0}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_subprocess_result):
            result = probe.probe("gemini", "flash")

            assert result["cached"] is False

    def test_probe_checks_p95_threshold(self, tmp_path):
        """Test that probe checks latency against P95 threshold."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record observations to establish P95
        for i in range(1, 101):
            stats.record_latency("gemini", "flash", float(i * 100))

        probe = CanaryProbe(stats, use_cache=False)

        # Mock subprocess with latency exceeding P95
        p95 = stats.get_percentile("gemini", "flash", 95)
        mock_result = {"healthy": True, "latency_ms": p95 + 1000}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            result = probe.probe("gemini", "flash")

            assert result["exceeded_p95"] is True
            assert result["fallback_recommended"] is True

    def test_probe_passes_p95_threshold(self, tmp_path):
        """Test that probe passes when latency under P95."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record observations
        for i in range(1, 101):
            stats.record_latency("gemini", "flash", float(i * 100))

        probe = CanaryProbe(stats, use_cache=False)

        # Mock subprocess with latency under P95
        p95 = stats.get_percentile("gemini", "flash", 95)
        mock_result = {"healthy": True, "latency_ms": p95 - 1000}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            result = probe.probe("gemini", "flash")

            assert result["exceeded_p95"] is False
            assert result["fallback_recommended"] is False

    def test_probe_sets_fallback_for_unhealthy_result(self, tmp_path):
        """Test that probe sets fallback_recommended for unhealthy results."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        mock_result = {
            "healthy": False,
            "latency_ms": 100.0,
            "error": "API Error",
            "fallback_recommended": True,
        }

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            result = probe.probe("gemini", "flash")

            assert result["fallback_recommended"] is True
            assert result["exceeded_p95"] is False

    def test_probe_caches_result(self, tmp_path):
        """Test that probe caches the result after execution."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=True)

        mock_result = {"healthy": True, "latency_ms": 100.0}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            probe.probe("gemini", "flash")

            # Result should be cached
            cached = probe.cache.get("gemini", "flash")
            assert cached is not None
            assert cached["healthy"] is True

    def test_probe_uses_default_canary_model_when_none_specified(self, tmp_path):
        """Test that probe uses canary default model when model is None."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        mock_result = {"healthy": True, "latency_ms": 100.0}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result) as mock:
            probe.probe("gemini", None)

            # Should call with canary default model
            mock.assert_called_once()
            call_args = mock.call_args[0]
            assert call_args[1] == CANARY_MODEL_MAP["gemini"]


class TestSynodCanaryCLI:
    """Tests for synod-canary CLI functions."""

    def test_probe_single_returns_result_dict(self, tmp_path, monkeypatch):
        """Test that probe_single returns result with provider and model."""
        # Import after adding to path
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "synod_canary",
            os.path.join(os.path.dirname(__file__), "..", "tools", "synod-canary.py"),
        )
        synod_canary = importlib.util.module_from_spec(spec)

        # Mock CanaryProbe
        with patch("canary.CanaryProbe") as mock_probe_class:
            mock_probe = MagicMock()
            mock_probe.probe.return_value = {"healthy": True, "latency_ms": 100.0}
            mock_probe_class.return_value = mock_probe

            spec.loader.exec_module(synod_canary)
            result = synod_canary.probe_single("gemini", "flash", no_cache=False)

            assert result["provider"] == "gemini"
            assert result["model"] == "flash"
            assert result["healthy"] is True

    def test_probe_all_returns_list_of_results(self, tmp_path, monkeypatch):
        """Test that probe_all returns results for all providers."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "synod_canary",
            os.path.join(os.path.dirname(__file__), "..", "tools", "synod-canary.py"),
        )
        synod_canary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(synod_canary)

        # Mock probe_single to return different providers
        def mock_probe_single(provider, model, no_cache):
            return {
                "provider": provider,
                "model": model or CANARY_MODEL_MAP.get(provider),
                "healthy": True,
                "latency_ms": 100.0,
            }

        with patch.object(synod_canary, "probe_single", side_effect=mock_probe_single):
            results = synod_canary.probe_all(no_cache=False)

            # Should return results for all providers in CLI_MAP
            assert len(results) == len(CLI_MAP)
            providers = [r["provider"] for r in results]
            for provider in CLI_MAP.keys():
                assert provider in providers


class TestCanaryIntegration:
    """Integration tests for canary system."""

    def test_canary_workflow_without_cache(self, tmp_path):
        """Test complete canary workflow without cache."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=False)

        # Record some stats
        for i in range(20):
            stats.record_latency("gemini", "flash", float(i * 100))

        # Mock successful probe
        mock_result = {"healthy": True, "latency_ms": 500.0}

        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            result = probe.probe("gemini", "flash")

            assert result["healthy"] is True
            assert result["cached"] is False
            assert "exceeded_p95" in result
            assert "fallback_recommended" in result

    def test_canary_workflow_with_cache(self, tmp_path):
        """Test complete canary workflow with cache."""
        cache_path = tmp_path / "canary-cache.json"
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        probe = CanaryProbe(stats, use_cache=True)
        probe.cache.cache_path = cache_path

        # First probe (cache miss)
        mock_result = {"healthy": True, "latency_ms": 100.0}
        with patch.object(probe, "_probe_via_subprocess", return_value=mock_result):
            result1 = probe.probe("gemini", "flash")
            assert result1["cached"] is False

        # Second probe (cache hit)
        result2 = probe.probe("gemini", "flash")
        assert result2["cached"] is True
        assert result2["healthy"] is True
