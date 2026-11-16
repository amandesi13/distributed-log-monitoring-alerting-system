"""The browser demo calls web/bridge.py; keep its JSON contract tested."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

import bridge  # noqa: E402

SAMPLE = (ROOT / "samples" / "service.log").read_text(encoding="utf-8")


def test_analyze_sample_log():
    result = json.loads(bridge.analyze(SAMPLE))

    assert result["ok"] is True
    assert len(result["events"]) == 10
    assert result["parse_errors"] == []
    titles = {alert["title"] for alert in result["alerts"]}
    assert "checkout-api error burst" in titles
    assert "inventory-api critical event" in titles
    for alert in result["alerts"]:
        assert alert["severity"] in {"low", "medium", "high", "critical"}
        assert alert["first_seen"] <= alert["last_seen"]


def test_thresholds_change_the_outcome():
    strict = json.loads(bridge.analyze(SAMPLE, error_threshold=10))
    assert "checkout-api error burst" not in {a["title"] for a in strict["alerts"]}

    sensitive = json.loads(bridge.analyze(SAMPLE, latency_threshold_ms=100))
    assert any(a["title"].endswith("latency spike") for a in sensitive["alerts"])


def test_bad_lines_are_reported_and_skipped():
    text = "garbage line\n" + SAMPLE + "\n{not json\n"
    result = json.loads(bridge.analyze(text))

    assert result["ok"] is True
    assert len(result["events"]) == 10
    bad_line = text.splitlines().index("{not json") + 1
    assert [e["line"] for e in result["parse_errors"]] == [1, bad_line]


def test_invalid_settings():
    assert json.loads(bridge.analyze(SAMPLE, window_seconds="abc"))["ok"] is False


def test_simulated_log_round_trips():
    text = bridge.simulate(events=120, seed=7)
    assert len(text.splitlines()) == 120

    result = json.loads(bridge.analyze(text))
    titles = {alert["title"] for alert in result["alerts"]}
    assert "checkout-api error burst" in titles
    assert "payment-worker repeated restarts" in titles
    assert "inventory-api critical event" in titles
