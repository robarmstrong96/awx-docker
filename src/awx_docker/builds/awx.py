"""Build helpers for the AWX control-plane image."""

from __future__ import annotations

from dataclasses import dataclass

import dagger
from dagger import dag


@dataclass(frozen=True)
class AwxImageBuildRequest:
    """Inputs for building the AWX control-plane image.

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
    awx_ui_delivery : str
        UI delivery mode, either ``embedded`` or ``sideloaded``.
    image_name : str
        Name to record on the built image.
    image_tag : str
        Tag to record on the built image.
    platform : str
        Target container platform.
    base_image : str
        CentOS Stream base image used by the AWX Dockerfile.
    receptor_image : str
        Receptor image copied into the AWX image.
    python_constraints : str
        Constraint file name under ``config/awx/constraints``.
    ssh_auth_sock : str
        Optional SSH agent socket used for private Git access.
    """

    source: dagger.Directory
    awx_repo: str
    awx_ref: str
    resolved_sha: str
    awx_ui_repo: str
    awx_ui_ref: str
    awx_ui_delivery: str
    image_name: str
    image_tag: str
    platform: str
    base_image: str
    receptor_image: str
    python_constraints: str
    ssh_auth_sock: str


def build_awx_image(request: AwxImageBuildRequest) -> dagger.Container:
    """Build the AWX control-plane image from a resolved upstream commit.

    Parameters
    ----------
    request : AwxImageBuildRequest
        AWX image build inputs.

    Returns
    -------
    dagger.Container
        Built AWX control-plane container.
    """
    ssh = dag.host().unix_socket(request.ssh_auth_sock) if request.ssh_auth_sock else None
    return (
        request.source.docker_build(
            dockerfile="docker/awx/Dockerfile",
            platform=dagger.Platform(request.platform),
            build_args=[
                dagger.BuildArg("CENTOS_STREAM_IMAGE", request.base_image),
                dagger.BuildArg("AWX_REPO", request.awx_repo),
                dagger.BuildArg("AWX_REF", request.resolved_sha),
                dagger.BuildArg("AWX_REQUESTED_REF", request.awx_ref),
                dagger.BuildArg("AWX_SOURCE_REVISION", request.resolved_sha),
                dagger.BuildArg("AWX_UI_REPO", request.awx_ui_repo),
                dagger.BuildArg("AWX_UI_REF", request.awx_ui_ref),
                dagger.BuildArg("AWX_UI_DELIVERY", request.awx_ui_delivery),
                dagger.BuildArg("RECEPTOR_IMAGE", request.receptor_image),
                dagger.BuildArg("AWX_PYTHON_CONSTRAINTS", request.python_constraints),
            ],
            ssh=ssh,
        )
        .with_label("org.opencontainers.image.title", "Unofficial AWX proof-of-concept image")
        .with_label("dev.awx-wrapper.awx.repo", request.awx_repo)
        .with_label("dev.awx-wrapper.awx.ref", request.awx_ref)
        .with_label("dev.awx-wrapper.awx.revision", request.resolved_sha)
        .with_label("dev.awx-wrapper.awx-ui.repo", request.awx_ui_repo)
        .with_label("dev.awx-wrapper.awx-ui.ref", request.awx_ui_ref)
        .with_label("dev.awx-wrapper.awx-ui.delivery", request.awx_ui_delivery)
        .with_label("dev.awx-wrapper.base.image", request.base_image)
        .with_label(
            "dev.awx-wrapper.image.name",
            f"{request.image_name}:{request.image_tag}",
        )
        .with_label("dev.awx-wrapper.platform", request.platform)
        .with_label("dev.awx-wrapper.python.constraints", request.python_constraints)
    )


def verify_awx_image(image: dagger.Container, image_ref: str) -> dagger.Container:
    """Attach the AWX runtime contract check to a built image.

    Parameters
    ----------
    image : dagger.Container
        AWX container to verify.
    image_ref : str
        Image reference passed to the runtime contract script.

    Returns
    -------
    dagger.Container
        Container with the verification command appended.
    """
    return image.with_exec(["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref])
