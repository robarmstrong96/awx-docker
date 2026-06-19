from pathlib import Path

from awx_docker.evidence import write_env, write_json, write_markdown

from .models import UpstreamHealthReport, UpstreamProvider, UpstreamSubject
from .normalize import empty_signals, normalize_github_signals
from .policy import decide, decide_unknown, load_policy
from .provider_registry import select_provider

SCHEMA_VERSION = "awx-docker.upstream-health/v2"


def build_report(
    repository: str,
    requested_ref: str,
    resolved_revision: str,
    combined: dict,
    checks: dict,
    policy: dict,
    mode: str,
) -> UpstreamHealthReport:
    decisions = policy["decisions"]
    signals = normalize_github_signals(
        combined,
        checks,
        fail_conclusions=set(decisions["fail_on_check_conclusions"]),
        wait_statuses=set(decisions["wait_on_check_statuses"]),
        blocking_failure_name_patterns=decisions["blocking_failed_check_name_patterns"],
        non_blocking_failure_name_patterns=decisions["non_blocking_failed_check_name_patterns"],
        required_success_name_patterns=decisions["required_success_check_name_patterns"],
    )
    return UpstreamHealthReport(
        schema_version=SCHEMA_VERSION,
        subject=UpstreamSubject(
            repository=repository,
            requested_ref=requested_ref,
            resolved_revision=resolved_revision,
        ),
        provider=UpstreamProvider(name="github", signal_source="github-api"),
        signals=signals,
        decision=decide(signals, policy, mode),
        waiver=None,
    )


def write_upstream_health(
    repository: str,
    requested_ref: str,
    evidence_dir: Path,
    policy_path: Path,
    mode: str,
    github_token: str | None = None,
    provider: str = "auto",
    signal_file: Path | None = None,
    resolved_revision: str | None = None,
) -> UpstreamHealthReport:
    policy = load_policy(policy_path)
    try:
        provider_name, collect = select_provider(repository, provider)
        result = collect(
            repository,
            requested_ref,
            policy=policy,
            github_token=github_token,
            evidence_dir=evidence_dir,
            signal_file=signal_file,
            resolved_revision=resolved_revision,
            mode=mode,
        )
    except Exception as exc:
        report = UpstreamHealthReport(
            schema_version=SCHEMA_VERSION,
            subject=UpstreamSubject(
                repository=repository,
                requested_ref=requested_ref,
                resolved_revision=resolved_revision or "unknown",
            ),
            provider=UpstreamProvider(name=provider, signal_source="unavailable"),
            signals=empty_signals(provider),
            decision=decide_unknown(
                f"Could not collect upstream provider signals: {exc}", policy, mode
            ),
            waiver=None,
        )
        _write_report(evidence_dir, report)
        return report

    report = UpstreamHealthReport(
        schema_version=SCHEMA_VERSION,
        subject=UpstreamSubject(
            repository=result.repository,
            requested_ref=result.requested_ref,
            resolved_revision=result.resolved_revision,
        ),
        provider=result.provider,
        signals=result.signals,
        decision=decide(result.signals, policy, mode),
        waiver=None,
    )
    if provider_name != result.provider.name and result.provider.name != "file":
        raise ValueError(f"provider mismatch: selected {provider_name}, got {result.provider.name}")
    _write_report(evidence_dir, report)
    return report


def _write_report(evidence_dir: Path, report: UpstreamHealthReport) -> None:
    data = report.to_dict()
    ci = report.signals.ci
    write_json(evidence_dir / "upstream-health.json", data)
    write_markdown(
        evidence_dir / "upstream-health.md",
        "Upstream Health",
        {
            "repository": f"`{report.subject.repository}`",
            "requested_ref": f"`{report.subject.requested_ref}`",
            "resolved_revision": f"`{report.subject.resolved_revision}`",
            "provider": f"`{report.provider.name}`",
            "ci_available": f"`{str(ci.available).lower()}`",
            "ci_total": str(ci.total),
            "blocking_failures": str(len(ci.blocking_failures)),
            "non_blocking_failures": str(len(ci.non_blocking_failures)),
            "unknown_failures": str(len(ci.unknown_failures)),
            "warnings": str(len(ci.warnings)),
            "decision": f"`{report.decision.state}`",
            "reason": report.decision.reason,
        },
    )
    write_env(
        evidence_dir / "upstream-health.env",
        {
            "UPSTREAM_REPOSITORY": report.subject.repository,
            "UPSTREAM_REQUESTED_REF": report.subject.requested_ref,
            "UPSTREAM_RESOLVED_REVISION": report.subject.resolved_revision,
            "UPSTREAM_PROVIDER": report.provider.name,
            "UPSTREAM_HEALTH_STATE": report.decision.state,
            "UPSTREAM_HEALTH_BLOCKING": str(report.decision.blocking).lower(),
            "UPSTREAM_HEALTH_REASON": report.decision.reason,
        },
    )
