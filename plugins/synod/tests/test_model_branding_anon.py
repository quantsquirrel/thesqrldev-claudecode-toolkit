"""Tests for deliberation anonymization helpers in tools/model_branding.py.

Covers:
- build_anon_map: deterministic, bijective, stable ordering
- anonymize_label: single-model alias
- deanonymize: round-trip fidelity
- alias purity: no provider substrings leak into aliases
- flag-off semantics documented (no runtime side-effect when SYNOD_ANONYMIZE unset)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import model_branding  # noqa: E402

# ---------------------------------------------------------------------------
# Provider substrings that must NOT appear in any alias
# ---------------------------------------------------------------------------
_PROVIDER_SUBSTRINGS = [
    "gemini",
    "openai",
    "gpt",
    "claude",
    "anthropic",
    "google",
    "microsoft",
    "mistral",
    "deepseek",
    "groq",
    "grok",
    "llama",
    "meta",
    "cohere",
    "command",
    "perplexity",
    "together",
]

# Canonical three-model roster used across multiple tests
ROSTER = ["gemini", "openai", "claude"]


class TestBuildAnonMap:
    def test_returns_dict(self):
        result = model_branding.build_anon_map(ROSTER)
        assert isinstance(result, dict)

    def test_all_models_present(self):
        result = model_branding.build_anon_map(ROSTER)
        assert set(result.keys()) == set(ROSTER)

    def test_deterministic_regardless_of_input_order(self):
        """Same aliases no matter how the list is ordered."""
        order_a = model_branding.build_anon_map(["gemini", "openai", "claude"])
        order_b = model_branding.build_anon_map(["claude", "gemini", "openai"])
        order_c = model_branding.build_anon_map(["openai", "claude", "gemini"])
        assert order_a == order_b == order_c

    def test_alphabetical_assignment(self):
        """Aliases are assigned A-Z alphabetically on the lowercased key."""
        result = model_branding.build_anon_map(["gemini", "openai", "claude"])
        # Alphabetical: claude < gemini < openai
        assert result["claude"] == "Agent-1"
        assert result["gemini"] == "Agent-2"
        assert result["openai"] == "Agent-3"

    def test_bijective_no_duplicate_aliases(self):
        """Every model gets a unique alias (bijective mapping)."""
        result = model_branding.build_anon_map(ROSTER)
        aliases = list(result.values())
        assert len(aliases) == len(set(aliases)), "duplicate aliases found"

    def test_aliases_contain_no_provider_substrings(self):
        """Aliases must not leak any provider/model name."""
        result = model_branding.build_anon_map(ROSTER)
        for alias in result.values():
            alias_lower = alias.lower()
            for substr in _PROVIDER_SUBSTRINGS:
                assert substr not in alias_lower, (
                    f"alias '{alias}' contains provider substring '{substr}'"
                )

    def test_single_model_roster(self):
        result = model_branding.build_anon_map(["claude"])
        assert result == {"claude": "Agent-1"}

    def test_case_insensitive_deduplication(self):
        """'GEMINI' and 'gemini' are the same model — only one alias issued."""
        result = model_branding.build_anon_map(["GEMINI", "gemini"])
        assert len(result) == 1

    def test_preserves_original_case_as_key(self):
        """Keys in the returned map use the original (first-seen) casing."""
        result = model_branding.build_anon_map(["Gemini", "OpenAI"])
        assert "Gemini" in result
        assert "OpenAI" in result

    def test_large_roster_sequential_aliases(self):
        models = ["alpha", "beta", "gamma", "delta", "epsilon"]
        result = model_branding.build_anon_map(models)
        assert len(result) == 5
        for i, key in enumerate(sorted(result.keys()), start=1):
            assert result[key] == f"Agent-{i}"

    def test_empty_roster_returns_empty(self):
        assert model_branding.build_anon_map([]) == {}


class TestAnonymizeLabel:
    def test_returns_string(self):
        alias = model_branding.anonymize_label("claude")
        assert isinstance(alias, str)

    def test_alias_contains_no_provider_substrings(self):
        alias = model_branding.anonymize_label("openai")
        alias_lower = alias.lower()
        for substr in _PROVIDER_SUBSTRINGS:
            assert substr not in alias_lower

    def test_single_model_is_agent_1(self):
        assert model_branding.anonymize_label("claude") == "Agent-1"


class TestDeanonymize:
    def test_round_trip_three_models(self):
        """anonymize then deanonymize must recover original model names."""
        anon_map = model_branding.build_anon_map(ROSTER)
        # Build a text that contains all three aliases
        text = "Agent-1 proposed X. Agent-2 disagreed. Agent-3 abstained."
        restored = model_branding.deanonymize(text, anon_map)
        # Each real model name must appear; no alias may remain
        for real in ROSTER:
            assert real in restored, f"'{real}' missing after deanonymize"
        for alias in anon_map.values():
            assert alias not in restored, f"alias '{alias}' still present after deanonymize"

    def test_round_trip_preserves_surrounding_text(self):
        anon_map = model_branding.build_anon_map(["gemini", "claude"])
        text = "Summary: Agent-1 said A; Agent-2 said B. End."
        restored = model_branding.deanonymize(text, anon_map)
        assert restored.startswith("Summary: ")
        assert restored.endswith(" End.")

    def test_no_alias_in_text_returns_unchanged(self):
        anon_map = model_branding.build_anon_map(ROSTER)
        text = "No aliases here, just plain text."
        assert model_branding.deanonymize(text, anon_map) == text

    def test_empty_text(self):
        anon_map = model_branding.build_anon_map(ROSTER)
        assert model_branding.deanonymize("", anon_map) == ""

    def test_empty_map_returns_unchanged(self):
        text = "Agent-1 and Agent-2"
        assert model_branding.deanonymize(text, {}) == text

    def test_longer_aliases_do_not_corrupt_shorter(self):
        """Agent-10 must not be partially replaced as Agent-1 + '0'."""
        models = [f"model{i:02d}" for i in range(1, 12)]  # 11 models
        anon_map = model_branding.build_anon_map(models)
        # All aliases present: Agent-1 through Agent-11
        text = " ".join(anon_map.values())
        restored = model_branding.deanonymize(text, anon_map)
        for real in models:
            assert real in restored, f"'{real}' missing"

    def test_multiple_occurrences_of_same_alias(self):
        anon_map = model_branding.build_anon_map(["claude", "gemini"])
        alias_claude = anon_map["claude"]
        text = f"{alias_claude} said X. Later, {alias_claude} said Y."
        restored = model_branding.deanonymize(text, anon_map)
        assert restored.count("claude") == 2

    def test_inverse_of_build_anon_map(self):
        """build_anon_map + deanonymize is a true round-trip for each value."""
        anon_map = model_branding.build_anon_map(ROSTER)
        for real, alias in anon_map.items():
            recovered = model_branding.deanonymize(alias, anon_map)
            assert recovered == real


class TestAliasPurity:
    """All aliases produced by either helper must be provider-clean."""

    def test_no_provider_substring_in_any_alias_diverse_roster(self):
        diverse = [
            "claude-3-5-sonnet",
            "gemini-2.0-flash",
            "gpt-4o",
            "gpt-5",
            "o3-mini",
            "deepseek-r1",
            "mistral-large",
            "llama-3.3-70b",
        ]
        anon_map = model_branding.build_anon_map(diverse)
        for alias in anon_map.values():
            alias_lower = alias.lower()
            for substr in _PROVIDER_SUBSTRINGS:
                assert substr not in alias_lower, (
                    f"alias '{alias}' leaks provider substring '{substr}'"
                )


class TestFlagOffSemantics:
    """Document that when SYNOD_ANONYMIZE is unset / '0' the helpers are
    importable but the phase modules are instructed to skip them — no
    existing BRANDING behavior is altered."""

    def test_existing_branding_dict_unchanged(self):
        """Adding anonymization helpers must not mutate BRANDING."""
        assert "claude" in model_branding.BRANDING
        assert "gemini" in model_branding.BRANDING
        assert "openai" in model_branding.BRANDING
        assert len(model_branding.BRANDING) == 3

    def test_get_function_unchanged(self):
        assert model_branding.get("claude")["hex"] == "#D97757"
        assert model_branding.get("gemini")["hex"] == "#4285F4"
        assert model_branding.get("openai")["hex"] == "#10A37F"

    def test_markdown_marker_unchanged(self):
        assert model_branding.markdown_marker("claude") == "✻"
        assert model_branding.markdown_marker("gemini") == "✦"
        assert model_branding.markdown_marker("openai") == "❀"

    def test_anon_helpers_importable_without_env_flag(self):
        """Helpers exist regardless of SYNOD_ANONYMIZE value."""
        # Ensure the env var is unset for this test
        env_before = os.environ.pop("SYNOD_ANONYMIZE", None)
        try:
            assert callable(model_branding.build_anon_map)
            assert callable(model_branding.anonymize_label)
            assert callable(model_branding.deanonymize)
        finally:
            if env_before is not None:
                os.environ["SYNOD_ANONYMIZE"] = env_before

    def test_build_anon_map_with_flag_off_still_works(self):
        """build_anon_map is a pure function; it runs correctly regardless of
        the SYNOD_ANONYMIZE env flag.  The flag governs whether the phase
        modules *call* it, not whether it functions correctly."""
        os.environ["SYNOD_ANONYMIZE"] = "0"
        try:
            result = model_branding.build_anon_map(["gemini", "claude"])
            assert len(result) == 2
        finally:
            del os.environ["SYNOD_ANONYMIZE"]
