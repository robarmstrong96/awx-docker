"""Build helpers for the AWX UI static bundle."""

import dagger

UI_STATIC_BUNDLE_PATH = "/awx-ui-static"


def build_awx_ui_bundle(
    source: dagger.Directory,
    awx_repo: str,
    awx_ref: str,
    resolved_sha: str,
    awx_ui_repo: str,
    awx_ui_ref: str,
    bundle_name: str,
    bundle_tag: str,
    platform: str,
    base_image: str,
) -> dagger.Container:
    """Build a container that exposes the AWX UI static bundle directory."""
    return (
        source.docker_build(
            dockerfile="docker/awx-ui/Dockerfile",
            platform=dagger.Platform(platform),
            build_args=[
                dagger.BuildArg("CENTOS_STREAM_IMAGE", base_image),
                dagger.BuildArg("AWX_REPO", awx_repo),
                dagger.BuildArg("AWX_REF", resolved_sha),
                dagger.BuildArg("AWX_REQUESTED_REF", awx_ref),
                dagger.BuildArg("AWX_UI_REPO", awx_ui_repo),
                dagger.BuildArg("AWX_UI_REF", awx_ui_ref),
            ],
        )
        .with_label("org.opencontainers.image.title", "AWX UI static bundle")
        .with_label("dev.awx-wrapper.awx.repo", awx_repo)
        .with_label("dev.awx-wrapper.awx.ref", awx_ref)
        .with_label("dev.awx-wrapper.awx.revision", resolved_sha)
        .with_label("dev.awx-wrapper.awx-ui.repo", awx_ui_repo)
        .with_label("dev.awx-wrapper.awx-ui.ref", awx_ui_ref)
        .with_label("dev.awx-wrapper.awx-ui.bundle.name", f"{bundle_name}:{bundle_tag}")
        .with_label("dev.awx-wrapper.base.image", base_image)
        .with_label("dev.awx-wrapper.platform", platform)
    )
