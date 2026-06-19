import json
from copy import deepcopy
from pathlib import Path

from awx_docker.upstream.policy import load_policy
from awx_docker.upstream.report import build_report, write_upstream_health

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/github"
POLICY = load_policy(ROOT / "policies/upstream-health.yml")


def load_fixture(name: str) -> tuple[dict, dict]:
    directory = FIXTURES / name
    combined = json.loads((directory / "combined-status.json").read_text())
    checks = json.loads((directory / "check-runs.json").read_text())
    return combined, checks


def report_for(name: str, mode: str = "scheduled-build", policy: dict | None = None):
    combined, checks = load_fixture(name)
    return build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        combined,
        checks,
        policy or POLICY,
        mode,
    )


def decision_for(name: str, mode: str = "scheduled-build", policy: dict | None = None) -> str:
    return report_for(name, mode, policy).decision.state


def test_healthy_signals_pass() -> None:
    assert decision_for("healthy") == "pass"


def test_build_failure_blocks() -> None:
    report = report_for("build-failure")

    assert report.decision.state == "fail"
    assert report.signals.check_runs.failing == ["Build (failure)"]


def test_sonarcloud_failure_is_non_blocking_evidence() -> None:
    report = report_for("non-blocking-failure", "publication")

    assert report.decision.state == "pass"
    assert report.signals.check_runs.failing == []
    assert report.signals.check_runs.non_blocking_failures == ["SonarCloud Code Analysis (failure)"]


def test_unclassified_failing_check_warns_and_publication_fails() -> None:
    assert decision_for("failing-check", "scheduled-build") == "warn"
    assert decision_for("failing-check", "local") == "warn"
    assert decision_for("failing-check", "publication") == "fail"


def test_pending_check_fails_scheduled_build_but_warns_local() -> None:
    assert decision_for("pending-check", "scheduled-build") == "fail"
    assert decision_for("pending-check", "local") == "warn"


def test_check_run_classification_comes_from_policy() -> None:
    relaxed_policy = deepcopy(POLICY)
    relaxed_policy["decisions"]["fail_on_check_conclusions"] = []

    report = report_for("build-failure", policy=relaxed_policy)

    assert report.signals.check_runs.failing == []
    assert report.decision.state == "warn"


def test_required_build_signal_warns_scheduled_and_fails_publication() -> None:
    assert decision_for("failing-check", "scheduled-build") == "warn"
    assert decision_for("failing-check", "publication") == "fail"


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
