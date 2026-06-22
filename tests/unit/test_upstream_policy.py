import json
from copy import deepcopy
from pathlib import Path

from awx_docker.upstream.policy import load_policy
from awx_docker.upstream.provider_registry import select_provider
from awx_docker.upstream.report import build_report, write_upstream_health

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/github"
POLICY = load_policy(ROOT / "rules/upstream-health.yml")


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
    assert report.signals.ci.blocking_failures == ["Build (failure)"]


def test_container_build_failure_blocks() -> None:
    combined, checks = load_fixture("healthy")
    checks["check_runs"] = [
        {"name": "Container build", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
    ]
    report = build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        combined,
        checks,
        POLICY,
        "scheduled-build",
    )

    assert report.decision.state == "fail"
    assert report.signals.ci.blocking_failures == ["Container build (failure)"]


def test_sonarcloud_failure_is_non_blocking_evidence() -> None:
    report = report_for("non-blocking-failure", "publication")

    assert report.decision.state == "pass"
    assert report.signals.ci.blocking_failures == []
    assert report.signals.ci.non_blocking_failures == ["SonarCloud Code Analysis (failure)"]


def test_lint_static_analysis_and_docs_failures_are_non_blocking_evidence() -> None:
    combined, checks = load_fixture("healthy")
    checks["check_runs"] = [
        {"name": "Build", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "failure"},
        {"name": "static-analysis", "status": "completed", "conclusion": "failure"},
        {"name": "docs", "status": "completed", "conclusion": "failure"},
    ]
    report = build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        combined,
        checks,
        POLICY,
        "publication",
    )

    assert report.decision.state == "pass"
    assert report.signals.ci.blocking_failures == []
    assert report.signals.ci.non_blocking_failures == [
        "lint (failure)",
        "static-analysis (failure)",
        "docs (failure)",
    ]


def test_release_branch_dispatch_failures_are_non_blocking_evidence() -> None:
    combined, checks = load_fixture("healthy")
    checks["check_runs"] = [
        {"name": "Build", "status": "completed", "conclusion": "success"},
        {
            "name": "Dispatch CI to release branches",
            "status": "completed",
            "conclusion": "failure",
        },
    ]
    report = build_report(
        "https://github.com/ansible/awx.git",
        "devel",
        "a" * 40,
        combined,
        checks,
        POLICY,
        "publication",
    )

    assert report.decision.state == "pass"
    assert report.signals.ci.blocking_failures == []
    assert report.signals.ci.non_blocking_failures == [
        "Dispatch CI to release branches (failure)",
    ]


def test_unclassified_failing_check_blocks() -> None:
    assert decision_for("failing-check", "scheduled-build") == "fail"
    assert decision_for("failing-check", "local") == "fail"
    assert decision_for("failing-check", "publication") == "fail"


def test_pending_check_fails_scheduled_build_but_warns_local() -> None:
    assert decision_for("pending-check", "scheduled-build") == "fail"
    assert decision_for("pending-check", "local") == "warn"


def test_check_run_classification_comes_from_policy() -> None:
    relaxed_policy = deepcopy(POLICY)
    relaxed_policy["decisions"]["fail_on_check_conclusions"] = []

    report = report_for("build-failure", policy=relaxed_policy)

    assert report.signals.ci.blocking_failures == []
    assert report.decision.state == "warn"


def test_required_build_signal_warns_scheduled_and_fails_publication() -> None:
    assert decision_for("no-build-success", "scheduled-build") == "warn"
    assert decision_for("no-build-success", "local") == "warn"
    assert decision_for("no-build-success", "publication") == "fail"


def test_missing_signal_warns_scheduled_build_and_fails_publication() -> None:
    assert decision_for("missing-signal", "scheduled-build") == "warn"
    assert decision_for("missing-signal", "local") == "warn"
    assert decision_for("missing-signal", "publication") == "fail"


def test_unresolvable_ref_writes_unknown_evidence(monkeypatch, tmp_path: Path) -> None:
    def fail_resolve(repo: str, ref: str) -> str:
        raise RuntimeError("missing ref")

    monkeypatch.setattr("awx_docker.upstream.providers.github.resolve_ref", fail_resolve)

    report = write_upstream_health(
        "https://github.com/ansible/awx.git",
        "missing",
        tmp_path,
        ROOT / "rules/upstream-health.yml",
        "scheduled-build",
    )

    assert report.decision.state == "warn"
    assert report.subject.resolved_revision == "unknown"
    assert (tmp_path / "upstream-health.json").exists()


def test_auto_provider_selects_github_for_github_repositories() -> None:
    provider_name, _ = select_provider("https://github.com/ansible/awx.git", "auto")

    assert provider_name == "github"


def test_auto_provider_selects_generic_git_for_other_repositories() -> None:
    provider_name, _ = select_provider("https://git.example.test/awx.git", "auto")

    assert provider_name == "generic-git"


def test_generic_git_provider_warns_without_ci_signal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "awx_docker.upstream.providers.generic_git.resolve_ref",
        lambda repo, ref: "b" * 40,
    )

    report = write_upstream_health(
        "https://git.example.test/awx.git",
        "devel",
        tmp_path,
        ROOT / "rules/upstream-health.yml",
        "scheduled-build",
        provider="generic-git",
    )

    assert report.provider.name == "generic-git"
    assert report.decision.state == "warn"
    assert report.signals.ci.available is False


def test_generic_git_provider_fails_publication_without_ci_signal(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "awx_docker.upstream.providers.generic_git.resolve_ref",
        lambda repo, ref: "b" * 40,
    )

    report = write_upstream_health(
        "https://git.example.test/awx.git",
        "devel",
        tmp_path,
        ROOT / "rules/upstream-health.yml",
        "publication",
        provider="generic-git",
    )

    assert report.decision.state == "fail"


def test_generic_git_provider_verifies_supplied_revision_for_publication(
    monkeypatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        "awx_docker.upstream.providers.generic_git.verify_revision_reachable",
        lambda repo, revision: calls.append((repo, revision)) or True,
    )

    report = write_upstream_health(
        "https://git.example.test/awx.git",
        "devel",
        tmp_path,
        ROOT / "rules/upstream-health.yml",
        "publication",
        provider="generic-git",
        resolved_revision="b" * 40,
    )

    assert calls == [("https://git.example.test/awx.git", "b" * 40)]
    assert report.subject.resolved_revision == "b" * 40


def test_generic_git_provider_fails_unreachable_supplied_revision_for_publication(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "awx_docker.upstream.providers.generic_git.verify_revision_reachable",
        lambda repo, revision: False,
    )

    report = write_upstream_health(
        "https://git.example.test/awx.git",
        "devel",
        tmp_path,
        ROOT / "rules/upstream-health.yml",
        "publication",
        provider="generic-git",
        resolved_revision="b" * 40,
    )

    assert report.decision.state == "fail"
    assert "not reachable" in report.decision.reason


def test_file_provider_reads_normalized_signals(tmp_path: Path) -> None:
    signal_file = tmp_path / "signals.json"
    signal_file.write_text(
        json.dumps(
            {
                "resolved_revision": "c" * 40,
                "signals": {
                    "ci": {
                        "provider": "external-ci",
                        "available": True,
                        "total": 1,
                        "blocking_failures": ["Container build (failure)"],
                        "non_blocking_failures": [],
                        "unknown_failures": [],
                        "pending": [],
                        "warnings": [],
                        "required_success_observed": False,
                        "required_success_missing": False,
                    }
                },
            }
        )
    )

    report = write_upstream_health(
        "https://git.example.test/awx.git",
        "devel",
        tmp_path / "evidence",
        ROOT / "rules/upstream-health.yml",
        "scheduled-build",
        provider="file",
        signal_file=signal_file,
    )

    assert report.decision.state == "fail"
    assert report.subject.resolved_revision == "c" * 40
