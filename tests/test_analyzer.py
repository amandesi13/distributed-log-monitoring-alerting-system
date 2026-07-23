from datetime import datetime, timedelta, timezone

from log_monitoring.analyzer import LogAnalyzer
from log_monitoring.models import AlertSeverity, LogEvent, MonitorConfig, Severity


def test_detects_error_burst() -> None:
    start = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)
    events = [
        LogEvent(start + timedelta(seconds=index * 5), "checkout-api", Severity.ERROR, "database timeout")
        for index in range(4)
    ]

    alerts = LogAnalyzer(MonitorConfig(error_threshold=4)).analyze(events)

    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].service == "checkout-api"


def test_detects_latency_spike() -> None:
    start = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)
    events = [
        LogEvent(start, "inventory-api", Severity.INFO, "slow request", latency_ms=950),
        LogEvent(start + timedelta(seconds=1), "inventory-api", Severity.INFO, "slow request", latency_ms=1200),
    ]

    alerts = LogAnalyzer().analyze(events)

    assert any(alert.title == "inventory-api latency spike" for alert in alerts)
