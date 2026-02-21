"""
Tests for synod-parser.py - SID signal extraction and parsing.
"""

import json
import os
import pytest
import sys

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

# Import after path modification
import importlib.util

spec = importlib.util.spec_from_file_location(
    "synod_parser", os.path.join(os.path.dirname(__file__), "..", "tools", "synod-parser.py")
)
synod_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(synod_parser)


class TestValidateFormat:
    """Tests for validate_format() function."""

    def test_valid_format(self, sample_valid_response):
        """Test validation with complete valid format."""
        result = synod_parser.validate_format(sample_valid_response)
        assert result["has_confidence"] is True
        assert result["has_score"] is True
        assert result["has_semantic_focus"] is True
        assert result["is_valid"] is True

    def test_missing_confidence(self):
        """Test validation with missing confidence tag."""
        text = "<semantic_focus>Focus here</semantic_focus>"
        result = synod_parser.validate_format(text)
        assert result["has_confidence"] is False
        assert result["has_semantic_focus"] is True
        assert result["is_valid"] is False

    def test_missing_semantic_focus(self, sample_partial_response):
        """Test validation with missing semantic_focus tag."""
        result = synod_parser.validate_format(sample_partial_response)
        assert result["has_confidence"] is True
        assert result["has_semantic_focus"] is False
        assert result["is_valid"] is False

    def test_completely_invalid(self, sample_invalid_response):
        """Test validation with plain text response."""
        result = synod_parser.validate_format(sample_invalid_response)
        assert result["has_confidence"] is False
        assert result["has_score"] is False
        assert result["has_semantic_focus"] is False
        assert result["is_valid"] is False


class TestExtractConfidence:
    """Tests for extract_confidence() function."""

    def test_extract_full_confidence(self, sample_valid_response):
        """Test extracting complete confidence block."""
        result = synod_parser.extract_confidence(sample_valid_response)
        assert result is not None
        assert result["score"] == 85
        assert "empirical data" in result["evidence"]
        assert "reasoning follows" in result["logic"]
        assert "domain knowledge" in result["expertise"]
        assert result["can_exit"] is True

    def test_extract_minimal_confidence(self):
        """Test extracting confidence with only score."""
        text = '<confidence score="60"></confidence>'
        result = synod_parser.extract_confidence(text)
        assert result is not None
        assert result["score"] == 60
        assert result["evidence"] is None
        assert result["logic"] is None
        assert result["expertise"] is None
        assert result["can_exit"] is False

    def test_extract_can_exit_false(self):
        """Test can_exit with false value."""
        text = '<confidence score="50"><can_exit>false</can_exit></confidence>'
        result = synod_parser.extract_confidence(text)
        assert result is not None
        assert result["can_exit"] is False

    def test_no_confidence_tag(self, sample_invalid_response):
        """Test extraction when confidence tag is missing."""
        result = synod_parser.extract_confidence(sample_invalid_response)
        assert result is None

    def test_multiline_content(self):
        """Test extraction with multiline content in tags."""
        text = """
        <confidence score="75">
            <evidence>
                Line 1 of evidence
                Line 2 of evidence
            </evidence>
            <logic>Multiline
            logic here</logic>
        </confidence>
        """
        result = synod_parser.extract_confidence(text)
        assert result is not None
        assert result["score"] == 75
        assert "Line 1" in result["evidence"]
        assert "Line 2" in result["evidence"]
        assert "Multiline" in result["logic"]


class TestExtractSemanticFocus:
    """Tests for extract_semantic_focus() function."""

    def test_extract_numbered_list(self, sample_valid_response):
        """Test extracting numbered semantic focus points."""
        result = synod_parser.extract_semantic_focus(sample_valid_response)
        assert len(result) == 3
        assert "Primary focus point" in result[0]
        assert "Secondary consideration" in result[1]
        assert "Tertiary aspect" in result[2]

    def test_extract_plain_lines(self):
        """Test extracting plain line-separated focus points."""
        text = """
        <semantic_focus>
        First point
        Second point
        Third point
        </semantic_focus>
        """
        result = synod_parser.extract_semantic_focus(text)
        assert len(result) >= 3
        assert any("First point" in item for item in result)

    def test_no_semantic_focus_tag(self, sample_invalid_response):
        """Test extraction when semantic_focus tag is missing."""
        result = synod_parser.extract_semantic_focus(sample_invalid_response)
        assert result == []

    def test_empty_semantic_focus(self):
        """Test extraction with empty semantic_focus tag."""
        text = "<semantic_focus></semantic_focus>"
        result = synod_parser.extract_semantic_focus(text)
        assert result == []


class TestCalculateTrustScore:
    """Tests for calculate_trust_score() function."""

    def test_perfect_trust(self):
        """Test Trust Score with perfect inputs."""
        result = synod_parser.calculate_trust_score(1.0, 1.0, 1.0, 0.1)
        assert result["trust_score"] == 2.0  # Capped at 2.0
        assert result["include"] is True
        assert result["rating"] == "high"

    def test_high_trust(self):
        """Test Trust Score in high range (>= 1.5)."""
        result = synod_parser.calculate_trust_score(0.9, 0.9, 0.9, 0.4)
        assert result["trust_score"] >= 1.5
        assert result["rating"] == "high"
        assert result["include"] is True

    def test_good_trust(self):
        """Test Trust Score in good range (1.0 - 1.5)."""
        result = synod_parser.calculate_trust_score(0.8, 0.8, 0.8, 0.5)
        assert 1.0 <= result["trust_score"] < 1.5
        assert result["rating"] == "good"
        assert result["include"] is True

    def test_acceptable_trust(self):
        """Test Trust Score in acceptable range (0.5 - 1.0)."""
        result = synod_parser.calculate_trust_score(0.7, 0.7, 0.7, 0.5)
        assert 0.5 <= result["trust_score"] < 1.0
        assert result["rating"] == "acceptable"
        assert result["include"] is True

    def test_low_trust(self):
        """Test Trust Score in low range (< 0.5)."""
        result = synod_parser.calculate_trust_score(0.3, 0.3, 0.3, 0.8)
        assert result["trust_score"] < 0.5
        assert result["rating"] == "low"
        assert result["include"] is False

    def test_self_orientation_minimum(self):
        """Test that self-orientation is clamped to minimum 0.1."""
        result = synod_parser.calculate_trust_score(0.8, 0.8, 0.8, 0.0)
        # Should use 0.1 instead of 0.0
        assert result["self_orientation"] == 0.1
        assert result["trust_score"] <= 2.0

    def test_trust_score_formula(self):
        """Test Trust Score formula: T = min((C×R×I)/S, 2.0)."""
        c, r, i, s = 0.9, 0.8, 0.7, 0.3
        expected = min((c * r * i) / s, 2.0)
        result = synod_parser.calculate_trust_score(c, r, i, s)
        assert abs(result["trust_score"] - expected) < 0.001


class TestParseResponse:
    """Tests for parse_response() main function."""

    def test_parse_valid_response(self, sample_valid_response):
        """Test parsing complete valid response."""
        result = synod_parser.parse_response(sample_valid_response)
        assert result["validation"]["is_valid"] is True
        assert result["confidence"]["score"] == 85
        assert len(result["semantic_focus"]) == 3
        assert result["can_exit_early"] is True
        assert result["high_confidence"] is True

    def test_parse_invalid_response_applies_defaults(self, sample_invalid_response):
        """Test that defaults are applied for invalid format."""
        result = synod_parser.parse_response(sample_invalid_response)
        assert "format_warning" in result
        assert result["confidence"]["score"] == 50  # Default
        assert result["confidence"]["can_exit"] is False
        assert len(result["semantic_focus"]) > 0  # Key sentences extracted

    def test_parse_detects_code_blocks(self):
        """Test detection of code blocks in response."""
        text = """
        <confidence score="80"></confidence>
        <semantic_focus>Code example</semantic_focus>
        ```python
        def hello():
            print("world")
        ```
        """
        result = synod_parser.parse_response(text)
        assert result["has_code"] is True

    def test_parse_no_code_blocks(self, sample_valid_response):
        """Test response without code blocks."""
        result = synod_parser.parse_response(sample_valid_response)
        assert result["has_code"] is False

    def test_parse_measures_length(self, sample_valid_response):
        """Test that raw_length is measured."""
        result = synod_parser.parse_response(sample_valid_response)
        assert result["raw_length"] == len(sample_valid_response)

    def test_confidence_below_85_not_high(self):
        """Test high_confidence flag for scores below 85."""
        text = """
        <confidence score="80"></confidence>
        <semantic_focus>Focus</semantic_focus>
        """
        result = synod_parser.parse_response(text)
        assert result["high_confidence"] is False


class TestExtractKeySentences:
    """Tests for extract_key_sentences() fallback function."""

    def test_extract_multiple_sentences(self):
        """Test extracting key sentences from plain text."""
        text = "First sentence here. Second sentence with content. Third one too. Fourth sentence."
        result = synod_parser.extract_key_sentences(text, limit=3)
        assert len(result) <= 3
        # Check that we got some results back
        assert len(result) > 0

    def test_filter_short_sentences(self):
        """Test that short sentences are filtered out."""
        text = "Hi. This is a longer sentence with actual content. Yes."
        result = synod_parser.extract_key_sentences(text, limit=3)
        # Short sentences (< 20 chars) should be filtered
        assert not any(len(s) < 20 for s in result)

    def test_removes_xml_tags(self):
        """Test that XML tags are stripped."""
        text = "<tag>This is content in tags.</tag> More content here."
        result = synod_parser.extract_key_sentences(text, limit=2)
        # Should not contain XML tags
        assert not any("<" in s or ">" in s for s in result)


class TestApplyDefaults:
    """Tests for apply_defaults() function."""

    def test_default_values(self, sample_invalid_response):
        """Test that correct default values are applied."""
        result = synod_parser.apply_defaults(sample_invalid_response)
        assert result["confidence"]["score"] == 50
        assert result["confidence"]["evidence"] is None
        assert result["confidence"]["logic"] is None
        assert result["confidence"]["expertise"] is None
        assert result["confidence"]["can_exit"] is False
        assert "format_warning" in result

    def test_extracts_key_sentences_as_fallback(self, sample_invalid_response):
        """Test that key sentences are extracted as semantic_focus fallback."""
        result = synod_parser.apply_defaults(sample_invalid_response)
        assert "semantic_focus" in result
        assert isinstance(result["semantic_focus"], list)


class TestParserCLI:
    """Tests for parser main() CLI (lines 243-300)."""

    def test_trust_calculation_cli(self, capsys):
        """Test --trust flag calculates trust score."""
        sys.argv = ["synod-parser", "--trust", "0.9", "0.8", "0.9", "0.2"]
        synod_parser.main()
        import json
        output = json.loads(capsys.readouterr().out)
        assert "trust_score" in output
        assert output["trust_score"] > 0

    def test_validate_cli_valid(self, capsys, sample_valid_response):
        """Test --validate flag with valid response."""
        sys.argv = ["synod-parser", "--validate", sample_valid_response]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0

    def test_validate_cli_invalid(self, capsys):
        """Test --validate flag with invalid response exits 1."""
        sys.argv = ["synod-parser", "--validate", "just plain text no xml"]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 1

    def test_full_parse_cli(self, capsys, sample_valid_response):
        """Test full parse via CLI argument."""
        sys.argv = ["synod-parser", sample_valid_response]
        synod_parser.main()
        import json
        output = json.loads(capsys.readouterr().out)
        assert "confidence" in output
        assert "semantic_focus" in output

    def test_consensus_cli(self, capsys):
        """Test --consensus flag."""
        sys.argv = [
            "synod-parser", "--consensus",
            "claude:1.5:85", "gemini:1.2:78", "openai:0.8:72"
        ]
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 0

    def test_no_input_exits(self, monkeypatch):
        """Test exits with error when no input provided (tty stdin)."""
        sys.argv = ["synod-parser"]
        # Simulate tty stdin by using a mock that returns True for isatty()
        import io
        mock_stdin = io.StringIO("")
        mock_stdin.isatty = lambda: True
        monkeypatch.setattr("sys.stdin", mock_stdin)
        with pytest.raises(SystemExit) as exc_info:
            synod_parser.main()
        assert exc_info.value.code == 1


class TestComputeMetrics:
    """Tests for _compute_metrics() and debate quality metric integration."""

    def test_parse_response_includes_metrics(self, sample_valid_response):
        """Test that valid SID input produces result with metrics key."""
        result = synod_parser.parse_response(sample_valid_response)
        assert "metrics" in result

    def test_parse_response_metrics_fields(self, sample_valid_response):
        """Test that metrics dict has all required fields."""
        result = synod_parser.parse_response(sample_valid_response)
        metrics = result["metrics"]
        assert "response_length" in metrics
        assert "format_compliance" in metrics
        assert "confidence_score" in metrics
        assert "semantic_focus_count" in metrics
        assert "has_evidence" in metrics
        assert "has_logic" in metrics
        assert "has_code" in metrics

    def test_parse_response_metrics_values_valid(self, sample_valid_response):
        """Test metric values for a valid SID response."""
        result = synod_parser.parse_response(sample_valid_response)
        metrics = result["metrics"]
        assert metrics["response_length"] == len(sample_valid_response)
        assert metrics["format_compliance"] is True
        assert metrics["confidence_score"] == 85
        assert metrics["semantic_focus_count"] == 3
        assert metrics["has_evidence"] is True
        assert metrics["has_logic"] is True
        assert metrics["has_code"] is False

    def test_parse_response_metrics_defaults(self, sample_invalid_response):
        """Test that malformed input still produces metrics with degraded values."""
        result = synod_parser.parse_response(sample_invalid_response)
        assert "metrics" in result
        metrics = result["metrics"]
        assert metrics["format_compliance"] is False
        assert metrics["confidence_score"] == 50  # default score
        assert metrics["has_evidence"] is False
        assert metrics["has_logic"] is False

    def test_compute_metrics_with_code(self):
        """Test metrics detection of code blocks."""
        text = """
        <confidence score="80"></confidence>
        <semantic_focus>Code example</semantic_focus>
        ```python
        def hello():
            print("world")
        ```
        """
        result = synod_parser.parse_response(text)
        assert result["metrics"]["has_code"] is True


class TestCollectRoundMetrics:
    """Tests for collect_round_metrics() aggregation function."""

    def test_collect_round_metrics(self):
        """Test aggregation of metrics from multiple parse results."""
        parsed_results = [
            {"metrics": {"confidence_score": 80, "format_compliance": True,
                         "response_length": 500, "semantic_focus_count": 3,
                         "has_evidence": True, "has_logic": True, "has_code": False}},
            {"metrics": {"confidence_score": 70, "format_compliance": True,
                         "response_length": 400, "semantic_focus_count": 2,
                         "has_evidence": True, "has_logic": False, "has_code": True}},
            {"metrics": {"confidence_score": 90, "format_compliance": False,
                         "response_length": 600, "semantic_focus_count": 4,
                         "has_evidence": False, "has_logic": True, "has_code": False}},
        ]
        result = synod_parser.collect_round_metrics(parsed_results)
        assert result["avg_confidence"] == 80  # (80+70+90)/3
        assert result["compliance_rate"] == 2  # 2 out of 3
        assert result["total_responses"] == 3
        assert result["avg_response_length"] == 500  # (500+400+600)/3
        assert result["total_semantic_focuses"] == 9  # 3+2+4

    def test_collect_round_metrics_single(self):
        """Test aggregation with single result."""
        parsed_results = [
            {"metrics": {"confidence_score": 85, "format_compliance": True,
                         "response_length": 300, "semantic_focus_count": 2,
                         "has_evidence": True, "has_logic": True, "has_code": False}},
        ]
        result = synod_parser.collect_round_metrics(parsed_results)
        assert result["avg_confidence"] == 85
        assert result["compliance_rate"] == 1
        assert result["total_responses"] == 1

    def test_collect_round_metrics_empty(self):
        """Test aggregation with empty list."""
        result = synod_parser.collect_round_metrics([])
        assert result["avg_confidence"] == 0
        assert result["compliance_rate"] == 0
        assert result["total_responses"] == 0


class TestFormatMetricsSummary:
    """Tests for format_metrics_summary() display function."""

    def test_format_metrics_summary(self):
        """Test human-readable one-line summary generation."""
        metrics = {
            "avg_confidence": 78,
            "compliance_rate": 3,
            "total_responses": 3,
            "avg_response_length": 500,
            "total_semantic_focuses": 9,
        }
        result = synod_parser.format_metrics_summary(metrics)
        assert isinstance(result, str)
        assert "78%" in result
        assert "3/3" in result

    def test_format_metrics_summary_low_compliance(self):
        """Test summary with low compliance rate."""
        metrics = {
            "avg_confidence": 45,
            "compliance_rate": 1,
            "total_responses": 3,
            "avg_response_length": 200,
            "total_semantic_focuses": 2,
        }
        result = synod_parser.format_metrics_summary(metrics)
        assert isinstance(result, str)
        assert "45%" in result
        assert "1/3" in result
