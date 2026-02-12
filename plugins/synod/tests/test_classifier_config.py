"""Tests for synod-classifier.py YAML config integration and coverage."""

import importlib.util
import io
import json
import os
import sys
import pytest

# Load the classifier module (hyphenated filename requires importlib)
_classifier_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "synod-classifier.py"
)
spec = importlib.util.spec_from_file_location("synod_classifier", _classifier_path)
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)


class TestKeywordPatternLoading:
    """Test that classifier loads keyword patterns from YAML config."""

    def test_load_keyword_patterns_returns_dict(self):
        """Test _load_keyword_patterns returns a dict with mode keys."""
        patterns = classifier._load_keyword_patterns()
        assert isinstance(patterns, dict)
        assert "review" in patterns
        assert "design" in patterns
        assert "debug" in patterns
        assert "idea" in patterns

    def test_load_keyword_patterns_has_lists(self):
        """Test each mode has a list of patterns."""
        patterns = classifier._load_keyword_patterns()
        for mode, pats in patterns.items():
            assert isinstance(pats, list), f"{mode} should have list of patterns"
            assert len(pats) > 0, f"{mode} should have at least one pattern"

    def test_patterns_match_yaml_config(self):
        """Test loaded patterns match YAML config values."""
        from tools.synod_config import get_all_keywords
        yaml_keywords = get_all_keywords()
        loaded_patterns = classifier._load_keyword_patterns()

        # Should match the YAML config
        assert set(loaded_patterns.keys()) == set(yaml_keywords.keys())
        for mode in yaml_keywords:
            assert loaded_patterns[mode] == yaml_keywords[mode]


class TestClassifyWithConfig:
    """Test classify_prompt uses config-loaded patterns."""

    def test_classify_review_korean(self):
        mode, conf = classifier.classify_prompt("코드를 리뷰해주세요")
        assert mode == "review"

    def test_classify_design_korean(self):
        mode, conf = classifier.classify_prompt("시스템 설계를 도와주세요")
        assert mode == "design"

    def test_classify_debug_korean(self):
        mode, conf = classifier.classify_prompt("에러가 발생합니다 디버그")
        assert mode == "debug"

    def test_classify_idea_korean(self):
        mode, conf = classifier.classify_prompt("아이디어를 브레인스토밍해봐요")
        assert mode == "idea"

    def test_classify_general_no_match(self):
        mode, conf = classifier.classify_prompt("hello world")
        assert mode == "general"
        assert conf == 0.5


class TestComplexityWithConfig:
    """Test determine_complexity uses config thresholds."""

    def test_simple_complexity(self):
        level, rounds = classifier.determine_complexity("short input")
        assert level == "simple"
        assert rounds == 2

    def test_medium_complexity(self):
        # 100 words → score ~1.0 (medium)
        prompt = " ".join(["word"] * 100)
        level, rounds = classifier.determine_complexity(prompt)
        assert level == "medium"
        assert rounds == 3

    def test_complex_complexity(self):
        # 300 words + code blocks → score well above 2.0
        prompt = " ".join(["word"] * 300) + "\n```python\ncode\n```\n```js\ncode\n```"
        level, rounds = classifier.determine_complexity(prompt)
        assert level == "complex"
        assert rounds == 4

    def test_file_mentions_add_to_score(self):
        # File mentions (.py, .js) contribute 0.3 each
        prompt = "fix main.py and utils.js and config.yaml"
        level, rounds = classifier.determine_complexity(prompt)
        assert level in ("simple", "medium")


class TestClassifyProblemType:
    """Test classify_problem_type function (lines 85-111)."""

    def test_coding_code_blocks(self):
        assert classifier.classify_problem_type("```python\nprint('hi')\n```") == "coding"

    def test_coding_keywords(self):
        assert classifier.classify_problem_type("def hello_world():") == "coding"
        assert classifier.classify_problem_type("import os") == "coding"
        assert classifier.classify_problem_type("class Foo:") == "coding"
        assert classifier.classify_problem_type("function bar()") == "coding"
        assert classifier.classify_problem_type("const x = 1") == "coding"

    def test_math_expression(self):
        assert classifier.classify_problem_type("calculate 5 + 3 = 8") == "math"

    def test_math_korean(self):
        assert classifier.classify_problem_type("수학 문제를 풀어줘") == "math"
        assert classifier.classify_problem_type("계산해줘") == "math"

    def test_math_algorithm(self):
        assert classifier.classify_problem_type("algorithm optimization") == "math"

    def test_creative_idea(self):
        assert classifier.classify_problem_type("아이디어 좀 줘") == "creative"

    def test_creative_brainstorm(self):
        assert classifier.classify_problem_type("브레인스토밍 해보자") == "creative"

    def test_creative_naming(self):
        assert classifier.classify_problem_type("이름 지어줘") == "creative"
        assert classifier.classify_problem_type("naming convention") == "creative"

    def test_general_default(self):
        assert classifier.classify_problem_type("what is the weather today") == "general"


class TestClassifierMainCLI:
    """Test main() CLI function (lines 161-214)."""

    def test_main_with_prompt_arg(self, capsys):
        sys.argv = ["synod-classifier.py", "코드 리뷰해줘"]
        classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert output["mode"] == "review"
        assert "confidence" in output
        assert "problem_type" in output
        assert "complexity" in output
        assert "rounds" in output

    def test_main_mode_only(self, capsys):
        sys.argv = ["synod-classifier.py", "--mode-only", "시스템 설계"]
        classifier.main()
        output = capsys.readouterr().out.strip()
        assert output == "design"

    def test_main_with_complexity(self, capsys):
        sys.argv = ["synod-classifier.py", "--complexity", "debug this error"]
        classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert "complexity" in output
        assert "rounds" in output

    def test_main_no_prompt_exits(self, monkeypatch):
        sys.argv = ["synod-classifier.py"]
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(SystemExit) as exc_info:
            classifier.main()
        assert exc_info.value.code == 1

    def test_main_stdin_input(self, capsys, monkeypatch):
        sys.argv = ["synod-classifier.py"]
        monkeypatch.setattr("sys.stdin", io.StringIO("에러가 발생합니다"))
        classifier.main()
        output = json.loads(capsys.readouterr().out)
        assert output["mode"] == "debug"
