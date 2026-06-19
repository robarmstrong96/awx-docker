import json
from pathlib import Path

from awx_docker.upstream.normalize import normalize_signals
from awx_docker.upstream.policy import decide, load_policy
from awx_docker.upstream.report import write_upstream_health

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


def test_unresolvable_ref_writes_unknown_evidence(monkeypatch, tmp_path: Path) -> None:
    def fail_resolve(repo: str, ref: str) -> str:
        raise RuntimeError("missing ref")

    monkeypatch.setattr("awx_docker.upstream.report.resolve_ref", fail_resolve)

    report = write_upstream_health(
        "https://github.com/ansible/awx.git",
        "missing",
        tmp_path,
        ROOT / "policies/upstream-health.yml",
        "scheduled-build",
    )

    assert report.decision.state == "warn"
    assert report.subject.resolved_sha == "unknown"
    assert (tmp_path / "upstream-health.json").exists()
