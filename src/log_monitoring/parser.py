from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .models import LogEvent, Severity

TEXT_PATTERN = re.compile(
    r"^(?P<timestamp>\S+)\s+"
    r"(?P<service>[\w.-]+)\s+"
    r"(?P<severity>debug|info|warning|warn|error|critical)\s+"
    r"(?P<message>.*)$",
    re.IGNORECASE,
)

LATENCY_PATTERN = re.compile(r"(?:latency|duration|elapsed)[_=:\s]+(?P<latency>\d+(?:\.\d+)?)ms", re.IGNORECASE)


def parse_log_line(line: str) -> LogEvent:
    line = line.strip()
    if not line:
        raise ValueError("empty log line")

    if line.startswith("{"):
        return _parse_json_line(line)

    match = TEXT_PATTERN.match(line)
    if not match:
        raise ValueError(f"unsupported log format: {line}")

    message = match.group("message")
    latency = _extract_latency(message)
    return LogEvent(
        timestamp=_parse_timestamp(match.group("timestamp")),
        service=match.group("service"),
        severity=_normalize_severity(match.group("severity")),
        message=message,
        latency_ms=latency,
        metadata={},
    )


def _parse_json_line(line: str) -> LogEvent:
    payload: dict[str, Any] = json.loads(line)
    message = str(payload.get("message", ""))
    latency = payload.get("latency_ms")
    if latency is None:
        latency = _extract_latency(message)

    metadata = {key: value for key, value in payload.items() if key not in {"timestamp", "service", "severity", "message", "latency_ms", "trace_id"}}
    return LogEvent(
        timestamp=_parse_timestamp(str(payload.get("timestamp"))),
        service=str(payload.get("service", "unknown-service")),
        severity=_normalize_severity(str(payload.get("severity", "info"))),
        message=message,
        latency_ms=float(latency) if latency is not None else None,
        trace_id=payload.get("trace_id"),
        metadata=metadata,
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_severity(value: str) -> Severity:
    lowered = value.lower()
    if lowered == "warn":
        lowered = "warning"
    return Severity(lowered)


def _extract_latency(message: str) -> float | None:
    match = LATENCY_PATTERN.search(message)
    return float(match.group("latency")) if match else None
