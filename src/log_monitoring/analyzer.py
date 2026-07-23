from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean

from .models import Alert, AlertSeverity, LogEvent, MonitorConfig, Severity


class LogAnalyzer:
    def __init__(self, config: MonitorConfig | None = None) -> None:
        self.config = config or MonitorConfig()

    def analyze(self, events: list[LogEvent]) -> list[Alert]:
        if not events:
            return []

        ordered_events = sorted(events, key=lambda event: event.timestamp)
        alerts: list[Alert] = []
        grouped: dict[str, list[LogEvent]] = defaultdict(list)
        for event in ordered_events:
            grouped[event.service].append(event)

        for service, service_events in grouped.items():
            alerts.extend(self._error_burst_alerts(service, service_events))
            alerts.extend(self._latency_spike_alerts(service, service_events))
            alerts.extend(self._restart_alerts(service, service_events))
            alerts.extend(self._critical_alerts(service, service_events))
            heartbeat_alert = self._heartbeat_alert(service, service_events, ordered_events[-1].timestamp)
            if heartbeat_alert:
                alerts.append(heartbeat_alert)

        return sorted(alerts, key=lambda alert: (alert.severity.value, alert.service, alert.title))

    def _error_burst_alerts(self, service: str, events: list[LogEvent]) -> list[Alert]:
        alerts: list[Alert] = []
        window = timedelta(seconds=self.config.window_seconds)
        error_events = [event for event in events if event.severity in {Severity.ERROR, Severity.CRITICAL}]

        for index, event in enumerate(error_events):
            window_events = [candidate for candidate in error_events[index:] if candidate.timestamp <= event.timestamp + window]
            if len(window_events) >= self.config.error_threshold:
                alerts.append(
                    Alert(
                        service=service,
                        severity=AlertSeverity.HIGH,
                        title=f"{service} error burst",
                        detail=f"{len(window_events)} error events observed in the last {self.config.window_seconds} seconds.",
                        hint="Inspect recent deployment, downstream dependency health, and retry saturation.",
                        evidence_count=len(window_events),
                        first_seen=window_events[0].timestamp,
                        last_seen=window_events[-1].timestamp,
                    )
                )
                break
        return alerts

    def _latency_spike_alerts(self, service: str, events: list[LogEvent]) -> list[Alert]:
        slow_events = [event for event in events if event.latency_ms is not None and event.latency_ms >= self.config.latency_threshold_ms]
        if len(slow_events) < 2:
            return []

        average_latency = mean(event.latency_ms for event in slow_events if event.latency_ms is not None)
        return [
            Alert(
                service=service,
                severity=AlertSeverity.MEDIUM,
                title=f"{service} latency spike",
                detail=f"{len(slow_events)} requests exceeded {self.config.latency_threshold_ms:.0f} ms; average slow latency was {average_latency:.0f} ms.",
                hint="Check saturation, queue depth, database timings, and upstream timeout settings.",
                evidence_count=len(slow_events),
                first_seen=slow_events[0].timestamp,
                last_seen=slow_events[-1].timestamp,
            )
        ]

    def _restart_alerts(self, service: str, events: list[LogEvent]) -> list[Alert]:
        restart_events = [event for event in events if "restart" in event.message.lower()]
        if len(restart_events) < self.config.restart_threshold:
            return []

        return [
            Alert(
                service=service,
                severity=AlertSeverity.HIGH,
                title=f"{service} repeated restarts",
                detail=f"{len(restart_events)} restart-related events observed.",
                hint="Inspect crash loops, memory limits, dependency readiness, and startup probes.",
                evidence_count=len(restart_events),
                first_seen=restart_events[0].timestamp,
                last_seen=restart_events[-1].timestamp,
            )
        ]

    def _critical_alerts(self, service: str, events: list[LogEvent]) -> list[Alert]:
        critical_events = [event for event in events if event.severity == Severity.CRITICAL]
        if not critical_events:
            return []

        return [
            Alert(
                service=service,
                severity=AlertSeverity.CRITICAL,
                title=f"{service} critical event",
                detail=critical_events[-1].message,
                hint="Escalate immediately and preserve logs, traces, and deployment context.",
                evidence_count=len(critical_events),
                first_seen=critical_events[0].timestamp,
                last_seen=critical_events[-1].timestamp,
            )
        ]

    def _heartbeat_alert(self, service: str, events: list[LogEvent], last_seen_global: datetime) -> Alert | None:
        heartbeat_events = [event for event in events if "heartbeat" in event.message.lower()]
        if not heartbeat_events:
            return None

        last_heartbeat = heartbeat_events[-1]
        gap = (last_seen_global - last_heartbeat.timestamp).total_seconds()
        if gap < self.config.heartbeat_timeout_seconds:
            return None

        return Alert(
            service=service,
            severity=AlertSeverity.MEDIUM,
            title=f"{service} missing heartbeat",
            detail=f"No heartbeat observed for {gap:.0f} seconds.",
            hint="Check pod health, service discovery, network policy, and node pressure.",
            evidence_count=1,
            first_seen=last_heartbeat.timestamp,
            last_seen=last_seen_global,
        )
