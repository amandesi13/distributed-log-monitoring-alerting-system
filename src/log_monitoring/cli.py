from __future__ import annotations

import argparse
from pathlib import Path

from .alerts import ConsoleAlertSink
from .analyzer import LogAnalyzer
from .collector import FileLogCollector
from .models import MonitorConfig
from .simulator import generate_log_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor distributed service logs and emit operational alerts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a log file and print alerts.")
    analyze_parser.add_argument("path", help="Path to a JSON or text log file.")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text", help="Alert output format.")
    analyze_parser.add_argument("--window-seconds", type=int, default=60)
    analyze_parser.add_argument("--error-threshold", type=int, default=4)
    analyze_parser.add_argument("--latency-threshold-ms", type=float, default=900.0)

    simulate_parser = subparsers.add_parser("simulate", help="Generate a synthetic distributed service log.")
    simulate_parser.add_argument("--output", default="reports/simulated.log")
    simulate_parser.add_argument("--events", type=int, default=120)
    simulate_parser.add_argument("--seed", type=int, default=7)

    args = parser.parse_args()
    if args.command == "simulate":
        output = generate_log_file(args.output, events=args.events, seed=args.seed)
        print(f"Wrote simulated log file to {output}")
        return

    config = MonitorConfig(
        window_seconds=args.window_seconds,
        error_threshold=args.error_threshold,
        latency_threshold_ms=args.latency_threshold_ms,
    )
    events = FileLogCollector(Path(args.path)).collect()
    alerts = LogAnalyzer(config).analyze(events)
    ConsoleAlertSink(args.format).publish(alerts)


if __name__ == "__main__":
    main()
