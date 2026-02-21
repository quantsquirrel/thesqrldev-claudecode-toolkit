#!/usr/bin/env python3
"""
Canary Pre-Sampling - lightweight probe to detect model health before full requests.

Subprocess-based implementation:
- Calls existing CLI tools (gemini-3.py, openai-cli.py, etc.) via subprocess
- Avoids import path issues and API interface mismatches
- CLI tool updates automatically benefit canary probes

Usage:
    from canary import CanaryProbe
    from model_stats import ModelStats

    probe = CanaryProbe(ModelStats())
    result = probe.probe("gemini", "flash")
    if result["fallback_recommended"]:
        # Use fallback model
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Import path setup (for ModelStats only)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_stats import ModelStats

CANARY_PROMPT = "Reply with exactly one word: 'ready'"
CANARY_TIMEOUT_SECONDS = 30  # Hard timeout for canary probes
CACHE_TTL_SECONDS = 300  # 5 minutes

# CLI tool mapping (provider -> CLI filename)
CLI_MAP = {
    "gemini": "gemini-3.py",
    "openai": "openai-cli.py",
    "deepseek": "deepseek-cli.py",
    "groq": "groq-cli.py",
    "grok": "grok-cli.py",
    "mistral": "mistral-cli.py",
    "openrouter": "openrouter-cli.py",
}

# Provider-specific lightweight models for canary probes
CANARY_MODEL_MAP = {
    "gemini": "flash",
    "openai": "gpt4o",
    "deepseek": "chat",
    "groq": "8b",
    "grok": "fast",
    "mistral": "small",
    "openrouter": "claude",
}


class CanaryCache:
    """File-based cache for canary results with 5-minute TTL."""

    def __init__(self, cache_path: str = "~/.synod/canary-cache.json"):
        self.cache_path = Path(cache_path).expanduser()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def get(self, provider: str, model: str) -> dict | None:
        """Get cached result if valid (within TTL)."""
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path) as f:
                cache = json.load(f)

            key = f"{provider}:{model}"
            if key not in cache:
                return None

            entry = cache[key]
            cached_time = datetime.fromisoformat(entry["timestamp"])
            if datetime.now() - cached_time > timedelta(seconds=CACHE_TTL_SECONDS):
                return None  # Expired

            return entry["result"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def set(self, provider: str, model: str, result: dict) -> None:
        """Cache a canary result."""
        cache = {}
        if self.cache_path.exists():
            try:
                with open(self.cache_path) as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}

        key = f"{provider}:{model}"
        cache[key] = {
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }

        with open(self.cache_path, "w") as f:
            json.dump(cache, f, indent=2)


class CanaryProbe:
    """
    Canary probe using subprocess to call existing CLI tools.

    This approach avoids:
    - Python import issues with hyphenated filenames (gemini-3.py)
    - create_client signature mismatches between providers
    - Different API interfaces (generate_content vs chat.completions.create)
    """

    def __init__(self, stats: ModelStats, use_cache: bool = True):
        self.stats = stats
        self.cache = CanaryCache() if use_cache else None
        self.tools_dir = Path(__file__).parent

    def _get_cli_path(self, provider: str) -> Path:
        """Get the CLI tool path for a provider."""
        if provider not in CLI_MAP:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(CLI_MAP.keys())}")
        return self.tools_dir / CLI_MAP[provider]

    def _probe_via_subprocess(self, provider: str, model: str) -> dict:
        """
        Execute canary probe via subprocess to existing CLI tool.

        Returns:
            dict with healthy, latency_ms, error (if any)
        """
        cli_path = self._get_cli_path(provider)

        if not cli_path.exists():
            return {
                "healthy": False,
                "latency_ms": 0,
                "error": f"CLI tool not found: {cli_path}",
                "fallback_recommended": True,
            }

        # Use canary-specific lightweight model if no model specified
        effective_model = model or CANARY_MODEL_MAP.get(provider, "default")

        start = time.time()
        try:
            result = subprocess.run(
                [
                    "python3",
                    str(cli_path),
                    "--model",
                    effective_model,
                    CANARY_PROMPT,
                ],
                capture_output=True,
                text=True,
                timeout=CANARY_TIMEOUT_SECONDS,
            )
            latency_ms = (time.time() - start) * 1000

            if result.returncode == 0:
                return {
                    "healthy": True,
                    "latency_ms": latency_ms,
                    "response_preview": result.stdout[:100] if result.stdout else None,
                }
            else:
                return {
                    "healthy": False,
                    "latency_ms": latency_ms,
                    "error": result.stderr[:200] if result.stderr else f"Exit code: {result.returncode}",
                    "fallback_recommended": True,
                }

        except subprocess.TimeoutExpired:
            latency_ms = (time.time() - start) * 1000
            return {
                "healthy": False,
                "latency_ms": latency_ms,
                "error": f"Timeout after {CANARY_TIMEOUT_SECONDS}s",
                "fallback_recommended": True,
            }
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return {
                "healthy": False,
                "latency_ms": latency_ms,
                "error": str(e),
                "fallback_recommended": True,
            }

    def probe(self, provider: str, model: str = None) -> dict:
        """
        Execute canary probe and return status.
        Uses cache if available and valid.

        Args:
            provider: Provider name (gemini, openai, etc.)
            model: Model name (optional, uses canary default if not specified)

        Returns:
            {
                "healthy": bool,
                "latency_ms": float,
                "exceeded_p95": bool,
                "fallback_recommended": bool,
                "cached": bool
            }
        """
        effective_model = model or CANARY_MODEL_MAP.get(provider, "default")

        # Check cache first
        if self.cache:
            cached = self.cache.get(provider, effective_model)
            if cached:
                cached["cached"] = True
                return cached

        # Execute probe via subprocess
        result = self._probe_via_subprocess(provider, effective_model)
        result["cached"] = False

        # Check against P95 threshold
        if result["healthy"]:
            p95 = self.stats.get_percentile(provider, effective_model, 95)
            exceeded = result["latency_ms"] > p95 if p95 else False
            result["exceeded_p95"] = exceeded
            result["fallback_recommended"] = exceeded
        else:
            result["exceeded_p95"] = False
            # fallback_recommended already set in _probe_via_subprocess

        # Cache the result
        if self.cache:
            self.cache.set(provider, effective_model, result)

        return result
