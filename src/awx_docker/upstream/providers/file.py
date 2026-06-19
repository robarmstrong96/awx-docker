import json
from pathlib import Path

from awx_docker.upstream.models import CiSignal, UpstreamProvider, UpstreamSignals

from .base import ProviderResult, require_signal_file


def collect(
    repository: str,
    requested_ref: str,
    *,
    signal_file: Path | None = None,
    resolved_revision: str | None = None,
    **_: object,
) -> ProviderResult:
    path = require_signal_file(signal_file)
    data = json.loads(path.read_text())
    subject = data.get("subject", {})
    provider = data.get("provider", {})
    signals = data.get("signals", {})
    ci = signals.get("ci", signals)

    provider_name = provider.get("name") or data.get("provider_name") or "file"
    revision = (
        resolved_revision
        or data.get("resolved_revision")
        or subject.get("resolved_revision")
        or subject.get("resolved_sha")
        or "unknown"
    )
    return ProviderResult(
        repository=repository,
        requested_ref=requested_ref,
        resolved_revision=revision,
        provider=UpstreamProvider(name="file", signal_source=str(path)),
        signals=UpstreamSignals(
            ci=CiSignal(
                provider=provider_name,
                available=bool(ci.get("available", False)),
                total=int(ci.get("total", 0)),
                blocking_failures=list(ci.get("blocking_failures", ci.get("failing", []))),
                non_blocking_failures=list(ci.get("non_blocking_failures", [])),
                unknown_failures=list(ci.get("unknown_failures", [])),
                pending=list(ci.get("pending", [])),
                warnings=list(ci.get("warnings", [])),
                required_success_observed=bool(ci.get("required_success_observed", False)),
                required_success_missing=bool(ci.get("required_success_missing", False)),
            )
        ),
        raw={"file": data},
    )
