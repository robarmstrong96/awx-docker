from .models import CheckRunSignal, CombinedStatusSignal, UpstreamSignals

FAIL_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}
WAIT_STATUSES = {"queued", "in_progress", "pending", "requested", "waiting"}


def normalize_signals(combined: dict, checks: dict) -> UpstreamSignals:
    contexts = combined.get("statuses") or []
    check_runs = checks.get("check_runs") or []

    failing = []
    pending = []
    for run in check_runs:
        name = run.get("name") or "unnamed check"
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status in WAIT_STATUSES:
            pending.append(f"{name} ({status})")
        if conclusion in FAIL_CONCLUSIONS:
            failing.append(f"{name} ({conclusion})")

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
            pending=pending,
        ),
    )
