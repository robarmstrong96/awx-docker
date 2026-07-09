"""Build helpers for the AWX UI static bundle."""

from dataclasses import dataclass

import dagger

UI_STATIC_BUNDLE_PATH = "/awx-ui-static"


@dataclass(frozen=True)
class AwxUiBundleBuildRequest:
    """Inputs for building the AWX UI static bundle.

    Attributes
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.
    awx_repo : str
        AWX Git repository used for the control-plane source.
    awx_ref : str
        Requested AWX branch, tag, or commit SHA.
    resolved_sha : str
        Concrete AWX commit SHA passed into the Docker build.
    awx_ui_repo : str
        AWX UI Git repository used for static assets.
    awx_ui_ref : str
        Requested AWX UI branch, tag, or commit SHA.
    bundle_name : str
        Name to record on the UI bundle image.
    bundle_tag : str
        Tag to record on the UI bundle image.
    platform : str
        Target container platform.
    base_image : str
        CentOS Stream base image used by the UI Dockerfile.
    """

    source: dagger.Directory
    awx_repo: str
    awx_ref: str
    resolved_sha: str
    awx_ui_repo: str
    awx_ui_ref: str
    bundle_name: str
    bundle_tag: str
    platform: str
    base_image: str


def build_awx_ui_bundle(request: AwxUiBundleBuildRequest) -> dagger.Container:
    """Build a container that exposes the AWX UI static bundle directory.

    Parameters
    ----------
    request : AwxUiBundleBuildRequest
        UI bundle build inputs.

    Returns
    -------
    dagger.Container
        Built container containing the AWX UI static bundle.
    """
    return (
        request.source.docker_build(
            dockerfile="docker/awx-ui/Dockerfile",
            platform=dagger.Platform(request.platform),
            build_args=[
                dagger.BuildArg("CENTOS_STREAM_IMAGE", request.base_image),
                dagger.BuildArg("AWX_REPO", request.awx_repo),
                dagger.BuildArg("AWX_REF", request.resolved_sha),
                dagger.BuildArg("AWX_REQUESTED_REF", request.awx_ref),
                dagger.BuildArg("AWX_UI_REPO", request.awx_ui_repo),
                dagger.BuildArg("AWX_UI_REF", request.awx_ui_ref),
            ],
        )
        .with_label("org.opencontainers.image.title", "AWX UI static bundle")
        .with_label("dev.awx-wrapper.awx.repo", request.awx_repo)
        .with_label("dev.awx-wrapper.awx.ref", request.awx_ref)
        .with_label("dev.awx-wrapper.awx.revision", request.resolved_sha)
        .with_label("dev.awx-wrapper.awx-ui.repo", request.awx_ui_repo)
        .with_label("dev.awx-wrapper.awx-ui.ref", request.awx_ui_ref)
        .with_label(
            "dev.awx-wrapper.awx-ui.bundle.name",
            f"{request.bundle_name}:{request.bundle_tag}",
        )
        .with_label("dev.awx-wrapper.base.image", request.base_image)
        .with_label("dev.awx-wrapper.platform", request.platform)
    )
