from log_monitoring.models import Severity
from log_monitoring.parser import parse_log_line


def test_parse_json_log_line() -> None:
    event = parse_log_line(
        '{"timestamp":"2026-07-23T10:00:00Z","service":"checkout-api","severity":"error","message":"timeout","latency_ms":1200}'
    )

    assert event.service == "checkout-api"
    assert event.severity == Severity.ERROR
    assert event.latency_ms == 1200.0


def test_parse_text_log_line_with_latency() -> None:
    event = parse_log_line("2026-07-23T10:00:00Z inventory-api WARN request slow latency=950ms")

    assert event.service == "inventory-api"
    assert event.severity == Severity.WARNING
    assert event.latency_ms == 950.0
