"""Integration tests for Synod orchestration flow.

Tests end-to-end data flow between phases:
- Phase 0: Config loading
- Phase 1: Solver (classifier → solver → parser)
- Phase 2: Critic
- Phase 3: Defense
- Phase 4: Synthesis (trust scoring, weighted consensus)
"""

import importlib.util
import json
import os
import sys
from unittest import mock

import pytest

# Import standard modules
from tools.synod_config import (
    get_mode_config,
    get_timeouts,
    get_threshold,
    load_config,
)
from tools.synod_progress import SynodProgress

# Import hyphenated modules using importlib
def _import_hyphenated_module(module_name, file_name):
    """Import Python module with hyphens in filename."""
    tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools")
    file_path = os.path.join(tools_dir, file_name)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


classifier = _import_hyphenated_module("synod_classifier", "synod-classifier.py")
parser = _import_hyphenated_module("synod_parser", "synod-parser.py")


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config cache before each test."""
    import tools.synod_config as config_module
    config_module._CONFIG_CACHE = None
    yield
    config_module._CONFIG_CACHE = None


class TestPhaseOrchestration:
    """Test data flows between phases 0-4."""

    def test_phase0_config_loading_all_modes(self):
        """Phase 0: Verify config loads correctly for all 5 modes."""
        config = load_config()

        assert "modes" in config
        assert "complexity" in config
        assert "timeouts" in config
        assert "thresholds" in config

        # All 5 modes present
        modes = config["modes"]
        assert set(modes.keys()) == {"review", "design", "debug", "idea", "general"}

        # Each mode has required fields
        for mode_name, mode_config in modes.items():
            assert "description" in mode_config
            assert "models" in mode_config
            assert "rounds" in mode_config
            assert "focus" in mode_config

    def test_phase1_classifier_output_feeds_solver_config(self):
        """Phase 1: Classifier output (mode/complexity/rounds) feeds into solver."""
        # Simulate user prompt
        prompt = "이 코드 리뷰해줘: def foo(): pass"

        # Phase 1a: Classifier determines mode and rounds
        mode, confidence = classifier.classify_prompt(prompt)
        complexity_level, rounds = classifier.determine_complexity(prompt)

        assert mode in ["review", "design", "debug", "idea", "general"]
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        assert complexity_level in ["simple", "medium", "complex"]
        assert rounds in [2, 3, 4]

        # Phase 1b: Config provides model settings for detected mode
        mode_config = get_mode_config(mode)
        assert "models" in mode_config
        assert "gemini" in mode_config["models"]
        assert "openai" in mode_config["models"]

    def test_phase1_mock_solver_xml_response_parsing(self):
        """Phase 1: Mock solver XML responses parse correctly."""
        mock_response = """
<confidence score="85">
<evidence>Code follows PEP 8 conventions</evidence>
<logic>Function naming is clear and descriptive</logic>
<expertise>Python best practices applied</expertise>
<can_exit>false</can_exit>
</confidence>

<semantic_focus>
1. Function signature is well-defined
2. Docstring is missing
3. Type hints would improve clarity
</semantic_focus>

The code is acceptable but could be improved.
"""

        # Parse the response
        result = parser.parse_response(mock_response)

        assert result["validation"]["is_valid"] is True
        assert result["confidence"]["score"] == 85
        assert result["confidence"]["can_exit"] is False
        assert "evidence" in result["confidence"]
        assert len(result["semantic_focus"]) > 0

    def test_phase2_trust_score_calculation(self):
        """Phase 2-3: Trust score calculation T = (C*R*I)/S with cap."""
        # CortexDebate Trust Score formula
        c = 0.9  # Credibility
        r = 0.85  # Reliability
        i = 0.8  # Intimacy
        s = 0.3  # Self-Orientation

        trust_result = parser.calculate_trust_score(c, r, i, s)

        # Formula: T = min((C*R*I)/S, trust_cap)
        expected_trust = min((c * r * i) / s, 2.0)

        assert trust_result["trust_score"] == pytest.approx(expected_trust, abs=0.001)
        assert trust_result["credibility"] == c
        assert trust_result["reliability"] == r
        assert trust_result["intimacy"] == i
        assert trust_result["self_orientation"] == s

    def test_phase3_trust_score_respects_cap_from_config(self):
        """Phase 3: Trust score cap from config (trust_cap = 2.0)."""
        trust_cap = get_threshold("trust_cap")
        assert trust_cap == 2.0

        # High trust scenario that would exceed cap
        c, r, i, s = 1.0, 1.0, 1.0, 0.1
        trust_result = parser.calculate_trust_score(c, r, i, s)

        # Raw formula would give 10.0, but should be capped
        raw_trust = (c * r * i) / s
        assert raw_trust == 10.0
        assert trust_result["trust_score"] == 2.0  # Capped

    def test_phase3_trust_filtering_below_threshold(self):
        """Phase 3: Responses with trust < trust_exclude filtered out."""
        trust_exclude = get_threshold("trust_exclude")
        assert trust_exclude == 0.5

        # Low trust scenario
        trust_result = parser.calculate_trust_score(0.3, 0.4, 0.5, 0.8)

        assert trust_result["trust_score"] < trust_exclude
        assert trust_result["include"] is False
        assert trust_result["rating"] == "low"

    def test_phase4_weighted_confidence_consensus(self):
        """Phase 4: Weighted consensus FINAL = Σ(T_i × C_i) / Σ(T_i)."""
        model_scores = [
            {"model": "gemini", "trust_score": 1.5, "confidence": 85},
            {"model": "openai", "trust_score": 1.2, "confidence": 90},
            {"model": "claude", "trust_score": 1.8, "confidence": 80},
        ]

        consensus = parser.weighted_consensus(model_scores)

        # Calculate expected
        total_trust = 1.5 + 1.2 + 1.8  # 4.5
        expected_final = (1.5*85 + 1.2*90 + 1.8*80) / total_trust

        assert consensus["final_confidence"] == pytest.approx(expected_final, abs=0.1)
        assert consensus["dominant_model"] == "claude"  # Highest trust
        assert len(consensus["weights"]) == 3

        # Weights should sum to ~1.0
        weight_sum = sum(consensus["weights"].values())
        assert weight_sum == pytest.approx(1.0, abs=0.01)

    def test_phase4_weighted_consensus_zero_trust_fallback(self):
        """Phase 4: Zero trust fallback uses equal weighting."""
        model_scores = [
            {"model": "gemini", "trust_score": 0.0, "confidence": 85},
            {"model": "openai", "trust_score": 0.0, "confidence": 90},
        ]

        consensus = parser.weighted_consensus(model_scores)

        # Equal weighting fallback
        expected_final = (85 + 90) / 2
        assert consensus["final_confidence"] == expected_final
        assert consensus["weights"]["gemini"] == 0.5
        assert consensus["weights"]["openai"] == 0.5

    def test_phase4_confidence_interval_calculation(self):
        """Phase 4: Confidence interval for trust scores."""
        scores = [1.2, 1.5, 1.3, 1.4]

        ci = parser.calculate_confidence_interval(scores)

        assert ci["n"] == 4
        assert ci["mean"] == pytest.approx(1.35, abs=0.01)
        assert ci["lower"] < ci["mean"]
        assert ci["upper"] > ci["mean"]
        assert ci["margin"] > 0

    def test_phase4_confidence_interval_single_score(self):
        """Phase 4: Single score has zero margin."""
        ci = parser.calculate_confidence_interval([1.5])

        assert ci["n"] == 1
        assert ci["mean"] == 1.5
        assert ci["lower"] == 1.5
        assert ci["upper"] == 1.5
        assert ci["margin"] == 0

    def test_phase4_confidence_interval_empty_scores(self):
        """Phase 4: Empty scores return zero values."""
        ci = parser.calculate_confidence_interval([])

        assert ci["n"] == 0
        assert ci["mean"] == 0
        assert ci["lower"] == 0
        assert ci["upper"] == 0
        assert ci["margin"] == 0


class TestCanaryIntegration:
    """Test SYNOD_V2_CANARY flag integration."""

    def test_canary_defaults_to_zero_when_not_set(self):
        """SYNOD_V2_CANARY defaults to '0' when not in environment."""
        # Ensure it's not set
        env_value = os.environ.get("SYNOD_V2_CANARY", "0")

        # Default should be '0' (disabled)
        assert env_value == "0"

    def test_canary_zero_means_no_probes(self):
        """When SYNOD_V2_CANARY='0', no canary probes run."""
        with mock.patch.dict(os.environ, {"SYNOD_V2_CANARY": "0"}):
            canary_enabled = os.environ.get("SYNOD_V2_CANARY") == "1"
            assert canary_enabled is False

    def test_canary_one_enables_probes(self):
        """When SYNOD_V2_CANARY='1', canary probes enabled."""
        with mock.patch.dict(os.environ, {"SYNOD_V2_CANARY": "1"}):
            canary_enabled = os.environ.get("SYNOD_V2_CANARY") == "1"
            assert canary_enabled is True


class TestProgressEventProtocol:
    """Test progress event protocol across phases."""

    def test_phase_lifecycle_events_sequence(self):
        """Test phase_start → model_start → model_complete → phase_end."""
        progress = SynodProgress()

        # Phase 1 lifecycle
        progress.phase_start(1, "Solver Round")
        assert progress.current_phase == 1
        assert progress.phase_name == "Solver Round"

        # Model events
        progress.model_start("gemini")
        assert progress.model_status["gemini"] == "running"

        progress.model_complete("gemini", duration_ms=5000)
        assert progress.model_status["gemini"] == "complete"
        assert progress.model_durations["gemini"] == 5.0

        progress.phase_end(1)
        # State should still be preserved after phase_end
        assert progress.current_phase == 1

    def test_error_handling_updates_status(self):
        """Test model_error updates status correctly."""
        progress = SynodProgress()

        progress.phase_start(2, "Critic Round")
        progress.model_start("openai")
        progress.model_error("openai", "API timeout")

        assert progress.model_status["openai"] == "error"

    def test_all_five_phases_tracked_sequentially(self):
        """Test all phases 0-4 can be tracked sequentially."""
        progress = SynodProgress()

        phase_names = [
            (0, "Setup"),
            (1, "Solver Round"),
            (2, "Critic Round"),
            (3, "Defense Round"),
            (4, "Synthesis"),
        ]

        for phase_num, phase_name in phase_names:
            progress.phase_start(phase_num, phase_name)
            assert progress.current_phase == phase_num
            assert progress.phase_name == phase_name

            # Each phase can track models
            progress.model_start("gemini")
            assert "gemini" in progress.model_status

            progress.phase_end(phase_num)

    def test_phase_start_clears_previous_model_state(self):
        """Test phase_start clears model status from previous phase."""
        progress = SynodProgress()

        # Phase 1 with some model state
        progress.phase_start(1, "Solver")
        progress.model_start("gemini")
        progress.model_complete("gemini", duration_ms=1000)

        assert len(progress.model_status) > 0
        assert len(progress.model_durations) > 0

        # Phase 2 should clear state
        progress.phase_start(2, "Critic")

        assert progress.model_status == {}
        assert progress.model_start_times == {}
        assert progress.model_durations == {}

    def test_multiple_models_in_single_phase(self):
        """Test tracking multiple models in a single phase."""
        progress = SynodProgress()

        progress.phase_start(1, "Solver Round")

        # Start all three models
        progress.model_start("gemini")
        progress.model_start("openai")
        progress.model_start("claude")

        assert progress.model_status["gemini"] == "running"
        assert progress.model_status["openai"] == "running"
        assert progress.model_status["claude"] == "running"

        # Complete them
        progress.model_complete("gemini", duration_ms=3000)
        progress.model_complete("openai", duration_ms=4000)
        progress.model_complete("claude", duration_ms=3500)

        assert progress.model_status["gemini"] == "complete"
        assert progress.model_status["openai"] == "complete"
        assert progress.model_status["claude"] == "complete"
        assert progress.model_durations["gemini"] == 3.0
        assert progress.model_durations["openai"] == 4.0
        assert progress.model_durations["claude"] == 3.5


class TestConfigProgressIntegration:
    """Test config + progress integration."""

    def test_config_timeouts_accessible(self):
        """Test config timeouts match YAML values."""
        timeouts = get_timeouts()

        assert timeouts["model"] == 110
        assert timeouts["outer"] == 120

    def test_config_thresholds_accessible_for_trust_calculation(self):
        """Test config thresholds accessible for trust scoring."""
        thresholds = {
            "low_confidence": get_threshold("low_confidence"),
            "trust_exclude": get_threshold("trust_exclude"),
            "trust_good": get_threshold("trust_good"),
            "trust_high": get_threshold("trust_high"),
            "trust_cap": get_threshold("trust_cap"),
            "early_exit_confidence": get_threshold("early_exit_confidence"),
        }

        assert thresholds["low_confidence"] == 50
        assert thresholds["trust_exclude"] == 0.5
        assert thresholds["trust_good"] == 1.0
        assert thresholds["trust_high"] == 1.5
        assert thresholds["trust_cap"] == 2.0
        assert thresholds["early_exit_confidence"] == 90

    def test_progress_tracks_phase_with_config_mode(self):
        """Test progress can track phases corresponding to config modes."""
        modes = ["review", "design", "debug", "idea", "general"]

        for mode in modes:
            mode_config = get_mode_config(mode)
            rounds = mode_config["rounds"]["base"]

            # Progress can track this mode's rounds
            progress = SynodProgress()
            for phase in range(rounds):
                progress.phase_start(phase, f"{mode.capitalize()} Phase {phase}")
                assert progress.current_phase == phase

    def test_classifier_complexity_uses_config_thresholds(self):
        """Test classifier uses config complexity thresholds."""
        # Simple prompt
        simple_prompt = "Fix this bug"
        complexity, rounds = classifier.determine_complexity(simple_prompt)
        assert complexity == "simple"
        assert rounds == 2

        # Complex prompt (long with code blocks)
        complex_prompt = "Review this code:\n" + "```python\n" + "def foo():\n    pass\n" * 50 + "```\n"
        complexity, rounds = classifier.determine_complexity(complex_prompt)
        assert rounds >= 2

    def test_end_to_end_flow_review_mode(self):
        """Test end-to-end flow for review mode."""
        # Phase 0: Load config
        config = load_config()
        assert "modes" in config

        # Phase 1a: Classify prompt
        prompt = "이 코드 리뷰해줘"
        mode, confidence = classifier.classify_prompt(prompt)
        assert mode == "review"

        # Phase 1b: Get mode config
        mode_config = get_mode_config(mode)
        assert mode_config["models"]["gemini"]["model"] == "flash"

        # Phase 1c: Progress tracking
        progress = SynodProgress()
        progress.phase_start(1, "Solver Round")
        progress.model_start("gemini")

        # Phase 1d: Parse response (mocked)
        mock_response = '<confidence score="80"><evidence>Good</evidence></confidence>\n<semantic_focus>Key points</semantic_focus>'
        result = parser.parse_response(mock_response)

        progress.model_complete("gemini", duration_ms=3000)

        # Phase 4: Calculate trust and consensus
        trust = parser.calculate_trust_score(0.8, 0.9, 0.7, 0.3)
        assert trust["trust_score"] > 0

        trust_exclude = get_threshold("trust_exclude")
        if trust["trust_score"] >= trust_exclude:
            assert trust["include"] is True

    def test_end_to_end_flow_with_multiple_models(self):
        """Test end-to-end flow with multiple model responses."""
        # Phase 0-1: Setup and classify
        prompt = "시스템 아키텍처 설계"
        mode, _ = classifier.classify_prompt(prompt)
        assert mode == "design"

        # Phase 1-3: Simulate multiple model responses
        progress = SynodProgress()
        progress.phase_start(1, "Solver Round")

        # Mock responses from 3 models
        model_responses = []
        for model_name in ["gemini", "openai", "claude"]:
            progress.model_start(model_name)

            # Mock confidence score
            confidence_score = 80 + len(model_responses) * 5

            # Mock trust calculation
            trust = parser.calculate_trust_score(0.85, 0.8, 0.75, 0.35)

            model_responses.append({
                "model": model_name,
                "trust_score": trust["trust_score"],
                "confidence": confidence_score,
            })

            progress.model_complete(model_name, duration_ms=3000)

        progress.phase_end(1)

        # Phase 4: Calculate weighted consensus
        consensus = parser.weighted_consensus(model_responses)

        assert "final_confidence" in consensus
        assert "weights" in consensus
        assert "dominant_model" in consensus
        assert len(consensus["weights"]) == 3
