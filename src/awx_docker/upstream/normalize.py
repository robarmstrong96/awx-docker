import re

from .models import CheckRunSignal, CombinedStatusSignal, UpstreamSignals


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def normalize_signals(
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

    failing = []
    non_blocking_failures = []
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
                failing.append(formatted)
            else:
                warnings.append(f"unclassified failing check: {formatted}")

    if check_runs and required_success_name_patterns and not observed_required_success:
        warnings.append("required upstream build check was not observed as successful")

    return UpstreamSignals(
        combined_status=CombinedStatusSignal(
            available=bool(contexts),
            state=combined.get("state") or "none",
            contexts=len(contexts),
        ),
        check_runs=CheckRunSignal(
            available=bool(check_runs),
            total=len(check_runs),
            failing=failing,
            non_blocking_failures=non_blocking_failures,
            pending=pending,
            warnings=warnings,
        ),
    )
