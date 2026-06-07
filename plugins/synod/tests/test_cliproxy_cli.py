"""Tests for cliproxy-cli.py - CLIProxyAPI OpenAI-compatible client."""

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace


def load_cli_module(filename: str):
    module_path = Path(__file__).parent.parent / "tools" / filename
    spec = importlib.util.spec_from_file_location("cliproxy_cli", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestClipProxyProvider:
    def test_model_map_routes_synod_defaults_to_cliproxy_aliases(self):
        cliproxy = load_cli_module("cliproxy-cli.py")

        assert cliproxy.ClipProxyProvider.DEFAULT_MODEL == "gpt55fast"
        assert cliproxy.ClipProxyProvider.MODEL_MAP["gpt55fast"] == "gpt-5.5-fast(xhigh)"
        assert cliproxy.ClipProxyProvider.MODEL_MAP["gpt55"] == "gpt-5.5(xhigh)"
        assert cliproxy.ClipProxyProvider.MODEL_MAP["gpt54mini"] == "gpt-5.4-mini"

    def test_legacy_openai_aliases_map_to_cliproxy_defaults(self):
        cliproxy = load_cli_module("cliproxy-cli.py")

        assert cliproxy.ClipProxyProvider.MODEL_MAP["o3"] == "gpt-5.5-fast(xhigh)"
        assert cliproxy.ClipProxyProvider.MODEL_MAP["gpt4o"] == "gpt-5.5-fast(xhigh)"

    def test_timeout_defaults_are_model_specific(self):
        cliproxy = load_cli_module("cliproxy-cli.py")
        provider = cliproxy.ClipProxyProvider()
        args = SimpleNamespace(timeout=None)

        assert provider.get_timeout_ms(args, "gpt55fast") == 120_000
        assert provider.get_timeout_ms(args, "gpt54mini") == 90_000

    def test_env_override_uses_cliproxy_provider_namespace(self, monkeypatch):
        cliproxy = load_cli_module("cliproxy-cli.py")
        provider = cliproxy.ClipProxyProvider()
        monkeypatch.setenv("SYNOD_CLIPROXY_GPT55FAST", "custom-proxy-model")

        assert provider.get_model_with_override("gpt55fast") == "custom-proxy-model"

    def test_reasoning_flag_is_accepted_but_not_sent_to_proxy(self):
        cliproxy = load_cli_module("cliproxy-cli.py")
        provider = cliproxy.ClipProxyProvider()
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="ok"),
                        )
                    ]
                )

        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        args = SimpleNamespace(reasoning="high")

        assert provider.generate(fake_client, "gpt-5.5-fast(xhigh)", "hi", args=args) == "ok"
        assert calls == [
            {
                "model": "gpt-5.5-fast(xhigh)",
                "messages": [{"role": "user", "content": "hi"}],
            }
        ]

    def test_config_api_key_is_loaded_from_local_cliproxy_yaml(self, monkeypatch, tmp_path):
        cliproxy = load_cli_module("cliproxy-cli.py")
        cfg = tmp_path / "config.yaml"
        cfg.write_text('api-keys:\n  - "local-test-token"\n')
        monkeypatch.setenv("CLIPROXY_CONFIG", str(cfg))

        assert cliproxy._load_config_api_key() == "local-test-token"

    def test_cliproxy_base_url_defaults_to_localhost(self):
        cliproxy = load_cli_module("cliproxy-cli.py")

        assert os.environ.get("CLIPROXY_BASE_URL") or cliproxy._BASE_URL == (
            "http://127.0.0.1:8317/v1"
        )
