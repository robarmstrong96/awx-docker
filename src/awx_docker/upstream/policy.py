from pathlib import Path

import yaml

from .models import UpstreamDecision, UpstreamSignals


def load_policy(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def decide(signals: UpstreamSignals, policy: dict, mode: str) -> UpstreamDecision:
    if mode not in policy["modes"]:
        raise ValueError(f"unknown upstream-health mode: {mode}")

    combined_state = signals.combined_status.state
    failing = list(signals.check_runs.failing)
    pending = list(signals.check_runs.pending)

    if combined_state in policy["decisions"]["fail_on_combined_states"]:
        failing.append(f"combined commit status is {combined_state}")
    wait_states = policy["decisions"]["wait_on_combined_states"]
    if signals.combined_status.available and combined_state in wait_states:
        pending.append(f"combined commit status is {combined_state}")

    if failing:
        base = "fail"
        reason = "; ".join(failing)
    elif pending:
        base = "wait"
        reason = "; ".join(pending)
    elif not signals.combined_status.available and not signals.check_runs.available:
        base = "warn"
        reason = (
            "GitHub exposed no combined status contexts or check runs for this upstream commit."
        )
    else:
        return UpstreamDecision(
            state="pass",
            blocking=False,
            reason="No failing or incomplete upstream statuses/check runs were found.",
        )

    mode_policy = policy["modes"][mode]
    signal_keys = {"warn": "warning_signal", "wait": "wait_signal", "fail": "fail_signal"}
    mapped = mode_policy[signal_keys[base]]
    return UpstreamDecision(state=mapped, blocking=mapped == "fail", reason=reason)


def decide_unknown(reason: str, policy: dict, mode: str) -> UpstreamDecision:
    if mode not in policy["modes"]:
        raise ValueError(f"unknown upstream-health mode: {mode}")
    mapped = policy["modes"][mode]["unknown_signal"]
    return UpstreamDecision(state=mapped, blocking=mapped == "fail", reason=reason)
