"""Tests for synod_progress.py - Rich-based progress visualization."""

import io
import json
import sys
import time
from unittest import mock

import pytest

# Import the module
from tools import synod_progress


class TestSynodProgressInit:
    """Test SynodProgress initialization."""

    def test_synod_progress_init(self):
        """Test default initialization state."""
        progress = synod_progress.SynodProgress()

        assert progress.current_phase == 0
        assert progress.phase_name == ""
        assert progress.model_status == {}
        assert progress.model_start_times == {}
        assert progress.model_durations == {}
        assert progress._live is None


class TestPhaseManagement:
    """Test phase start/end functionality."""

    def test_phase_start_sets_state(self):
        """Test phase_start updates internal state."""
        progress = synod_progress.SynodProgress()

        progress.phase_start(1, "Solver Round")

        assert progress.current_phase == 1
        assert progress.phase_name == "Solver Round"
        assert progress.model_status == {}
        assert progress.model_start_times == {}
        assert progress.model_durations == {}

    def test_phase_start_uses_default_name(self):
        """Test phase_start uses PHASE_NAMES when name not provided."""
        progress = synod_progress.SynodProgress()

        progress.phase_start(2)

        assert progress.current_phase == 2
        assert progress.phase_name == "Critic Round"

    def test_phase_start_unknown_phase_fallback(self):
        """Test phase_start with unknown phase number."""
        progress = synod_progress.SynodProgress()

        progress.phase_start(99)

        assert progress.current_phase == 99
        assert progress.phase_name == "Phase 99"

    def test_phase_end(self):
        """Test phase_end method exists and runs."""
        progress = synod_progress.SynodProgress()
        progress.phase_start(1, "Test Phase")

        # Should not raise
        progress.phase_end(1)


class TestModelTracking:
    """Test model status tracking."""

    def test_model_start_sets_running(self):
        """Test model_start sets status to running and records start time."""
        progress = synod_progress.SynodProgress()
        start_time = time.time()

        progress.model_start("gemini")

        assert progress.model_status["gemini"] == "running"
        assert "gemini" in progress.model_start_times
        assert progress.model_start_times["gemini"] >= start_time

    def test_model_complete_sets_complete(self):
        """Test model_complete sets status and calculates duration."""
        progress = synod_progress.SynodProgress()
        progress.model_start("openai")
        time.sleep(0.01)  # Small delay

        progress.model_complete("openai")

        assert progress.model_status["openai"] == "complete"
        assert "openai" in progress.model_durations
        assert progress.model_durations["openai"] > 0

    def test_model_complete_with_duration_ms(self):
        """Test model_complete with explicit duration_ms parameter."""
        progress = synod_progress.SynodProgress()

        progress.model_complete("claude", duration_ms=5000)

        assert progress.model_status["claude"] == "complete"
        assert progress.model_durations["claude"] == 5.0

    def test_model_complete_without_start_time(self):
        """Test model_complete when model was never started."""
        progress = synod_progress.SynodProgress()

        progress.model_complete("gemini", duration_ms=3000)

        assert progress.model_status["gemini"] == "complete"
        assert progress.model_durations["gemini"] == 3.0

    def test_model_error_sets_error(self):
        """Test model_error sets error status."""
        progress = synod_progress.SynodProgress()

        progress.model_error("openai", "API timeout")

        assert progress.model_status["openai"] == "error"


class TestFallbackMode:
    """Test fallback behavior when Rich is not available."""

    def test_fallback_print_without_rich(self, capsys):
        """Test _fallback_print outputs to stderr."""
        progress = synod_progress.SynodProgress()

        progress._fallback_print("Test message")

        captured = capsys.readouterr()
        assert "[Synod] Test message" in captured.err

    def test_phase_start_without_rich(self, capsys, monkeypatch):
        """Test phase_start fallback when Rich not available."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)
        progress = synod_progress.SynodProgress()

        progress.phase_start(1, "Test Phase")

        captured = capsys.readouterr()
        assert "[Synod] Phase 1: Test Phase started" in captured.err

    def test_phase_end_without_rich(self, capsys, monkeypatch):
        """Test phase_end fallback when Rich not available."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)
        progress = synod_progress.SynodProgress()

        progress.phase_end(2)

        captured = capsys.readouterr()
        assert "[Synod] Phase 2: Complete" in captured.err

    def test_model_start_without_rich(self, capsys, monkeypatch):
        """Test model_start fallback when Rich not available."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)
        progress = synod_progress.SynodProgress()

        progress.model_start("gemini")

        captured = capsys.readouterr()
        assert "[Synod] Gemini Architect started" in captured.err

    def test_model_complete_without_rich(self, capsys, monkeypatch):
        """Test model_complete fallback when Rich not available."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)
        progress = synod_progress.SynodProgress()

        progress.model_complete("openai", duration_ms=2500)

        captured = capsys.readouterr()
        assert "[Synod] OpenAI Explorer complete (2.5s)" in captured.err

    def test_model_error_without_rich(self, capsys, monkeypatch):
        """Test model_error fallback when Rich not available."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)
        progress = synod_progress.SynodProgress()

        progress.model_error("claude", "timeout")

        captured = capsys.readouterr()
        assert "[Synod] Claude Validator error: timeout" in captured.err


class TestConfiguration:
    """Test configuration dictionaries."""

    def test_model_config_has_all_models(self):
        """Test MODEL_CONFIG has all expected models."""
        assert "gemini" in synod_progress.MODEL_CONFIG
        assert "openai" in synod_progress.MODEL_CONFIG
        assert "claude" in synod_progress.MODEL_CONFIG

        # Check structure
        for model, config in synod_progress.MODEL_CONFIG.items():
            assert "name" in config
            assert "color" in config
            assert "icon" in config

    def test_phase_names_complete(self):
        """Test PHASE_NAMES covers expected phases."""
        assert 0 in synod_progress.PHASE_NAMES
        assert 1 in synod_progress.PHASE_NAMES
        assert 2 in synod_progress.PHASE_NAMES
        assert 3 in synod_progress.PHASE_NAMES
        assert 4 in synod_progress.PHASE_NAMES

        assert synod_progress.PHASE_NAMES[0] == "Setup"
        assert synod_progress.PHASE_NAMES[1] == "Solver Round"
        assert synod_progress.PHASE_NAMES[2] == "Critic Round"
        assert synod_progress.PHASE_NAMES[3] == "Defense Round"
        assert synod_progress.PHASE_NAMES[4] == "Synthesis"


class TestContextManager:
    """Test context manager protocol."""

    def test_context_manager_without_rich(self, monkeypatch):
        """Test context manager enter/exit without Rich."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)

        progress = synod_progress.SynodProgress()
        with progress as p:
            assert p is progress
            assert p._live is None

        assert progress._live is None

    @mock.patch('tools.synod_progress.Live')
    def test_context_manager_with_rich(self, mock_live):
        """Test context manager with Rich available."""
        if not synod_progress.RICH_AVAILABLE:
            pytest.skip("Rich not available")

        mock_live_instance = mock.MagicMock()
        mock_live.return_value = mock_live_instance

        progress = synod_progress.SynodProgress()

        with progress as p:
            assert p is progress
            mock_live_instance.__enter__.assert_called_once()

        mock_live_instance.__exit__.assert_called_once()


class TestStdinProcessing:
    """Test stdin JSON event processing."""

    def test_process_stdin_json_events(self, monkeypatch, capsys):
        """Test process_stdin handles valid JSON events."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)

        # Mock stdin with JSON events
        events = [
            '{"event":"phase_start","phase":1,"name":"Solver"}',
            '{"event":"model_start","model":"gemini"}',
            '{"event":"model_complete","model":"gemini","duration_ms":5000}',
            '{"event":"phase_end","phase":1}',
        ]
        mock_stdin = io.StringIO('\n'.join(events))
        monkeypatch.setattr(sys, 'stdin', mock_stdin)
        monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)

        synod_progress.process_stdin()

        captured = capsys.readouterr()
        assert "[Synod] Phase 1: Solver started" in captured.err
        assert "[Synod] Gemini Architect started" in captured.err
        assert "[Synod] Gemini Architect complete (5.0s)" in captured.err
        assert "[Synod] Phase 1: Complete" in captured.err

    def test_process_stdin_ignores_invalid_json(self, monkeypatch, capsys):
        """Test process_stdin ignores malformed JSON."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)

        events = [
            '{"event":"phase_start","phase":1}',
            'invalid json here',
            '',  # empty line
            '{"event":"phase_end","phase":1}',
        ]
        mock_stdin = io.StringIO('\n'.join(events))
        monkeypatch.setattr(sys, 'stdin', mock_stdin)
        monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)

        # Should not raise, should skip invalid JSON
        synod_progress.process_stdin()

        captured = capsys.readouterr()
        assert "[Synod] Phase 1:" in captured.err  # First event processed
        assert "[Synod] Phase 1: Complete" in captured.err  # Last event processed

    def test_process_stdin_handles_model_error_event(self, monkeypatch, capsys):
        """Test process_stdin handles model_error events."""
        monkeypatch.setattr(synod_progress, "RICH_AVAILABLE", False)

        events = [
            '{"event":"model_error","model":"openai","error":"timeout"}',
        ]
        mock_stdin = io.StringIO('\n'.join(events))
        monkeypatch.setattr(sys, 'stdin', mock_stdin)
        monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)

        synod_progress.process_stdin()

        captured = capsys.readouterr()
        assert "[Synod] OpenAI Explorer error: timeout" in captured.err


class TestBuildDisplay:
    """Test _build_display method when Rich is available."""

    def test_build_display_returns_panel(self):
        """Test _build_display creates a Panel object."""
        if not synod_progress.RICH_AVAILABLE:
            pytest.skip("Rich not available")

        progress = synod_progress.SynodProgress()
        progress.phase_start(1, "Test Phase")

        panel = progress._build_display()

        # Check it's a Panel (Rich object)
        assert hasattr(panel, 'renderable')
        assert hasattr(panel, 'title')

    def test_build_display_includes_phase_info(self):
        """Test _build_display includes phase information in title."""
        if not synod_progress.RICH_AVAILABLE:
            pytest.skip("Rich not available")

        progress = synod_progress.SynodProgress()
        progress.phase_start(2, "Critic Round")

        panel = progress._build_display()

        # Title should contain phase info
        assert "Phase 2" in str(panel.title)
        assert "Critic Round" in str(panel.title)
