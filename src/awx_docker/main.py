"""Dagger API facade for AWX Docker builds and checks."""

import dagger
from dagger import function, object_type

from awx_docker.builds.awx import build_awx_image, verify_awx_image
from awx_docker.builds.awx_ee import build_ee_context, build_ee_image, verify_ee_image
from awx_docker.builds.awx_ui import UI_STATIC_BUNDLE_PATH, build_awx_ui_bundle
from awx_docker.checks.lint import check_container, format_container, lint_container, test_container
from awx_docker.checks.tool_container import python_container
from awx_docker.utilities.image_ref import split_image_ref
from awx_docker.utilities.load_configuration import (
    DEFAULT_AWX_EE_BASE_IMAGE,
    DEFAULT_AWX_EE_IMAGE_NAME,
    DEFAULT_AWX_EE_IMAGE_TAG,
    DEFAULT_AWX_EE_PLATFORM,
    DEFAULT_AWX_PYTHON_CONSTRAINTS,
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_AWX_UI_BUNDLE_NAME,
    DEFAULT_AWX_UI_BUNDLE_TAG,
    DEFAULT_AWX_UI_DELIVERY,
    DEFAULT_AWX_UI_REF,
    DEFAULT_AWX_UI_REPO,
    DEFAULT_BASE_IMAGE,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_PLATFORM,
    DEFAULT_RECEPTOR_IMAGE,
)


@object_type
class AwxDocker:
    """Dagger API exposed by this repository."""

    @function
    async def check(self, source: dagger.Directory) -> str:
        """Run lint and unit tests."""
        return await check_container(source).stdout()

    @function
    async def format(self, source: dagger.Directory) -> str:
        """Format Python files."""
        return await format_container(source).stdout()

    @function
    async def lint(self, source: dagger.Directory) -> str:
        """Run linters and shell checks."""
        return await lint_container(source).stdout()

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Run unit tests."""
        return await test_container(source).stdout()

    @function
    async def resolve_ref(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
    ) -> str:
        """Resolve an AWX branch, tag, or SHA to a concrete upstream SHA."""
        return await resolve_upstream_revision(source, upstream_repository, upstream_ref)

    @function
    async def build(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        awx_ui_repository: str = DEFAULT_AWX_UI_REPO,
        awx_ui_ref: str = DEFAULT_AWX_UI_REF,
        awx_ui_delivery: str = DEFAULT_AWX_UI_DELIVERY,
        resolved_revision: str = "",
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
        base_image: str = DEFAULT_BASE_IMAGE,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        python_constraints: str = DEFAULT_AWX_PYTHON_CONSTRAINTS,
        ssh_auth_sock: str = "",
    ) -> dagger.Container:
        """Build the AWX proof-of-concept image."""
        resolved_sha = resolved_revision or await resolve_upstream_revision(
            source, upstream_repository, upstream_ref
        )
        return build_awx_image(
            source,
            upstream_repository,
            upstream_ref,
            resolved_sha,
            awx_ui_repository,
            awx_ui_ref,
            awx_ui_delivery,
            image_name,
            image_tag,
            platform,
            base_image,
            receptor_image,
            python_constraints,
            ssh_auth_sock,
        )

    @function
    async def verify(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        awx_ui_repository: str = DEFAULT_AWX_UI_REPO,
        awx_ui_ref: str = DEFAULT_AWX_UI_REF,
        awx_ui_delivery: str = DEFAULT_AWX_UI_DELIVERY,
        resolved_revision: str = "",
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
        base_image: str = DEFAULT_BASE_IMAGE,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        python_constraints: str = DEFAULT_AWX_PYTHON_CONSTRAINTS,
        ssh_auth_sock: str = "",
    ) -> str:
        """Build the image and run the runtime contract check."""
        image = await self.build(
            source,
            upstream_repository,
            upstream_ref,
            awx_ui_repository,
            awx_ui_ref,
            awx_ui_delivery,
            resolved_revision,
            image_name,
            image_tag,
            platform,
            base_image,
            receptor_image,
            python_constraints,
            ssh_auth_sock,
        )
        return await verify_awx_image(image, f"{image_name}:{image_tag}").stdout()

    @function
    async def export(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        awx_ui_repository: str = DEFAULT_AWX_UI_REPO,
        awx_ui_ref: str = DEFAULT_AWX_UI_REF,
        awx_ui_delivery: str = DEFAULT_AWX_UI_DELIVERY,
        resolved_revision: str = "",
        image_ref: str = f"{DEFAULT_IMAGE_NAME}:{DEFAULT_IMAGE_TAG}",
        platform: str = DEFAULT_PLATFORM,
        base_image: str = DEFAULT_BASE_IMAGE,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        python_constraints: str = DEFAULT_AWX_PYTHON_CONSTRAINTS,
        ssh_auth_sock: str = "",
    ) -> dagger.File:
        """Build and verify an image, then return it as an OCI tarball."""
        image_name, image_tag = split_image_ref(image_ref)
        image = await self.build(
            source,
            upstream_repository,
            upstream_ref,
            awx_ui_repository,
            awx_ui_ref,
            awx_ui_delivery,
            resolved_revision,
            image_name,
            image_tag,
            platform,
            base_image,
            receptor_image,
            python_constraints,
            ssh_auth_sock,
        )
        return verify_awx_image(image, image_ref).as_tarball()

    @function
    async def build_ui(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        awx_ui_repository: str = DEFAULT_AWX_UI_REPO,
        awx_ui_ref: str = DEFAULT_AWX_UI_REF,
        bundle_name: str = DEFAULT_AWX_UI_BUNDLE_NAME,
        bundle_tag: str = DEFAULT_AWX_UI_BUNDLE_TAG,
        resolved_revision: str = "",
        platform: str = DEFAULT_PLATFORM,
        base_image: str = DEFAULT_BASE_IMAGE,
    ) -> dagger.Directory:
        """Build the pinned AWX UI as a sideloadable static bundle."""
        resolved_sha = resolved_revision or await resolve_upstream_revision(
            source, upstream_repository, upstream_ref
        )
        image = build_awx_ui_bundle(
            source,
            upstream_repository,
            upstream_ref,
            resolved_sha,
            awx_ui_repository,
            awx_ui_ref,
            bundle_name,
            bundle_tag,
            platform,
            base_image,
        )
        return image.directory(UI_STATIC_BUNDLE_PATH)

    @function
    async def export_ui(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        awx_ui_repository: str = DEFAULT_AWX_UI_REPO,
        awx_ui_ref: str = DEFAULT_AWX_UI_REF,
        bundle_name: str = DEFAULT_AWX_UI_BUNDLE_NAME,
        bundle_tag: str = DEFAULT_AWX_UI_BUNDLE_TAG,
        resolved_revision: str = "",
        platform: str = DEFAULT_PLATFORM,
        base_image: str = DEFAULT_BASE_IMAGE,
    ) -> dagger.Directory:
        """Build and return the AWX UI static bundle directory."""
        return await self.build_ui(
            source,
            upstream_repository,
            upstream_ref,
            awx_ui_repository,
            awx_ui_ref,
            bundle_name,
            bundle_tag,
            resolved_revision,
            platform,
            base_image,
        )

    @function
    async def build_ee(
        self,
        source: dagger.Directory,
        image_name: str = DEFAULT_AWX_EE_IMAGE_NAME,
        image_tag: str = DEFAULT_AWX_EE_IMAGE_TAG,
        platform: str = DEFAULT_AWX_EE_PLATFORM,
        ee_base_image: str = DEFAULT_AWX_EE_BASE_IMAGE,
    ) -> dagger.Container:
        """Build the custom AWX execution environment image."""
        context = await build_ee_context(python_container(source))
        return build_ee_image(context, image_name, image_tag, platform, ee_base_image)

    @function
    async def export_ee(
        self,
        source: dagger.Directory,
        image_ref: str = f"{DEFAULT_AWX_EE_IMAGE_NAME}:{DEFAULT_AWX_EE_IMAGE_TAG}",
        platform: str = DEFAULT_AWX_EE_PLATFORM,
        ee_base_image: str = DEFAULT_AWX_EE_BASE_IMAGE,
    ) -> dagger.File:
        """Build and verify the custom AWX EE image, then return it as an OCI tarball."""
        image_name, image_tag = split_image_ref(image_ref)
        image = await self.build_ee(source, image_name, image_tag, platform, ee_base_image)
        return verify_ee_image(image).as_tarball()


async def resolve_upstream_revision(
    source: dagger.Directory,
    upstream_repository: str,
    upstream_ref: str,
) -> str:
    """Resolve an AWX ref inside the Dagger Python tooling container."""
    return (
        await python_container(source)
        .with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "resolve-ref",
                "--upstream-repository",
                upstream_repository,
                "--upstream-ref",
                upstream_ref,
            ]
        )
        .stdout()
    ).strip()
