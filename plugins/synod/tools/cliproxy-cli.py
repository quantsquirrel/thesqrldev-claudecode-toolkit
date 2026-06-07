#!/usr/bin/env python3
"""
CLIProxyAPI CLI - routes Synod's OpenAI lane to local CLIProxyAPI.

The local proxy exposes an OpenAI-compatible API on port 8317 and bridges the
user's ChatGPT Pro OAuth session. Reasoning effort is encoded in the model alias
that CLIProxyAPI accepts, so Synod's historical --reasoning flag is accepted for
compatibility but intentionally ignored.

Usage:
  echo "prompt" | cliproxy-cli [--model MODEL]
  cliproxy-cli "prompt" [--model MODEL]
  cliproxy-cli --prompt "question" --model gpt55fast

Models:
  gpt55fast -> gpt-5.5-fast(xhigh)  priority tier + xhigh reasoning
  gpt55     -> gpt-5.5(xhigh)       standard + xhigh reasoning
  gpt55high -> gpt-5.5(high)        standard + high reasoning
  gpt54     -> gpt-5.4
  gpt54mini -> gpt-5.4-mini
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import httpx
    from openai import OpenAI
except ImportError:
    sys.stderr.write("Error: openai 패키지가 설치되지 않았습니다.\n")
    sys.stderr.write("설치: pip install openai httpx\n")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_provider import (  # noqa: E402
    BaseProvider,
    build_cached_messages,
    build_single_turn_messages,
    load_synod_env,
    resolve_api_key,
)

_BASE_URL = os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1")


def _load_config_api_key() -> str:
    """Read the first local CLIProxyAPI key from config.yaml when available."""
    candidates = [
        os.environ.get("CLIPROXY_CONFIG"),
        str(Path.home() / "CLIProxyAPI" / "config.yaml"),
    ]
    for raw_path in candidates:
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.exists():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        match = re.search(r"api-keys:\s*(?:\n\s*-\s*[\"']?([^\"'\s#]+))", text)
        if match:
            return match.group(1).strip()
    return ""


class ClipProxyProvider(BaseProvider):
    """CLIProxyAPI provider — ChatGPT OAuth via local OpenAI-compatible proxy."""

    PROVIDER = "cliproxy"
    API_KEY_ENV = "CLIPROXY_API_KEY"

    MODEL_MAP = {
        "gpt55fast": "gpt-5.5-fast(xhigh)",
        "gpt55": "gpt-5.5(xhigh)",
        "gpt55high": "gpt-5.5(high)",
        "gpt54": "gpt-5.4",
        "gpt54mini": "gpt-5.4-mini",
        # Legacy compatibility: old Synod config may still pass these aliases.
        "o3": "gpt-5.5-fast(xhigh)",
        "gpt4o": "gpt-5.5-fast(xhigh)",
        "gpt5mini": "gpt-5.4-mini",
    }
    DEFAULT_MODEL = "gpt55fast"

    TIMEOUT_CONFIG = {
        "gpt55fast": 120,
        "gpt55": 150,
        "gpt55high": 150,
        "gpt54": 120,
        "gpt54mini": 90,
        "o3": 120,
        "gpt4o": 120,
        "gpt5mini": 90,
    }

    def get_timeout_ms(self, args, model_key: str, default_ms: int = 300_000) -> int:
        configured = self.TIMEOUT_CONFIG.get(model_key)
        if configured is not None:
            default_ms = configured * 1000
        return super().get_timeout_ms(args, model_key, default_ms=default_ms)

    def validate_api_key(self) -> str:
        """Use CLIPROXY_API_KEY when set; otherwise use the local proxy key."""
        load_synod_env()
        key = resolve_api_key(self.API_KEY_ENV) or resolve_api_key("CLI_PROXY_API_KEY")
        key = key or _load_config_api_key()
        if key:
            return key.strip()
        print(
            "Error: CLIPROXY_API_KEY not found and ~/CLIProxyAPI/config.yaml has no api-keys entry.",
            file=sys.stderr,
        )
        sys.exit(1)

    def create_client(self, timeout_ms: int):
        api_key = self.validate_api_key()
        timeout_sec = timeout_ms / 1000
        return OpenAI(
            api_key=api_key,
            base_url=_BASE_URL,
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
        )

    def generate(self, client, model: str, prompt: str, **kwargs) -> str:
        """Send prompt to CLIProxyAPI and return the text response.

        When SYNOD_PROMPT_CACHE=1 and the caller supplies a ``stable_prefix``
        kwarg the request payload will include an Anthropic-style
        ``cache_control`` marker on the stable-prefix block so that
        cache-supporting endpoints can skip recomputing it on every round.
        The local CLIProxyAPI proxy ignores unknown message fields, so the
        request shape is safe regardless of whether the proxy supports caching.

        Prompt-ordering rule (cache-friendly):
          1. stable_prefix  — large, slow-changing context (task + evidence + transcript)
          2. prompt         — small, per-round dynamic instruction / user turn
        """
        stable_prefix = kwargs.get("stable_prefix", "")
        if stable_prefix:
            # build_cached_messages keeps the stable prefix in ALL cases — it
            # only adds the cache_control marker when SYNOD_PROMPT_CACHE=1, and
            # emits the same prefix as a plain system message when caching is
            # disabled. Gating on is_prompt_cache_enabled() here previously
            # dropped the prefix entirely under SYNOD_PROMPT_CACHE=0, violating
            # the base_provider contract ("identical content, minus the marker").
            messages = build_cached_messages(stable_prefix, prompt)
        else:
            messages = build_single_turn_messages(prompt)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        raise Exception("Empty response")

    def add_provider_args(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--model",
            "-m",
            choices=list(self.MODEL_MAP.keys()),
            default=self.DEFAULT_MODEL,
            help="모델 alias (기본값: gpt55fast = gpt-5.5-fast priority+xhigh)",
        )
        parser.add_argument(
            "--reasoning",
            "-r",
            choices=["low", "medium", "high"],
            default=None,
            help="무시됨 — 추론 강도는 모델 alias에 포함됨 (Synod 호환성용)",
        )


if __name__ == "__main__":
    ClipProxyProvider().run()
