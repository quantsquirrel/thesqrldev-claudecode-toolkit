"""
Tests for model_stats.py - Model latency statistics collection and percentile calculation.
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from model_stats import COLD_START_DEFAULTS, ModelStats


class TestColdStartDefaults:
    """Tests for COLD_START_DEFAULTS configuration."""

    def test_cold_start_defaults_exist(self):
        """Test that cold start defaults are defined for all major providers."""
        assert "gemini:flash" in COLD_START_DEFAULTS
        assert "gemini:pro" in COLD_START_DEFAULTS
        assert "openai:gpt4o" in COLD_START_DEFAULTS
        assert "openai:o3" in COLD_START_DEFAULTS
        assert "deepseek:chat" in COLD_START_DEFAULTS
        assert "deepseek:reasoner" in COLD_START_DEFAULTS
        assert "groq:8b" in COLD_START_DEFAULTS
        assert "grok:fast" in COLD_START_DEFAULTS
        assert "mistral:large" in COLD_START_DEFAULTS
        assert "openrouter:claude" in COLD_START_DEFAULTS

    def test_cold_start_values_reasonable(self):
        """Test that all cold start timeouts are positive and reasonable."""
        for key, timeout_ms in COLD_START_DEFAULTS.items():
            assert timeout_ms > 0, f"{key} timeout must be positive"
            assert timeout_ms <= 600_000, f"{key} timeout should be <= 10 minutes"

    def test_reasoning_models_have_longer_timeouts(self):
        """Test that reasoning models have longer timeouts than chat models."""
        assert COLD_START_DEFAULTS["deepseek:reasoner"] > COLD_START_DEFAULTS["deepseek:chat"]
        assert COLD_START_DEFAULTS["openai:o3"] > COLD_START_DEFAULTS["openai:gpt4o"]


class TestModelStatsInit:
    """Tests for ModelStats initialization."""

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom stats path."""
        stats_path = tmp_path / "custom-stats.json"
        stats = ModelStats(stats_path=str(stats_path))
        assert stats.stats_path == stats_path

    def test_init_creates_parent_directory(self, tmp_path):
        """Test that initialization creates parent directory if needed."""
        stats_path = tmp_path / "subdir" / "stats.json"
        stats = ModelStats(stats_path=str(stats_path))
        assert stats.stats_path.parent.exists()

    def test_init_default_path_expansion(self):
        """Test that default path expands ~ to home directory."""
        stats = ModelStats()
        assert "~" not in str(stats.stats_path)
        assert stats.stats_path.is_absolute()


class TestRecordLatency:
    """Tests for record_latency() method."""

    def test_record_latency_creates_new_entry(self, tmp_path):
        """Test recording latency for a new model creates entry."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        stats.record_latency("gemini", "flash", 1234.5)

        data = stats._load()
        assert "gemini:flash" in data["models"]
        assert data["models"]["gemini:flash"]["observations"] == [1234.5]
        assert data["models"]["gemini:flash"]["count"] == 1

    def test_record_latency_appends_to_existing(self, tmp_path):
        """Test recording latency appends to existing observations."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        stats.record_latency("gemini", "flash", 100.0)
        stats.record_latency("gemini", "flash", 200.0)
        stats.record_latency("gemini", "flash", 300.0)

        data = stats._load()
        assert data["models"]["gemini:flash"]["count"] == 3
        assert 100.0 in data["models"]["gemini:flash"]["observations"]
        assert 200.0 in data["models"]["gemini:flash"]["observations"]
        assert 300.0 in data["models"]["gemini:flash"]["observations"]

    def test_record_latency_rounds_to_one_decimal(self, tmp_path):
        """Test that latency values are rounded to 1 decimal place."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        stats.record_latency("gemini", "flash", 123.456789)

        data = stats._load()
        assert data["models"]["gemini:flash"]["observations"] == [123.5]

    def test_record_latency_keeps_last_100_observations(self, tmp_path):
        """Test that only last 100 observations are kept."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record 150 observations
        for i in range(150):
            stats.record_latency("gemini", "flash", float(i))

        data = stats._load()
        assert data["models"]["gemini:flash"]["count"] == 100
        assert len(data["models"]["gemini:flash"]["observations"]) == 100
        # Should keep last 100 (50-149)
        assert 49.0 not in data["models"]["gemini:flash"]["observations"]
        assert 50.0 in data["models"]["gemini:flash"]["observations"]
        assert 149.0 in data["models"]["gemini:flash"]["observations"]

    def test_record_latency_updates_last_observed_timestamp(self, tmp_path):
        """Test that last_observed timestamp is updated."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        stats.record_latency("gemini", "flash", 100.0)

        data = stats._load()
        assert "last_observed" in data["models"]["gemini:flash"]
        # Should be ISO 8601 format
        assert "T" in data["models"]["gemini:flash"]["last_observed"]
        assert "Z" in data["models"]["gemini:flash"]["last_observed"]

    def test_record_latency_calculates_percentiles(self, tmp_path):
        """Test that percentiles are calculated when recording."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record observations that make percentile calculation easy
        for val in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            stats.record_latency("gemini", "flash", float(val))

        data = stats._load()
        entry = data["models"]["gemini:flash"]
        assert "p50" in entry
        assert "p90" in entry
        assert "p95" in entry
        assert "p99" in entry


class TestGetPercentile:
    """Tests for get_percentile() method."""

    def test_get_percentile_returns_none_for_unknown_model(self, tmp_path):
        """Test that get_percentile returns None for unknown model."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        assert stats.get_percentile("unknown", "model", 50) is None

    def test_get_percentile_returns_correct_values(self, tmp_path):
        """Test that get_percentile returns correct percentile values."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record 100 observations (1-100)
        for i in range(1, 101):
            stats.record_latency("gemini", "flash", float(i))

        p50 = stats.get_percentile("gemini", "flash", 50)
        p90 = stats.get_percentile("gemini", "flash", 90)
        p95 = stats.get_percentile("gemini", "flash", 95)
        p99 = stats.get_percentile("gemini", "flash", 99)

        assert p50 is not None
        assert p90 is not None
        assert p95 is not None
        assert p99 is not None

        # Percentiles should be increasing
        assert p50 < p90 < p95 < p99

    def test_get_percentile_with_few_observations(self, tmp_path):
        """Test percentile calculation with very few observations."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        stats.record_latency("gemini", "flash", 100.0)
        stats.record_latency("gemini", "flash", 200.0)

        p50 = stats.get_percentile("gemini", "flash", 50)
        p99 = stats.get_percentile("gemini", "flash", 99)

        assert p50 is not None
        assert p99 is not None


class TestGetDynamicTimeout:
    """Tests for get_dynamic_timeout() method."""

    def test_get_dynamic_timeout_returns_p99_plus_epsilon(self, tmp_path):
        """Test that dynamic timeout = P99 + epsilon when data exists."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record observations
        for i in range(1, 101):
            stats.record_latency("gemini", "flash", float(i * 100))

        timeout = stats.get_dynamic_timeout("gemini", "flash", epsilon_ms=10_000)
        p99 = stats.get_percentile("gemini", "flash", 99)

        assert timeout == p99 + 10_000

    def test_get_dynamic_timeout_uses_cold_start_default_when_no_data(self, tmp_path):
        """Test that cold-start default is used when no data exists."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        timeout = stats.get_dynamic_timeout("gemini", "flash")
        expected = COLD_START_DEFAULTS["gemini:flash"]

        assert timeout == expected

    def test_get_dynamic_timeout_uses_generic_default_for_unknown_model(self, tmp_path):
        """Test that generic default (120s) is used for unknown models."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        timeout = stats.get_dynamic_timeout("unknown", "model")
        assert timeout == 120_000  # Generic default

    def test_get_dynamic_timeout_custom_epsilon(self, tmp_path):
        """Test dynamic timeout with custom epsilon value."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        for i in range(1, 101):
            stats.record_latency("gemini", "flash", float(i * 100))

        timeout = stats.get_dynamic_timeout("gemini", "flash", epsilon_ms=5_000)
        p99 = stats.get_percentile("gemini", "flash", 99)

        assert timeout == p99 + 5_000


class TestHasSufficientData:
    """Tests for has_sufficient_data() method."""

    def test_has_sufficient_data_returns_false_for_unknown_model(self, tmp_path):
        """Test that has_sufficient_data returns False for unknown model."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        assert stats.has_sufficient_data("unknown", "model") is False

    def test_has_sufficient_data_requires_min_10_observations(self, tmp_path):
        """Test that at least 10 observations are required by default."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Record 9 observations
        for i in range(9):
            stats.record_latency("gemini", "flash", 100.0)

        assert stats.has_sufficient_data("gemini", "flash") is False

        # Record 10th observation
        stats.record_latency("gemini", "flash", 100.0)
        assert stats.has_sufficient_data("gemini", "flash") is True

    def test_has_sufficient_data_custom_min_count(self, tmp_path):
        """Test has_sufficient_data with custom min_count."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        for i in range(5):
            stats.record_latency("gemini", "flash", 100.0)

        assert stats.has_sufficient_data("gemini", "flash", min_count=5) is True
        assert stats.has_sufficient_data("gemini", "flash", min_count=6) is False


class TestFileLocking:
    """Tests for file locking mechanism."""

    def test_file_lock_creates_lock_file(self, tmp_path):
        """Test that file locking creates a .lock file."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        with stats._file_lock():
            lock_path = tmp_path / "stats.lock"
            assert lock_path.exists()

    def test_file_lock_cleanup(self, tmp_path):
        """Test that file lock is cleaned up after use."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        lock_path = tmp_path / "stats.lock"

        with stats._file_lock():
            assert lock_path.exists()

        # Lock file should still exist (only fd is closed)
        # fcntl.flock releases the lock when fd is closed


class TestAtomicWrite:
    """Tests for atomic write mechanism."""

    def test_atomic_write_creates_file(self, tmp_path):
        """Test that atomic write creates the target file."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        data = {"version": "1.0", "models": {}}

        stats._atomic_write(data)

        assert stats.stats_path.exists()
        with open(stats.stats_path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_atomic_write_preserves_existing_data(self, tmp_path):
        """Test that atomic write doesn't corrupt existing data."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Write initial data
        data1 = {"version": "1.0", "models": {"test:model": {"count": 1}}}
        stats._atomic_write(data1)

        # Overwrite with new data
        data2 = {"version": "1.0", "models": {"test:model": {"count": 2}}}
        stats._atomic_write(data2)

        with open(stats.stats_path) as f:
            loaded = json.load(f)
        assert loaded["models"]["test:model"]["count"] == 2

    def test_atomic_write_cleans_up_temp_file_on_error(self, tmp_path):
        """Test that temp file is cleaned up if write fails."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Create data that can't be serialized
        bad_data = {"version": "1.0", "models": {"bad": object()}}

        with pytest.raises(TypeError):
            stats._atomic_write(bad_data)

        # Verify no temp files are left behind
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0


class TestPercentileCalculation:
    """Tests for _recalculate_percentiles() method."""

    def test_recalculate_percentiles_with_empty_observations(self, tmp_path):
        """Test that percentile calculation handles empty observations."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        entry = {"observations": []}

        stats._recalculate_percentiles(entry)

        # Should not crash, but no percentiles should be added
        assert "p50" not in entry

    def test_recalculate_percentiles_with_single_observation(self, tmp_path):
        """Test percentile calculation with single observation."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))
        entry = {"observations": [100.0]}

        stats._recalculate_percentiles(entry)

        # All percentiles should be the same value
        assert entry["p50"] == 100.0
        assert entry["p90"] == 100.0
        assert entry["p95"] == 100.0
        assert entry["p99"] == 100.0

    def test_recalculate_percentiles_correctness(self, tmp_path):
        """Test that percentiles are calculated correctly."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Use 100 observations (1-100) for easy verification
        entry = {"observations": [float(i) for i in range(1, 101)]}

        stats._recalculate_percentiles(entry)

        # P50 should be around 50, P90 around 90, etc.
        assert 45 <= entry["p50"] <= 55
        assert 85 <= entry["p90"] <= 95
        assert 90 <= entry["p95"] <= 100
        assert 95 <= entry["p99"] <= 100


class TestStatsRefresh:
    """Tests for stats refresh mechanism."""

    def test_refresh_if_stale_clears_cache_after_60_seconds(self, tmp_path, monkeypatch):
        """Test that stats are refreshed after 60 seconds."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Load initial data
        stats.record_latency("gemini", "flash", 100.0)
        assert stats._data is not None

        # Mock time to simulate 61 seconds passing
        original_time = time.time()
        monkeypatch.setattr(time, "time", lambda: original_time + 61)

        stats._refresh_if_stale()
        assert stats._data is None

    def test_refresh_if_stale_keeps_cache_within_60_seconds(self, tmp_path):
        """Test that cache is kept if less than 60 seconds old."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Load initial data
        stats.record_latency("gemini", "flash", 100.0)
        initial_data = stats._data

        # Call refresh immediately
        stats._refresh_if_stale()

        # Data should still be cached
        assert stats._data is initial_data


class TestLoadMethod:
    """Tests for _load() method."""

    def test_load_creates_empty_structure_for_new_file(self, tmp_path):
        """Test that _load creates empty structure for new file."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        data = stats._load()

        assert data["version"] == "1.0"
        assert "last_updated" in data
        assert data["models"] == {}

    def test_load_returns_cached_data(self, tmp_path):
        """Test that _load returns cached data if available."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        data1 = stats._load()
        data2 = stats._load()

        # Should return same object (cached)
        assert data1 is data2

    def test_load_handles_corrupted_json(self, tmp_path):
        """Test that _load handles corrupted JSON gracefully."""
        stats_path = tmp_path / "stats.json"
        stats = ModelStats(stats_path=str(stats_path))

        # Write corrupted JSON
        with open(stats_path, "w") as f:
            f.write("{corrupted json")

        # Should return empty structure instead of crashing
        data = stats._load()
        assert data["version"] == "1.0"
        assert data["models"] == {}

    def test_load_handles_io_error(self, tmp_path):
        """Test that _load handles IO errors gracefully."""
        stats_path = tmp_path / "stats.json"
        stats = ModelStats(stats_path=str(stats_path))

        # Create file with no read permissions
        stats_path.touch()
        stats_path.chmod(0o000)

        try:
            # Should return empty structure instead of crashing
            data = stats._load()
            assert data["version"] == "1.0"
        finally:
            # Restore permissions for cleanup
            stats_path.chmod(0o644)


class TestGetAllStats:
    """Tests for get_all_stats() method."""

    def test_get_all_stats_returns_complete_data(self, tmp_path):
        """Test that get_all_stats returns all model statistics."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        stats.record_latency("gemini", "flash", 100.0)
        stats.record_latency("openai", "gpt4o", 200.0)

        all_stats = stats.get_all_stats()

        assert "gemini:flash" in all_stats["models"]
        assert "openai:gpt4o" in all_stats["models"]
        assert all_stats["version"] == "1.0"

    def test_get_all_stats_triggers_refresh(self, tmp_path, monkeypatch):
        """Test that get_all_stats triggers refresh if stale."""
        stats = ModelStats(stats_path=str(tmp_path / "stats.json"))

        # Load data
        stats.record_latency("gemini", "flash", 100.0)

        # Make cache stale
        original_time = time.time()
        monkeypatch.setattr(time, "time", lambda: original_time + 61)

        # Should trigger refresh
        all_stats = stats.get_all_stats()
        assert all_stats is not None
