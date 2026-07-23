from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Iterable, Protocol

from .models import Alert


class AlertSink(Protocol):
    def publish(self, alerts: Iterable[Alert]) -> None:
        ...


class ConsoleAlertSink:
    def __init__(self, output_format: str = "text") -> None:
        self.output_format = output_format

    def publish(self, alerts: Iterable[Alert]) -> None:
        alert_list = list(alerts)
        if self.output_format == "json":
            print(json.dumps([_json_ready(alert) for alert in alert_list], indent=2))
            return

        if not alert_list:
            print("No alerts detected.")
            return

        for alert in alert_list:
            print(f"[{alert.severity.value.upper()}] {alert.title}")
            print(alert.detail)
            print(f"Hint: {alert.hint}")
            print()


class MemoryAlertSink:
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def publish(self, alerts: Iterable[Alert]) -> None:
        self.alerts.extend(alerts)


def _json_ready(alert: Alert) -> dict[str, object]:
    def convert(value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value

    return {key: convert(value) for key, value in asdict(alert).items()}
