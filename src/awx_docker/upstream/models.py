from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DecisionState = Literal["pass", "warn", "wait", "fail", "unknown", "waived"]


@dataclass(frozen=True)
class UpstreamSubject:
    repo: str
    requested_ref: str
    resolved_sha: str


@dataclass(frozen=True)
class CombinedStatusSignal:
    available: bool
    state: str
    contexts: int


@dataclass(frozen=True)
class CheckRunSignal:
    available: bool
    total: int
    failing: list[str] = field(default_factory=list)
    non_blocking_failures: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UpstreamSignals:
    combined_status: CombinedStatusSignal
    check_runs: CheckRunSignal


@dataclass(frozen=True)
class UpstreamDecision:
    state: DecisionState
    blocking: bool
    reason: str


@dataclass(frozen=True)
class UpstreamHealthReport:
    schema_version: str
    subject: UpstreamSubject
    signals: UpstreamSignals
    decision: UpstreamDecision
    waiver: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
