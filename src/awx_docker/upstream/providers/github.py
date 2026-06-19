from pathlib import Path

from awx_docker.git_refs import resolve_ref
from awx_docker.upstream.github_client import fetch_signals, write_raw
from awx_docker.upstream.models import UpstreamProvider
from awx_docker.upstream.normalize import normalize_github_signals

from .base import ProviderResult


def collect(
    repository: str,
    requested_ref: str,
    *,
    policy: dict,
    github_token: str | None = None,
    evidence_dir: Path | None = None,
    resolved_revision: str | None = None,
    **_: object,
) -> ProviderResult:
    revision = resolved_revision or resolve_ref(repository, requested_ref)
    combined, checks = fetch_signals(
        repository,
        revision,
        github_token,
        checks_per_page=policy["github"]["check_runs"]["per_page"],
    )
    if evidence_dir is not None:
        write_raw(evidence_dir / "upstream" / "raw" / "github", combined, checks)

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
    return ProviderResult(
        repository=repository,
        requested_ref=requested_ref,
        resolved_revision=revision,
        provider=UpstreamProvider(name="github", signal_source="github-api"),
        signals=signals,
        raw={"github": {"combined_status": combined, "check_runs": checks}},
    )
