"""Phase 4 collapsible must instruct branded per-model claim rendering.

Verifies that the orchestrator-side instruction text in
`skills/synod/modules/synod-phase4-synthesis.md` references:

1. The PRIMARY claim extraction protocol (`semantic_focus[0]`).
2. The unicode brand-shape glyphs from `tools/model_branding.markdown_marker(...)`
   on the correct model rows.
3. The hex codes from `tools/model_branding.py.BRANDING` so that the
   markdown layer and the HUD layer cite the same single source of truth.

This is a documentation-as-test: it does NOT generate the markdown itself
(that work is done by the orchestrator at runtime), it just guards the
instruction template against drift.
"""

import os
import sys

PHASE4_MODULE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "synod",
    "modules",
    "synod-phase4-synthesis.md",
)


def _phase4_text() -> str:
    with open(PHASE4_MODULE, encoding="utf-8") as f:
        return f.read()


class TestPhase4Instructions:
    def test_per_agent_claim_extraction_protocol_is_documented(self):
        body = _phase4_text()
        assert "semantic_focus[0]" in body
        assert "round-1-solver" in body
        assert "no primary claim extracted" in body
        assert "120 character" in body  # truncation rule

    def test_branded_model_rows_use_brand_glyph(self):
        body = _phase4_text()
        assert "✻ **Claude (Validator):**" in body
        assert "✦ **Gemini (Architect):**" in body
        assert "❀ **OpenAI (Explorer):**" in body

    def test_three_brand_hex_codes_are_cited(self):
        body = _phase4_text()
        assert "#D97757" in body
        assert "#4285F4" in body
        assert "#10A37F" in body


class TestBrandingConsistency:
    """Phase 4 markdown must agree with tools/model_branding.py."""

    def test_phase4_uses_markdown_marker_for_each_model(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
        import model_branding

        body = _phase4_text()
        for key in ("claude", "gemini", "openai"):
            marker = model_branding.markdown_marker(key)
            assert marker in body, (
                f"{key} marker {marker!r} missing from phase4 module — branding drift"
            )

    def test_phase4_uses_branding_module_hex_codes(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
        import model_branding

        body = _phase4_text()
        for key in ("claude", "gemini", "openai"):
            hex_code = model_branding.BRANDING[key]["hex"]
            assert hex_code in body, (
                f"{key} hex {hex_code} missing from phase4 module — branding drift"
            )
