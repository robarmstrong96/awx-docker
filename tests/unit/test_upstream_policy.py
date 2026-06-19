import json
from pathlib import Path

from awx_docker.upstream.normalize import normalize_signals
from awx_docker.upstream.policy import decide, load_policy

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/github"
POLICY = load_policy(ROOT / "policies/upstream-health.yml")


def load_fixture(name: str) -> tuple[dict, dict]:
    directory = FIXTURES / name
    combined = json.loads((directory / "combined-status.json").read_text())
    checks = json.loads((directory / "check-runs.json").read_text())
    return combined, checks


def decision_for(name: str, mode: str = "scheduled-build") -> str:
    combined, checks = load_fixture(name)
    signals = normalize_signals(combined, checks)
    return decide(signals, POLICY, mode).state


def test_healthy_signals_pass() -> None:
    assert decision_for("healthy") == "pass"


def test_failing_check_fails() -> None:
    assert decision_for("failing-check") == "fail"


def test_pending_check_fails_scheduled_build_but_warns_local() -> None:
    assert decision_for("pending-check", "scheduled-build") == "fail"
    assert decision_for("pending-check", "local") == "warn"


def test_missing_signal_warns_scheduled_build_and_fails_publication() -> None:
    assert decision_for("missing-signal", "scheduled-build") == "warn"
    assert decision_for("missing-signal", "publication") == "fail"
