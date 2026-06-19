from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DecisionState = Literal["pass", "warn", "wait", "fail", "unknown", "waived"]


@dataclass(frozen=True)
class UpstreamSubject:
    repository: str
    requested_ref: str
    resolved_revision: str


@dataclass(frozen=True)
class UpstreamProvider:
    name: str
    signal_source: str


@dataclass(frozen=True)
class CiSignal:
    provider: str
    available: bool
    total: int
    blocking_failures: list[str] = field(default_factory=list)
    non_blocking_failures: list[str] = field(default_factory=list)
    unknown_failures: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_success_observed: bool = False
    required_success_missing: bool = False


@dataclass(frozen=True)
class UpstreamSignals:
    ci: CiSignal


@dataclass(frozen=True)
class UpstreamDecision:
    state: DecisionState
    blocking: bool
    reason: str


@dataclass(frozen=True)
class UpstreamHealthReport:
    schema_version: str
    subject: UpstreamSubject
    provider: UpstreamProvider
    signals: UpstreamSignals
    decision: UpstreamDecision
    waiver: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
