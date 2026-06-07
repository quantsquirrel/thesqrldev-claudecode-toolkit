"""Tests for prompt/prefix caching wiring (SYNOD_PROMPT_CACHE=1).

Covers:
- is_prompt_cache_enabled() honours the env flag (on/off/absent)
- build_cached_messages() puts stable prefix FIRST, dynamic suffix SECOND
- cache_control marker present iff flag is on
- build_single_turn_messages() never adds cache markers
- ClipProxyProvider.generate() passes cache-annotated messages when flag on
  and a stable_prefix kwarg is supplied
- ClipProxyProvider.generate() falls back to plain single-turn when flag off
- Request payload does not crash (shape-correct) when proxy ignores cache fields

Live-verification gap: whether these markers produce actual cache HIT/MISS
savings can only be confirmed against a live cache-supporting endpoint
(Anthropic Claude API or OpenAI with prompt caching enabled).  The tests here
verify request-shape correctness only.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module(filename: str):
    module_path = Path(__file__).parent.parent / "tools" / filename
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".py", ""), module_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def base_provider_module():
    return _load_module("base_provider.py")


@pytest.fixture()
def cliproxy_module():
    return _load_module("cliproxy-cli.py")


# ---------------------------------------------------------------------------
# is_prompt_cache_enabled
# ---------------------------------------------------------------------------


class TestIsPromptCacheEnabled:
    def test_disabled_by_default(self, monkeypatch, base_provider_module):
        monkeypatch.delenv("SYNOD_PROMPT_CACHE", raising=False)
        assert base_provider_module.is_prompt_cache_enabled() is False

    def test_disabled_when_zero(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "0")
        assert base_provider_module.is_prompt_cache_enabled() is False

    def test_enabled_when_one(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        assert base_provider_module.is_prompt_cache_enabled() is True

    def test_disabled_for_arbitrary_value(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "true")
        assert base_provider_module.is_prompt_cache_enabled() is False


# ---------------------------------------------------------------------------
# build_cached_messages — ordering and marker presence
# ---------------------------------------------------------------------------


class TestBuildCachedMessages:
    def test_stable_prefix_is_first_message(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        msgs = base_provider_module.build_cached_messages("STABLE", "DYNAMIC")
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_dynamic_suffix_is_last_message(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        msgs = base_provider_module.build_cached_messages("STABLE", "DYNAMIC")
        assert msgs[-1]["content"] == "DYNAMIC"

    def test_cache_control_marker_present_when_enabled(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        msgs = base_provider_module.build_cached_messages("STABLE", "DYNAMIC")
        prefix_content = msgs[0]["content"]
        # Anthropic-style: content is a list with a single block carrying cache_control
        assert isinstance(prefix_content, list), "prefix content should be a list when caching on"
        assert len(prefix_content) == 1
        block = prefix_content[0]
        assert block.get("type") == "text"
        assert block.get("text") == "STABLE"
        assert block.get("cache_control") == {"type": "ephemeral"}

    def test_cache_control_absent_when_disabled(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "0")
        msgs = base_provider_module.build_cached_messages("STABLE", "DYNAMIC")
        prefix_content = msgs[0]["content"]
        # Without caching the prefix is a plain string, no cache_control block
        assert isinstance(prefix_content, str), (
            "prefix content should be plain string when caching off"
        )
        assert prefix_content == "STABLE"

    def test_cache_control_absent_when_env_unset(self, monkeypatch, base_provider_module):
        monkeypatch.delenv("SYNOD_PROMPT_CACHE", raising=False)
        msgs = base_provider_module.build_cached_messages("big context", "round N")
        prefix_content = msgs[0]["content"]
        assert isinstance(prefix_content, str)

    def test_two_messages_always_returned(self, monkeypatch, base_provider_module):
        for flag in ("0", "1"):
            monkeypatch.setenv("SYNOD_PROMPT_CACHE", flag)
            msgs = base_provider_module.build_cached_messages("A", "B")
            assert len(msgs) == 2


# ---------------------------------------------------------------------------
# build_single_turn_messages — never adds cache markers
# ---------------------------------------------------------------------------


class TestBuildSingleTurnMessages:
    def test_single_user_message(self, base_provider_module):
        msgs = base_provider_module.build_single_turn_messages("hello")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hello"

    def test_no_cache_control_even_when_flag_on(self, monkeypatch, base_provider_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        msgs = base_provider_module.build_single_turn_messages("hello")
        content = msgs[0]["content"]
        assert isinstance(content, str)
        assert "cache_control" not in msgs[0]


# ---------------------------------------------------------------------------
# ClipProxyProvider.generate() — cache marker wiring
# ---------------------------------------------------------------------------


class TestClipProxyGenerateCaching:
    """Verify generate() passes cache-annotated messages when flag is on."""

    def _make_fake_client(self, calls: list):
        class FakeCompletions:
            def create(self_, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="response"))]
                )

        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    def test_cache_markers_in_payload_when_flag_on_and_prefix_given(
        self, monkeypatch, cliproxy_module
    ):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        result = provider.generate(
            client,
            "gpt-5.5-fast(xhigh)",
            "round instruction",
            stable_prefix="task + evidence + prior transcript",
        )

        assert result == "response"
        assert len(calls) == 1
        msgs = calls[0]["messages"]
        # system message first (stable prefix)
        assert msgs[0]["role"] == "system"
        prefix_content = msgs[0]["content"]
        assert isinstance(prefix_content, list)
        assert prefix_content[0].get("cache_control") == {"type": "ephemeral"}
        assert prefix_content[0].get("text") == "task + evidence + prior transcript"
        # user message last (dynamic suffix)
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "round instruction"

    def test_no_cache_markers_when_flag_off(self, monkeypatch, cliproxy_module):
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "0")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        provider.generate(
            client,
            "gpt-5.5-fast(xhigh)",
            "round instruction",
            stable_prefix="task + evidence + prior transcript",
        )

        msgs = calls[0]["messages"]
        # system message content should be plain string (no cache_control block)
        assert isinstance(msgs[0]["content"], str)

    def test_stable_prefix_retained_when_flag_off(self, monkeypatch, cliproxy_module):
        """Regression: cache disabled MUST still include the stable prefix as a
        plain system message (only the cache_control marker is dropped). The old
        code routed flag-off+prefix to single-turn and lost the prefix entirely."""
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "0")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        provider.generate(
            client,
            "gpt-5.5-fast(xhigh)",
            "round instruction",
            stable_prefix="task + evidence + prior transcript",
        )

        msgs = calls[0]["messages"]
        assert len(msgs) == 2, "prefix must survive as its own system message"
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "task + evidence + prior transcript"
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "round instruction"

    def test_no_cache_markers_when_flag_unset(self, monkeypatch, cliproxy_module):
        monkeypatch.delenv("SYNOD_PROMPT_CACHE", raising=False)
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        provider.generate(client, "gpt-5.5-fast(xhigh)", "hi")

        # single-turn path: one user message, plain string content
        msgs = calls[0]["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert isinstance(msgs[0]["content"], str)

    def test_no_stable_prefix_uses_single_turn_even_when_flag_on(
        self, monkeypatch, cliproxy_module
    ):
        """No stable_prefix kwarg → fallback to single-turn (no cache markers)."""
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        provider.generate(client, "gpt-5.5-fast(xhigh)", "standalone prompt")

        msgs = calls[0]["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert isinstance(msgs[0]["content"], str)

    def test_empty_stable_prefix_uses_single_turn(self, monkeypatch, cliproxy_module):
        """Empty stable_prefix → single-turn, no cache markers."""
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)

        provider.generate(client, "gpt-5.5-fast(xhigh)", "dynamic only", stable_prefix="")

        msgs = calls[0]["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_request_shape_valid_when_proxy_ignores_cache_fields(
        self, monkeypatch, cliproxy_module
    ):
        """A proxy that ignores cache_control should still return a valid response.

        Simulate a proxy that strips unknown keys silently — the request must
        not crash and must still return a usable response.
        """
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        provider = cliproxy_module.ClipProxyProvider()

        class ProxyThatIgnoresCacheFields:
            def create(self_, **kwargs):
                # A naive proxy strips unknown fields from message content blocks
                cleaned_msgs = []
                for msg in kwargs["messages"]:
                    content = msg["content"]
                    if isinstance(content, list):
                        # proxy ignores cache_control; returns plain text
                        content = " ".join(b.get("text", "") for b in content)
                    cleaned_msgs.append({"role": msg["role"], "content": content})
                # Responds normally
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="proxy ok"))]
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=ProxyThatIgnoresCacheFields()))

        result = provider.generate(
            client, "gpt-5.5-fast(xhigh)", "dynamic", stable_prefix="large stable context"
        )
        assert result == "proxy ok"

    def test_legacy_reasoning_flag_still_accepted_with_caching(self, monkeypatch, cliproxy_module):
        """Existing behaviour (reasoning kwarg accepted) is preserved with caching on."""
        monkeypatch.setenv("SYNOD_PROMPT_CACHE", "1")
        calls: list = []
        provider = cliproxy_module.ClipProxyProvider()
        client = self._make_fake_client(calls)
        args = SimpleNamespace(reasoning="high")

        result = provider.generate(
            client,
            "gpt-5.5-fast(xhigh)",
            "hi",
            args=args,
            stable_prefix="stable",
        )
        assert result == "response"
        # reasoning should NOT appear in the API payload
        assert "reasoning" not in calls[0]
        assert "reasoning_effort" not in calls[0]
