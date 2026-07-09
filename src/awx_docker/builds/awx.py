"""Build helpers for the AWX control-plane image."""

from __future__ import annotations

import dagger
from dagger import dag


def build_awx_image(
    source: dagger.Directory,
    awx_repo: str,
    awx_ref: str,
    resolved_sha: str,
    awx_ui_repo: str,
    awx_ui_ref: str,
    awx_ui_delivery: str,
    image_name: str,
    image_tag: str,
    platform: str,
    base_image: str,
    receptor_image: str,
    python_constraints: str,
    ssh_auth_sock: str,
) -> dagger.Container:
    """Build the AWX control-plane image from a resolved upstream commit."""
    ssh = dag.host().unix_socket(ssh_auth_sock) if ssh_auth_sock else None
    return (
        source.docker_build(
            dockerfile="docker/awx/Dockerfile",
            platform=dagger.Platform(platform),
            build_args=[
                dagger.BuildArg("CENTOS_STREAM_IMAGE", base_image),
                dagger.BuildArg("AWX_REPO", awx_repo),
                dagger.BuildArg("AWX_REF", resolved_sha),
                dagger.BuildArg("AWX_REQUESTED_REF", awx_ref),
                dagger.BuildArg("AWX_SOURCE_REVISION", resolved_sha),
                dagger.BuildArg("AWX_UI_REPO", awx_ui_repo),
                dagger.BuildArg("AWX_UI_REF", awx_ui_ref),
                dagger.BuildArg("AWX_UI_DELIVERY", awx_ui_delivery),
                dagger.BuildArg("RECEPTOR_IMAGE", receptor_image),
                dagger.BuildArg("AWX_PYTHON_CONSTRAINTS", python_constraints),
            ],
            ssh=ssh,
        )
        .with_label("org.opencontainers.image.title", "Unofficial AWX proof-of-concept image")
        .with_label("dev.awx-wrapper.awx.repo", awx_repo)
        .with_label("dev.awx-wrapper.awx.ref", awx_ref)
        .with_label("dev.awx-wrapper.awx.revision", resolved_sha)
        .with_label("dev.awx-wrapper.awx-ui.repo", awx_ui_repo)
        .with_label("dev.awx-wrapper.awx-ui.ref", awx_ui_ref)
        .with_label("dev.awx-wrapper.awx-ui.delivery", awx_ui_delivery)
        .with_label("dev.awx-wrapper.base.image", base_image)
        .with_label("dev.awx-wrapper.image.name", f"{image_name}:{image_tag}")
        .with_label("dev.awx-wrapper.platform", platform)
        .with_label("dev.awx-wrapper.python.constraints", python_constraints)
    )


def verify_awx_image(image: dagger.Container, image_ref: str) -> dagger.Container:
    """Attach the AWX runtime contract check to a built image."""
    return image.with_exec(["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref])
