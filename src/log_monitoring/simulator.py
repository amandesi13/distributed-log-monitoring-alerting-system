from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SERVICES = ["checkout-api", "payment-worker", "inventory-api"]


def generate_log_file(path: str | Path, events: int = 100, seed: int = 7) -> Path:
    random.seed(seed)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc).replace(microsecond=0)

    with output_path.open("w", encoding="utf-8") as handle:
        for index in range(events):
            service = SERVICES[index % len(SERVICES)]
            timestamp = start + timedelta(seconds=index * 3)
            severity = "info"
            latency_ms = random.randint(40, 220)
            message = "request completed"

            # Incidents pin their own service: the round-robin above would put
            # most of these indices on other services and the alerts never fire.
            if 25 <= index <= 34:
                service = "checkout-api"
                severity = "error"
                latency_ms = random.randint(950, 1500)
                message = "database timeout latency_ms={}ms".format(latency_ms)
            elif index in {45, 48, 51}:
                service = "payment-worker"
                severity = "warning"
                message = "service restart requested"
            elif index == 70:
                service = "inventory-api"
                severity = "critical"
                message = "dependency unavailable for stock reservation"
            elif index % 15 == 0:
                message = "heartbeat ok"

            handle.write(
                json.dumps(
                    {
                        "timestamp": timestamp.isoformat(),
                        "service": service,
                        "severity": severity,
                        "message": message,
                        "latency_ms": latency_ms,
                        "trace_id": f"trace-{index:04d}",
                    }
                )
                + "\n"
            )

    return output_path
