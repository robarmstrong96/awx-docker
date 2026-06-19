import re

from .models import CiSignal, UpstreamSignals


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def empty_signals(provider: str) -> UpstreamSignals:
    return UpstreamSignals(
        ci=CiSignal(
            provider=provider,
            available=False,
            total=0,
            warnings=[],
            required_success_missing=True,
        )
    )


def normalize_github_signals(
    combined: dict,
    checks: dict,
    *,
    fail_conclusions: set[str],
    wait_statuses: set[str],
    blocking_failure_name_patterns: list[str],
    non_blocking_failure_name_patterns: list[str],
    required_success_name_patterns: list[str],
) -> UpstreamSignals:
    contexts = combined.get("statuses") or []
    check_runs = checks.get("check_runs") or []

    blocking_failures = []
    non_blocking_failures = []
    unknown_failures = []
    pending = []
    warnings = []
    observed_required_success = False
    for run in check_runs:
        name = run.get("name") or "unnamed check"
        status = run.get("status")
        conclusion = run.get("conclusion")
        if conclusion == "success" and _matches_any(name, required_success_name_patterns):
            observed_required_success = True
        if status in wait_statuses:
            pending.append(f"{name} ({status})")
        if conclusion in fail_conclusions:
            formatted = f"{name} ({conclusion})"
            if _matches_any(name, non_blocking_failure_name_patterns):
                non_blocking_failures.append(formatted)
            elif _matches_any(name, blocking_failure_name_patterns):
                blocking_failures.append(formatted)
            else:
                unknown_failures.append(f"unclassified failing check: {formatted}")

    required_success_missing = (
        bool(required_success_name_patterns) and not observed_required_success
    )

    combined_state = combined.get("state") or "none"
    if not check_runs and contexts and combined_state in {"failure", "error"}:
        warnings.append(f"combined commit status is {combined_state}")
    if contexts and combined_state == "pending":
        pending.append(f"combined commit status is {combined_state}")

    return UpstreamSignals(
        ci=CiSignal(
            provider="github",
            available=bool(check_runs),
            total=len(check_runs),
            blocking_failures=blocking_failures,
            non_blocking_failures=non_blocking_failures,
            unknown_failures=unknown_failures,
            pending=pending,
            warnings=warnings,
            required_success_observed=observed_required_success,
            required_success_missing=required_success_missing,
        ),
    )
