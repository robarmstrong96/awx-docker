import dagger
from dagger import dag, function, object_type

from awx_docker.config import (
    DEFAULT_AWX_PYTHON_CONSTRAINTS,
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_AWX_UI_DELIVERY,
    DEFAULT_AWX_UI_REF,
    DEFAULT_AWX_UI_REPO,
    DEFAULT_BASE_IMAGE,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_PLATFORM,
    DEFAULT_RECEPTOR_IMAGE,
    DEFAULT_TOOLING_PYTHON,
    DEFAULT_TOOLING_UV_IMAGE,
)


def _uv_python(*args: str) -> list[str]:
    return ["uv", "run", "--python", DEFAULT_TOOLING_PYTHON, "python", *args]


@object_type
class AwxDocker:
    @function
    async def check(self, source: dagger.Directory) -> str:
        """Run lint and unit tests."""
        ctr = self._lint_container(source)
        ctr = ctr.with_exec(_uv_python("-m", "pytest", "tests/unit"))
        return await ctr.stdout()

    @function
    async def format(self, source: dagger.Directory) -> str:
        """Format Python files."""
        return await self._python(source).with_exec(["uv", "run", "ruff", "format", "."]).stdout()

    @function
    async def lint(self, source: dagger.Directory) -> str:
        """Run linters and shell checks."""
        return await self._lint_container(source).stdout()

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Run unit tests."""
        return (
            await self._python(source).with_exec(_uv_python("-m", "pytest", "tests/unit")).stdout()
        )

    @function
    async def resolve_ref(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
    ) -> str:
        """Resolve an AWX branch, tag, or SHA to a concrete upstream SHA."""
        return (
            await self._python(source)
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
        resolved_sha = resolved_revision or await self._resolve_upstream_revision(
            source, upstream_repository, upstream_ref
        )
        return self._build_image_from_source(
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
        resolved_sha = resolved_revision or await self._resolve_upstream_revision(
            source, upstream_repository, upstream_ref
        )
        image = self._build_image_from_source(
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
        image_ref = f"{image_name}:{image_tag}"
        return await image.with_exec(
            ["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref]
        ).stdout()

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
        image_name, image_tag = self._split_image_ref(image_ref)
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
        verified = image.with_exec(
            ["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref]
        )
        return verified.as_tarball()

    def _build_image_from_source(
        self,
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

    def _python(self, source: dagger.Directory) -> dagger.Container:
        return (
            dag.container()
            .from_(DEFAULT_TOOLING_UV_IMAGE)
            .with_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["apt-get", "update"])
            .with_exec(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    "ca-certificates",
                    "git",
                ]
            )
            .with_exec(["uv", "sync", "--all-groups"])
        )

    def _tools(self, source: dagger.Directory) -> dagger.Container:
        return (
            self._python(source)
            .with_exec(["apt-get", "update"])
            .with_exec(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    "ca-certificates",
                    "git",
                    "shellcheck",
                ]
            )
        )

    def _lint_container(self, source: dagger.Directory) -> dagger.Container:
        ctr = self._tools(source)
        ctr = ctr.with_exec(["uv", "run", "ruff", "format", "--check", "."])
        ctr = ctr.with_exec(["uv", "run", "ruff", "check", "."])
        ctr = ctr.with_exec(["shellcheck", "scripts/runtime-entrypoint.sh"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-rpms"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-awx-ui-build-deps"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-awx-source"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-awx-ui-delivery"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-awx-ui-source"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-awx-python-deps"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/synthesize-awx-dist-info"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-runtime-layout"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/verify-runtime-contract"])
        return ctr

    async def _resolve_upstream_revision(
        self,
        source: dagger.Directory,
        upstream_repository: str,
        upstream_ref: str,
    ) -> str:
        return (
            await self._python(source)
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

    def _split_image_ref(self, image_ref: str) -> tuple[str, str]:
        if ":" not in image_ref.rsplit("/", 1)[-1]:
            return image_ref, DEFAULT_IMAGE_TAG
        image_name, image_tag = image_ref.rsplit(":", 1)
        return image_name, image_tag
