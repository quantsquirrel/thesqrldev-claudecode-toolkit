#!/usr/bin/env python3
"""Synod debate progress visualization using Rich.

Displays real-time progress for multi-model debate phases.
Receives JSON events via stdin or can be used as a library.

Usage (stdin mode):
  echo '{"event":"phase_start","phase":1,"name":"Solver"}' | python3 synod_progress.py

Usage (library mode):
  from synod_progress import SynodProgress
  with SynodProgress() as progress:
      progress.phase_start(1, "Solver")
      progress.model_start("gemini")
      progress.model_complete("gemini", duration_ms=5000)
"""

import json
import sys
import time
from contextlib import contextmanager
from typing import Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Model display names and colors
MODEL_CONFIG = {
    "gemini": {"name": "Gemini Architect", "color": "blue", "icon": "◆"},
    "openai": {"name": "OpenAI Explorer", "color": "green", "icon": "●"},
    "claude": {"name": "Claude Validator", "color": "magenta", "icon": "▲"},
}

PHASE_NAMES = {
    0: "Setup",
    1: "Solver Round",
    2: "Critic Round",
    3: "Defense Round",
    4: "Synthesis",
}


class SynodProgress:
    """Real-time progress display for Synod debate phases."""

    def __init__(self, console: Optional[object] = None):
        self.console = console or (Console(stderr=True) if RICH_AVAILABLE else None)
        self.current_phase = 0
        self.phase_name = ""
        self.model_status: dict[str, str] = {}  # model -> status
        self.model_start_times: dict[str, float] = {}
        self.model_durations: dict[str, float] = {}
        self._live = None

    def _build_display(self) -> Panel:
        """Build the Rich display panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Icon", width=2)
        table.add_column("Model", width=20)
        table.add_column("Status", width=30)
        table.add_column("Time", width=10, justify="right")

        for model_key, config in MODEL_CONFIG.items():
            status = self.model_status.get(model_key, "waiting")
            elapsed = ""

            if model_key in self.model_durations:
                elapsed = f"{self.model_durations[model_key]:.1f}s"
            elif model_key in self.model_start_times:
                elapsed = f"{time.time() - self.model_start_times[model_key]:.0f}s"

            if status == "running":
                status_text = Text("● Running...", style=f"bold {config['color']}")
            elif status == "complete":
                status_text = Text("✓ Complete", style="bold green")
            elif status == "error":
                status_text = Text("✗ Error", style="bold red")
            else:
                status_text = Text("○ Waiting", style="dim")

            table.add_row(
                Text(config["icon"], style=config["color"]),
                Text(config["name"], style=config["color"]),
                status_text,
                Text(elapsed, style="dim"),
            )

        title = f"Phase {self.current_phase}: {self.phase_name}"
        return Panel(table, title=f"[bold]Synod v2.0 — {title}[/bold]", border_style="cyan")

    def _fallback_print(self, message: str):
        """Fallback for when Rich is not available."""
        print(f"[Synod] {message}", file=sys.stderr)

    def phase_start(self, phase: int, name: Optional[str] = None):
        """Signal start of a debate phase."""
        self.current_phase = phase
        self.phase_name = name or PHASE_NAMES.get(phase, f"Phase {phase}")
        self.model_status.clear()
        self.model_start_times.clear()
        self.model_durations.clear()

        if not RICH_AVAILABLE:
            self._fallback_print(f"Phase {phase}: {self.phase_name} started")
            return

        if self._live:
            self._live.update(self._build_display())

    def phase_end(self, phase: int):
        """Signal end of a debate phase."""
        if not RICH_AVAILABLE:
            self._fallback_print(f"Phase {phase}: Complete")
            return

        if self._live:
            self._live.update(self._build_display())

    def model_start(self, model: str):
        """Signal that a model has started processing."""
        self.model_status[model] = "running"
        self.model_start_times[model] = time.time()

        if not RICH_AVAILABLE:
            config = MODEL_CONFIG.get(model, {"name": model})
            self._fallback_print(f"{config['name']} started")
            return

        if self._live:
            self._live.update(self._build_display())

    def model_complete(self, model: str, duration_ms: Optional[int] = None):
        """Signal that a model has finished processing."""
        self.model_status[model] = "complete"
        if duration_ms is not None:
            self.model_durations[model] = duration_ms / 1000
        elif model in self.model_start_times:
            self.model_durations[model] = time.time() - self.model_start_times[model]

        if not RICH_AVAILABLE:
            config = MODEL_CONFIG.get(model, {"name": model})
            duration = self.model_durations.get(model, 0)
            self._fallback_print(f"{config['name']} complete ({duration:.1f}s)")
            return

        if self._live:
            self._live.update(self._build_display())

    def model_error(self, model: str, error: Optional[str] = None):
        """Signal that a model encountered an error."""
        self.model_status[model] = "error"

        if not RICH_AVAILABLE:
            config = MODEL_CONFIG.get(model, {"name": model})
            self._fallback_print(f"{config['name']} error: {error or 'unknown'}")
            return

        if self._live:
            self._live.update(self._build_display())

    def __enter__(self):
        if RICH_AVAILABLE:
            self._live = Live(self._build_display(), console=self.console, refresh_per_second=2)
            self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)
            self._live = None


def process_stdin():
    """Process JSON events from stdin for CLI usage."""
    progress = SynodProgress()

    if not sys.stdin.isatty():
        with progress:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("event", "")
                if event_type == "phase_start":
                    progress.phase_start(event.get("phase", 0), event.get("name"))
                elif event_type == "phase_end":
                    progress.phase_end(event.get("phase", 0))
                elif event_type == "model_start":
                    progress.model_start(event.get("model", ""))
                elif event_type == "model_complete":
                    progress.model_complete(event.get("model", ""), event.get("duration_ms"))
                elif event_type == "model_error":
                    progress.model_error(event.get("model", ""), event.get("error"))


if __name__ == "__main__":
    process_stdin()
