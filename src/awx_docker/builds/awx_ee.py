"""Build helpers for the AWX execution environment image."""

import dagger


async def build_ee_context(tooling: dagger.Container) -> dagger.Directory:
    """Generate an Ansible Builder context for the starter EE image."""
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


def build_ee_image(
    context: dagger.Directory,
    image_name: str,
    image_tag: str,
    platform: str,
    ee_base_image: str,
) -> dagger.Container:
    """Build the custom AWX execution environment image."""
    return (
        context.docker_build(
            dockerfile="Containerfile",
            platform=dagger.Platform(platform),
            build_args=[dagger.BuildArg("EE_BASE_IMAGE", ee_base_image)],
        )
        .with_label("org.opencontainers.image.title", "Custom AWX execution environment")
        .with_label("dev.awx-wrapper.ee.base-image", ee_base_image)
        .with_label("dev.awx-wrapper.ee.image.name", f"{image_name}:{image_tag}")
        .with_label("dev.awx-wrapper.ee.platform", platform)
    )


def verify_ee_image(image: dagger.Container) -> dagger.Container:
    """Attach basic smoke checks to a built EE image."""
    return (
        image.with_exec(["python", "--version"])
        .with_exec(["ansible", "--version"])
        .with_exec(["ansible-runner", "--version"])
        .with_exec(["ansible-galaxy", "collection", "list"])
    )
