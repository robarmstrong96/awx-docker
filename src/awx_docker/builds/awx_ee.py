"""Build helpers for the AWX execution environment image."""

from dataclasses import dataclass

import dagger


@dataclass(frozen=True)
class AwxEeImageBuildRequest:
    """Inputs for building the AWX execution environment image.

    Attributes
    ----------
    context
        Ansible Builder context directory.
    image_name
        Name to record on the EE image.
    image_tag
        Tag to record on the EE image.
    platform
        Target container platform.
    ee_base_image
        Base execution environment image used by Ansible Builder.
    """

    context: dagger.Directory
    image_name: str
    image_tag: str
    platform: str
    ee_base_image: str


async def build_ee_context(tooling: dagger.Container) -> dagger.Directory:
    """Generate an Ansible Builder context for the starter EE image.

    Parameters
    ----------
    tooling
        Python tooling container with Ansible Builder installed.

    Returns
    -------
    dagger.Directory
        Generated Ansible Builder context directory.
    """
    return tooling.with_exec(
        [
            "uv",
            "run",
            "ansible-builder",
            "create",
            "-f",
            "docker/awx-ee/execution-environment.yml",
            "--context",
            "build/awx-ee-context",
        ]
    ).directory("build/awx-ee-context")


def build_ee_image(request: AwxEeImageBuildRequest) -> dagger.Container:
    """Build the custom AWX execution environment image.

    Parameters
    ----------
    request
        EE image build inputs.

    Returns
    -------
    dagger.Container
        Built AWX execution environment container.
    """
    return (
        request.context.docker_build(
            dockerfile="Containerfile",
            platform=dagger.Platform(request.platform),
            build_args=[dagger.BuildArg("EE_BASE_IMAGE", request.ee_base_image)],
        )
        .with_label("org.opencontainers.image.title", "Custom AWX execution environment")
        .with_label("dev.awx-wrapper.ee.base-image", request.ee_base_image)
        .with_label(
            "dev.awx-wrapper.ee.image.name",
            f"{request.image_name}:{request.image_tag}",
        )
        .with_label("dev.awx-wrapper.ee.platform", request.platform)
    )


def verify_ee_image(image: dagger.Container) -> dagger.Container:
    """Attach basic smoke checks to a built EE image.

    Parameters
    ----------
    image
        AWX execution environment container to verify.

    Returns
    -------
    dagger.Container
        Container with smoke-check commands appended.
    """
    return (
        image.with_exec(["python", "--version"])
        .with_exec(["ansible", "--version"])
        .with_exec(["ansible-runner", "--version"])
        .with_exec(["ansible-galaxy", "collection", "list"])
    )
