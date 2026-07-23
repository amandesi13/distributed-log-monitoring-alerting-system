from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    service: str
    severity: Severity
    message: str
    latency_ms: float | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class Alert:
    service: str
    severity: AlertSeverity
    title: str
    detail: str
    hint: str
    evidence_count: int
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True)
class MonitorConfig:
    window_seconds: int = 60
    error_threshold: int = 4
    latency_threshold_ms: float = 900.0
    restart_threshold: int = 2
    heartbeat_timeout_seconds: int = 120
