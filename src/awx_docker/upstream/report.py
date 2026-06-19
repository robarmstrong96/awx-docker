from pathlib import Path

from awx_docker.evidence import write_env, write_json, write_markdown
from awx_docker.git_refs import resolve_ref

from .github_client import fetch_signals, write_raw
from .models import UpstreamHealthReport, UpstreamSubject
from .normalize import normalize_signals
from .policy import decide, decide_unknown, load_policy

SCHEMA_VERSION = "awx-docker.upstream-health/v1"


def build_report(
    repo: str,
    requested_ref: str,
    resolved_sha: str,
    combined: dict,
    checks: dict,
    policy: dict,
    mode: str,
) -> UpstreamHealthReport:
    signals = normalize_signals(combined, checks)
    return UpstreamHealthReport(
        schema_version=SCHEMA_VERSION,
        subject=UpstreamSubject(repo=repo, requested_ref=requested_ref, resolved_sha=resolved_sha),
        signals=signals,
        decision=decide(signals, policy, mode),
        waiver=None,
    )


def write_upstream_health(
    repo: str,
    requested_ref: str,
    evidence_dir: Path,
    policy_path: Path,
    mode: str,
    github_token: str | None = None,
) -> UpstreamHealthReport:
    resolved_sha = resolve_ref(repo, requested_ref)
    policy = load_policy(policy_path)
    try:
        combined, checks = fetch_signals(repo, resolved_sha, github_token)
        write_raw(evidence_dir / "upstream-raw", combined, checks)
    except Exception as exc:
        combined = {"state": "none", "statuses": []}
        checks = {"check_runs": []}
        report = build_report(repo, requested_ref, resolved_sha, combined, checks, policy, mode)
        report = UpstreamHealthReport(
            schema_version=report.schema_version,
            subject=report.subject,
            signals=report.signals,
            decision=decide_unknown(
                f"Could not collect GitHub upstream signals: {exc}",
                policy,
                mode,
            ),
            waiver=None,
        )
    else:
        report = build_report(repo, requested_ref, resolved_sha, combined, checks, policy, mode)

    data = report.to_dict()
    write_json(evidence_dir / "upstream-health.json", data)
    write_markdown(
        evidence_dir / "upstream-health.md",
        "Upstream AWX Health",
        {
            "repo": f"`{repo}`",
            "requested_ref": f"`{requested_ref}`",
            "resolved_sha": f"`{resolved_sha}`",
            "combined_status": f"`{report.signals.combined_status.state}`",
            "check_runs": str(report.signals.check_runs.total),
            "decision": f"`{report.decision.state}`",
            "reason": report.decision.reason,
        },
    )
    write_env(
        evidence_dir / "upstream-health.env",
        {
            "AWX_REPO": repo,
            "AWX_REQUESTED_REF": requested_ref,
            "AWX_RESOLVED_REF": resolved_sha,
            "UPSTREAM_HEALTH_STATE": report.decision.state,
            "UPSTREAM_HEALTH_BLOCKING": str(report.decision.blocking).lower(),
            "UPSTREAM_HEALTH_REASON": report.decision.reason,
        },
    )
    return report
