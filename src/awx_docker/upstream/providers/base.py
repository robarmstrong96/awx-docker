from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from awx_docker.upstream.models import UpstreamProvider, UpstreamSignals


@dataclass(frozen=True)
class ProviderResult:
    repository: str
    requested_ref: str
    resolved_revision: str
    provider: UpstreamProvider
    signals: UpstreamSignals
    raw: dict[str, Any] = field(default_factory=dict)


class UpstreamProviderError(RuntimeError):
    pass


def require_signal_file(signal_file: Path | None) -> Path:
    if signal_file is None:
        raise UpstreamProviderError("--signal-file is required when --provider=file")
    return signal_file
