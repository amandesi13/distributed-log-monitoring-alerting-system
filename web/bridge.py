"""Entry points for the browser demo.

The page loads the real `log_monitoring` package into Pyodide (Python compiled
to WebAssembly) and calls these functions with plain strings and numbers.
They return JSON strings so the JavaScript side never touches Python objects.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from log_monitoring.alerts import _json_ready
from log_monitoring.analyzer import LogAnalyzer
from log_monitoring.models import MonitorConfig
from log_monitoring.parser import parse_log_line
from log_monitoring.simulator import generate_log_file

MAX_PARSE_ERRORS = 20


def analyze(
    log_text: str,
    window_seconds: int = 60,
    error_threshold: int = 4,
    latency_threshold_ms: float = 900.0,
) -> str:
    """Parse every line, run the analyzer and return events, alerts and parse errors.

    Lines that do not parse are reported with their line number and skipped,
    so one bad line does not hide the alerts in the rest of the file.
    """
    try:
        config = MonitorConfig(
            window_seconds=int(window_seconds),
            error_threshold=int(error_threshold),
            latency_threshold_ms=float(latency_threshold_ms),
        )
    except (TypeError, ValueError) as exc:
        return json.dumps({"ok": False, "error": f"invalid settings: {exc}"})

    events = []
    errors = []
    for number, line in enumerate(log_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(parse_log_line(line))
        except (ValueError, TypeError) as exc:
            if len(errors) < MAX_PARSE_ERRORS:
                errors.append({"line": number, "error": str(exc)[:200]})

    alerts = LogAnalyzer(config).analyze(events)
    ordered = sorted(events, key=lambda event: event.timestamp)
    return json.dumps(
        {
            "ok": True,
            "config": {
                "window_seconds": config.window_seconds,
                "error_threshold": config.error_threshold,
                "latency_threshold_ms": config.latency_threshold_ms,
            },
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "service": event.service,
                    "severity": event.severity.value,
                    "latency_ms": event.latency_ms,
                    "message": event.message,
                }
                for event in ordered
            ],
            "alerts": [_json_ready(alert) for alert in alerts],
            "parse_errors": errors,
        }
    )


def simulate(events: int = 120, seed: int = 7) -> str:
    """Generate a synthetic incident log with the project's own simulator."""
    count = max(10, min(int(events), 2000))
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_log_file(Path(tmp) / "simulated.log", events=count, seed=int(seed))
        return path.read_text(encoding="utf-8")
