from pathlib import Path

import yaml

from .models import CiSignal, UpstreamDecision, UpstreamSignals


def load_policy(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def decide(signals: UpstreamSignals, policy: dict, mode: str) -> UpstreamDecision:
    if mode not in policy["modes"]:
        raise ValueError(f"unknown upstream-health mode: {mode}")

    ci = signals.ci
    blocking_failures = list(ci.blocking_failures)
    unknown_failures = list(ci.unknown_failures)
    pending = list(ci.pending)
    warnings = list(ci.warnings)

    if blocking_failures:
        base = "fail"
        reason = "; ".join(blocking_failures)
    elif unknown_failures:
        base = "fail"
        reason = "; ".join(unknown_failures)
    elif pending:
        base = "wait"
        reason = "; ".join(pending)
    elif not ci.available or ci.required_success_missing:
        base = "missing_build_signal"
        reason = _missing_signal_reason(ci)
    elif warnings:
        base = "warn"
        reason = "; ".join(warnings)
    else:
        return UpstreamDecision(
            state="pass",
            blocking=False,
            reason="No blocking upstream provider signals were found.",
        )

    mode_policy = policy["modes"][mode]
    signal_keys = {
        "warn": "warning_signal",
        "wait": "wait_signal",
        "fail": "fail_signal",
        "missing_build_signal": "missing_build_signal",
    }
    mapped = mode_policy[signal_keys[base]]
    return UpstreamDecision(state=mapped, blocking=mapped == "fail", reason=reason)


def decide_unknown(reason: str, policy: dict, mode: str) -> UpstreamDecision:
    if mode not in policy["modes"]:
        raise ValueError(f"unknown upstream-health mode: {mode}")
    mapped = policy["modes"][mode]["unknown_signal"]
    return UpstreamDecision(state=mapped, blocking=mapped == "fail", reason=reason)


def _missing_signal_reason(ci: CiSignal) -> str:
    if not ci.available:
        return f"no CI health signal available from provider {ci.provider}"
    return "required upstream build check was not observed as successful"
