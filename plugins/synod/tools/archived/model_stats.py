#!/usr/bin/env python3
"""
Model latency statistics collection and percentile calculation.

Tracks per-model latency observations and calculates P50/P90/P95/P99
for adaptive timeout management.

Data stored at ~/.synod/model-stats.json with file locking for concurrent access.
"""

import fcntl
import json
import os
import tempfile
import time
from pathlib import Path


# Cold-start default timeouts (ms) - used when no historical data exists
COLD_START_DEFAULTS = {
    "gemini:flash": 60_000,
    "gemini:pro": 120_000,
    "gemini:2.5-flash": 60_000,
    "gemini:2.5-pro": 120_000,
    "openai:gpt4o": 60_000,
    "openai:o3": 180_000,
    "openai:o4mini": 60_000,
    "deepseek:chat": 60_000,
    "deepseek:reasoner": 300_000,
    "groq:8b": 30_000,
    "groq:70b": 45_000,
    "groq:mixtral": 60_000,
    "grok:fast": 60_000,
    "grok:grok4": 120_000,
    "grok:mini": 60_000,
    "grok:vision": 90_000,
    "mistral:large": 120_000,
    "mistral:medium": 90_000,
    "mistral:small": 60_000,
    "mistral:codestral": 90_000,
    "mistral:devstral": 90_000,
    "openrouter:claude": 120_000,
    "openrouter:llama": 60_000,
    "openrouter:qwen": 60_000,
}


class ModelStats:
    """Track and query model latency statistics with file-based persistence."""

    def __init__(self, stats_path: str = "~/.synod/model-stats.json"):
        self.stats_path = Path(stats_path).expanduser()
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = None
        self._last_load_time = 0

    def record_latency(self, provider: str, model: str, latency_ms: float) -> None:
        """Record a latency observation for a model with file locking."""
        with self._file_lock():
            data = self._load()
            key = f"{provider}:{model}"
            if key not in data["models"]:
                data["models"][key] = {"observations": [], "count": 0}

            entry = data["models"][key]
            entry["observations"].append(round(latency_ms, 1))
            # Keep last 100 observations
            entry["observations"] = entry["observations"][-100:]
            entry["count"] = len(entry["observations"])
            entry["last_observed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._recalculate_percentiles(entry)

            data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._atomic_write(data)
            self._data = data

    def get_percentile(self, provider: str, model: str, percentile: int) -> float | None:
        """Get P50/P90/P95/P99 latency for a model. Returns None if no data."""
        self._refresh_if_stale()
        data = self._load()
        key = f"{provider}:{model}"

        if key not in data["models"]:
            return None

        pkey = f"p{percentile}"
        return data["models"][key].get(pkey)

    def get_dynamic_timeout(self, provider: str, model: str, epsilon_ms: int = 10_000) -> float:
        """Calculate dynamic timeout = P99 + epsilon. Falls back to cold-start default."""
        p99 = self.get_percentile(provider, model, 99)
        if p99 is not None:
            return p99 + epsilon_ms

        # Cold-start default
        key = f"{provider}:{model}"
        return COLD_START_DEFAULTS.get(key, 120_000)

    def has_sufficient_data(self, provider: str, model: str, min_count: int = 10) -> bool:
        """Check if we have enough observations for reliable stats."""
        self._refresh_if_stale()
        data = self._load()
        key = f"{provider}:{model}"

        if key not in data["models"]:
            return False

        return data["models"][key].get("count", 0) >= min_count

    def get_all_stats(self) -> dict:
        """Get all model statistics."""
        self._refresh_if_stale()
        return self._load()

    def _recalculate_percentiles(self, entry: dict) -> None:
        """Recalculate P50/P90/P95/P99 from observations."""
        obs = sorted(entry["observations"])
        n = len(obs)
        if n == 0:
            return

        for p in [50, 90, 95, 99]:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            entry[f"p{p}"] = obs[idx]

    def _refresh_if_stale(self) -> None:
        """Refresh stats if older than 60 seconds."""
        if time.time() - self._last_load_time > 60:
            self._data = None

    def _load(self) -> dict:
        """Load stats from disk."""
        if self._data is not None:
            return self._data

        if self.stats_path.exists():
            try:
                with open(self.stats_path) as f:
                    self._data = json.load(f)
                    self._last_load_time = time.time()
                    return self._data
            except (json.JSONDecodeError, IOError):
                pass

        # Initialize empty structure
        self._data = {
            "version": "1.0",
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "models": {},
        }
        self._last_load_time = time.time()
        return self._data

    def _file_lock(self):
        """Context manager for file locking using fcntl.flock."""

        class FileLock:
            def __init__(self, path):
                self.lock_path = path.with_suffix(".lock")

            def __enter__(self):
                self.fd = open(self.lock_path, "w")
                fcntl.flock(self.fd, fcntl.LOCK_EX)
                return self

            def __exit__(self, *args):
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()

        return FileLock(self.stats_path)

    def _atomic_write(self, data: dict) -> None:
        """Atomic write: write to temp file, then rename."""
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(self.stats_path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(data, f, indent=2)
            os.rename(temp_path, str(self.stats_path))
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
