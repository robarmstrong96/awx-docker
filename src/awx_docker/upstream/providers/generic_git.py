from awx_docker.git_refs import resolve_ref
from awx_docker.upstream.models import CiSignal, UpstreamProvider, UpstreamSignals

from .base import ProviderResult


def collect(
    repository: str,
    requested_ref: str,
    *,
    resolved_revision: str | None = None,
    **_: object,
) -> ProviderResult:
    revision = resolved_revision or resolve_ref(repository, requested_ref)
    return ProviderResult(
        repository=repository,
        requested_ref=requested_ref,
        resolved_revision=revision,
        provider=UpstreamProvider(name="generic-git", signal_source="git"),
        signals=UpstreamSignals(
            ci=CiSignal(
                provider="generic-git",
                available=False,
                total=0,
                warnings=["generic-git resolves refs but does not expose CI health signals"],
                required_success_missing=True,
            )
        ),
    )
