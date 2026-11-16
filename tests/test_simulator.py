from log_monitoring.analyzer import LogAnalyzer
from log_monitoring.collector import FileLogCollector
from log_monitoring.simulator import generate_log_file


def test_simulated_incidents_raise_their_alerts(tmp_path) -> None:
    path = generate_log_file(tmp_path / "simulated.log", events=120, seed=7)

    alerts = LogAnalyzer().analyze(FileLogCollector(path).collect())
    titles = {alert.title for alert in alerts}

    assert "checkout-api error burst" in titles
    assert "checkout-api latency spike" in titles
    assert "payment-worker repeated restarts" in titles
    assert "inventory-api critical event" in titles


def test_simulator_is_deterministic_for_a_seed(tmp_path) -> None:
    a = generate_log_file(tmp_path / "a.log", events=80, seed=3).read_text(encoding="utf-8")
    b = generate_log_file(tmp_path / "b.log", events=80, seed=3).read_text(encoding="utf-8")

    strip = lambda text: [line.split('"service"', 1)[1] for line in text.splitlines()]
    assert strip(a) == strip(b)
