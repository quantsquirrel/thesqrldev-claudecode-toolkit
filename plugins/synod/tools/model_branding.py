"""Single source of truth for synod model branding.

Each AI provider has a brand color used to visually distinguish its output
in the Rich-based HUD, plus a unicode glyph used as the marker in
markdown surfaces. Both the HUD (`tools/synod_progress.py`) and the
Phase 4 markdown layer source from this module so the two surfaces
cannot drift.

Markdown rendering note: Claude Code's markdown renderer does not apply
HTML inline color or data-URI SVG, so the markdown marker is a
monochrome unicode glyph chosen to visually echo each provider's brand
shape:

- Claude → ✻ (HEAVY EIGHT TEARDROP-SPOKED ASTERISK, U+273B) — Anthropic asterisk
- Gemini → ✦ (BLACK FOUR POINTED STAR, U+2726) — Gemini sparkle
- OpenAI → ❀ (BLACK FLORETTE, U+2740) — OpenAI knot motif

Hex sources (verified 2026-05):
- claude — claude.ai logo SVG fill
- gemini — Google Design Library, dominant of brand gradient
- openai — openai.com / platform.openai.com signature teal-green
"""

from __future__ import annotations

BRANDING: dict[str, dict[str, str]] = {
    "claude": {
        "label": "Claude",
        "hex": "#D97757",  # warm coral
        "rich": "orange3",  # Rich named-color when truecolor unavailable
        "glyph": "✻",  # U+273B
    },
    "gemini": {
        "label": "Gemini",
        "hex": "#4285F4",  # Google Blue
        "rich": "blue",
        "glyph": "✦",  # U+2726
    },
    "openai": {
        "label": "OpenAI",
        "hex": "#10A37F",  # signature teal-green
        "rich": "green",
        "glyph": "❀",  # U+2740
    },
}


def get(model: str) -> dict[str, str]:
    """Return the branding dict for a model key. Case-insensitive.

    Raises KeyError for unknown models — callers pass one of the three
    keys in BRANDING; an unknown key signals a real bug, not a rendering
    edge case.
    """
    return BRANDING[model.lower()]


def markdown_marker(model: str) -> str:
    """Return the monochrome unicode glyph used as the marker for `model`
    in markdown surfaces.

    Claude Code's markdown renderer strips HTML inline color and does not
    inline data-URI SVG, so the marker is glyph-shape only. The HUD
    surface (`tools/synod_progress.py`) carries the actual color via
    Rich.
    """
    return get(model)["glyph"]


# ---------------------------------------------------------------------------
# Deliberation anonymization (arXiv:2510.07517)
#
# During Phases 1-3, model/provider identity cues drive sycophantic
# premature consensus.  When SYNOD_ANONYMIZE=1 these helpers replace real
# model names with neutral aliases so the court never sees which provider
# authored which claim.  Phase 4 calls deanonymize() before rendering the
# branded per-model summary so the user still sees real model names.
#
# Feature-flagged OFF by default (SYNOD_ANONYMIZE env var unset / "0").
# When the flag is off all three helpers are still importable but the
# phase modules are instructed to skip them — no existing behavior changes.
# ---------------------------------------------------------------------------

# Neutral alias prefix used for all anonymous labels.
_ALIAS_PREFIX = "Agent-"

# Deterministic ordering: alphabetical on the normalised model key so the
# mapping never depends on call order, Python dict insertion order, or
# runtime state.
_PROVIDER_SUBSTRINGS = (
    "claude",
    "gemini",
    "openai",
    "gpt",
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
)


def anonymize_label(model: str) -> str:
    """Return the neutral alias for a single model string.

    The alias is derived by looking the model up in the canonical sorted
    position of its lowercase form within a singleton roster built from
    ``build_anon_map``.  For a single-model call the alias is always
    ``Agent-1``.  Prefer ``build_anon_map`` when you have the full roster
    so relative ordering is stable.

    Examples::

        anonymize_label("claude")  -> "Agent-1"
        anonymize_label("GEMINI")  -> "Agent-1"  # single-model call
    """
    return _ALIAS_PREFIX + "1"


def build_anon_map(models: list[str]) -> dict[str, str]:
    """Return a stable real->alias mapping for the given model roster.

    Rules
    -----
    * Aliases are ``Agent-1``, ``Agent-2``, … assigned in *ascending
      alphabetical order* of the lowercased model key.  This makes the
      mapping deterministic regardless of the order ``models`` is passed.
    * Duplicate entries (after lowercasing) are collapsed: each unique
      model gets exactly one alias.
    * The map is bijective: no two models share an alias.

    Parameters
    ----------
    models:
        Iterable of model keys, e.g. ``["gemini", "openai", "claude"]``.

    Returns
    -------
    dict mapping each original key (preserved case) to its neutral alias.

    Examples::

        build_anon_map(["gemini", "openai", "claude"])
        # -> {"claude": "Agent-1", "gemini": "Agent-2", "openai": "Agent-3"}
    """
    # Deduplicate while preserving a canonical (lowercased) key for sorting.
    seen: dict[str, str] = {}  # lower -> first-seen original
    for m in models:
        lower = m.lower()
        if lower not in seen:
            seen[lower] = m

    # Sort by lowercased key to get a deterministic, order-independent result.
    sorted_lowers = sorted(seen.keys())

    result: dict[str, str] = {}
    for idx, lower in enumerate(sorted_lowers, start=1):
        original = seen[lower]
        result[original] = _ALIAS_PREFIX + str(idx)

    return result


def deanonymize(text: str, anon_map: dict[str, str]) -> str:
    """Replace neutral aliases in *text* with their real model names.

    This is the inverse of ``build_anon_map``.  It is called in Phase 4
    before rendering the branded per-model claim summary so the user sees
    real provider names after the anonymous deliberation phases.

    Parameters
    ----------
    text:
        Arbitrary string that may contain alias tokens like ``Agent-1``.
    anon_map:
        The ``real -> alias`` dict returned by ``build_anon_map``.

    Returns
    -------
    A new string with every alias occurrence replaced by its real model name.
    Aliases that do not appear in the text are silently ignored.
    """
    # Build the reverse map: alias -> real.
    reverse: dict[str, str] = {alias: real for real, alias in anon_map.items()}

    result = text
    # Sort by alias length descending so longer tokens match before shorter
    # prefixes (e.g. "Agent-10" before "Agent-1").
    for alias in sorted(reverse.keys(), key=len, reverse=True):
        result = result.replace(alias, reverse[alias])

    return result
