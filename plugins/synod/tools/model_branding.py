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
