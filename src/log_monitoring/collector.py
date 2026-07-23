from __future__ import annotations

from pathlib import Path

from .models import LogEvent
from .parser import parse_log_line


class FileLogCollector:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def collect(self) -> list[LogEvent]:
        events: list[LogEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(parse_log_line(line))
                except ValueError as exc:
                    raise ValueError(f"{self.path}:{line_number}: {exc}") from exc
        return events
