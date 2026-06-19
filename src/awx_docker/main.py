import dagger
from dagger import dag, function, object_type

from awx_docker.config import (
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_RECEPTOR_IMAGE,
)


@object_type
class AwxDocker:
    @function
    async def check(self, source: dagger.Directory) -> str:
        """Run fast local quality checks."""
        ctr = self._tools(source)
        ctr = ctr.with_exec(["uv", "run", "ruff", "format", "--check", "."])
        ctr = ctr.with_exec(["uv", "run", "ruff", "check", "."])
        ctr = ctr.with_exec(["uv", "run", "pyright", "src", "tests"])
        ctr = ctr.with_exec(["uv", "run", "pytest"])
        ctr = ctr.with_exec(["shellcheck", "scripts/check-public-hygiene.sh"])
        ctr = ctr.with_exec(["shellcheck", "scripts/check-upstream-status.sh"])
        ctr = ctr.with_exec(["shellcheck", "scripts/image.sh"])
        ctr = ctr.with_exec(["shellcheck", "scripts/runtime-entrypoint.sh"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-rpms"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-awx-source"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-awx-python-deps"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/synthesize-awx-dist-info"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-runtime-layout"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/verify-runtime-contract"])
        ctr = ctr.with_exec(["shfmt", "-d", "scripts", "docker/awx/bin"])
        ctr = ctr.with_exec(["uv", "run", "yamllint", "."])
        ctr = ctr.with_exec(["actionlint"])
        ctr = ctr.with_exec(["hadolint", "-c", ".hadolint.yaml", "docker/awx/Dockerfile"])
        ctr = ctr.with_exec(["uv", "run", "awx-docker", "public-hygiene"])
        return await ctr.stdout()

    @function
    async def format(self, source: dagger.Directory) -> str:
        """Format Python files where safe."""
        return await self._python(source).with_exec(["uv", "run", "ruff", "format", "."]).stdout()

    @function
    async def lint(self, source: dagger.Directory) -> str:
        """Run static linters."""
        ctr = self._python(source)
        ctr = ctr.with_exec(["uv", "run", "ruff", "format", "--check", "."])
        ctr = ctr.with_exec(["uv", "run", "ruff", "check", "."])
        return await ctr.stdout()

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Run unit tests."""
        return await self._python(source).with_exec(["uv", "run", "pytest"]).stdout()

    @function
    async def upstream_health(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
        mode: str = "scheduled-build",
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Evaluate upstream AWX health and return evidence files."""
        ctr = self._python(source)
        if github_token is not None:
            ctr = ctr.with_secret_variable("GITHUB_TOKEN", github_token)
        ctr = ctr.with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "upstream-health",
                "--awx-repo",
                awx_repo,
                "--awx-ref",
                awx_ref,
                "--mode",
                mode,
            ]
        )
        return ctr.directory("build/evidence")

    @function
    async def image_build(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = "linux/amd64",
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        ssh_auth_sock: str = "",
    ) -> dagger.Container:
        """Build the AWX proof-of-concept image."""
        resolved_sha = (
            await self._python(source)
            .with_exec(
                [
                    "uv",
                    "run",
                    "awx-docker",
                    "resolve-ref",
                    "--awx-repo",
                    awx_repo,
                    "--awx-ref",
                    awx_ref,
                ]
            )
            .stdout()
        ).strip()
        source = await self._write_metadata(
            source,
            image_name,
            image_tag,
            awx_repo,
            awx_ref,
            resolved_sha,
            platform,
        )
        ssh = dag.host().unix_socket(ssh_auth_sock) if ssh_auth_sock else None
        return (
            source.docker_build(
                dockerfile="docker/awx/Dockerfile",
                platform=dagger.Platform(platform),
                build_args=[
                    dagger.BuildArg("AWX_REPO", awx_repo),
                    dagger.BuildArg("AWX_REF", resolved_sha),
                    dagger.BuildArg("AWX_REQUESTED_REF", awx_ref),
                    dagger.BuildArg("AWX_SOURCE_REVISION", resolved_sha),
                    dagger.BuildArg("RECEPTOR_IMAGE", receptor_image),
                ],
                ssh=ssh,
            )
            .with_label("org.opencontainers.image.title", "Unofficial AWX proof-of-concept image")
            .with_label("dev.awx-wrapper.awx.repo", awx_repo)
            .with_label("dev.awx-wrapper.awx.ref", awx_ref)
            .with_label("dev.awx-wrapper.awx.revision", resolved_sha)
            .with_label("dev.awx-wrapper.image.name", f"{image_name}:{image_tag}")
            .with_label("dev.awx-wrapper.platform", platform)
        )

    @function
    async def image_verify(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
    ) -> dagger.Directory:
        """Verify image contents and return evidence files."""
        image = await self.image_build(source, awx_repo, awx_ref, image_name, image_tag)
        image_ref = f"{image_name}:{image_tag}"
        verified = image.with_exec(
            ["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref]
        )
        return verified.directory("/tmp/awx-docker-evidence")

    @function
    async def release_check(
        self,
        source: dagger.Directory,
        awx_ref: str = DEFAULT_AWX_REF,
        awx_repo: str = DEFAULT_AWX_REPO,
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Run checks required before making the repository or image public."""
        ctr = self._python(source)
        if github_token is not None:
            ctr = ctr.with_secret_variable("GITHUB_TOKEN", github_token)
        ctr = ctr.with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "release-check",
                "--awx-repo",
                awx_repo,
                "--awx-ref",
                awx_ref,
            ]
        )
        return ctr.directory("build/evidence")

    @function
    async def evidence(self, source: dagger.Directory) -> dagger.Directory:
        """Return generated evidence files."""
        return source.directory("build/evidence")

    def _python(self, source: dagger.Directory) -> dagger.Container:
        return (
            dag.container()
            .from_("ghcr.io/astral-sh/uv:python3.12-bookworm-slim")
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
        actionlint_url = (
            "https://github.com/rhysd/actionlint/releases/download/v1.7.7/"
            "actionlint_1.7.7_linux_amd64.tar.gz"
        )
        hadolint_url = (
            "https://github.com/hadolint/hadolint/releases/download/v2.14.0/hadolint-Linux-x86_64"
        )
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
                    "curl",
                    "git",
                    "shellcheck",
                    "shfmt",
                    "tar",
                ]
            )
            .with_exec(
                [
                    "bash",
                    "-lc",
                    f"curl -fsSL {actionlint_url} | tar -xz -C /usr/local/bin actionlint",
                ]
            )
            .with_exec(["curl", "-fsSL", "-o", "/usr/local/bin/hadolint", hadolint_url])
            .with_exec(["chmod", "+x", "/usr/local/bin/actionlint", "/usr/local/bin/hadolint"])
        )

    async def _write_metadata(
        self,
        source: dagger.Directory,
        image_name: str,
        image_tag: str,
        awx_repo: str,
        requested_ref: str,
        resolved_ref: str,
        platform: str,
    ) -> dagger.Directory:
        ctr = self._python(source).with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "write-metadata",
                "--image-name",
                image_name,
                "--image-tag",
                image_tag,
                "--awx-repo",
                awx_repo,
                "--awx-ref",
                requested_ref,
                "--awx-resolved-ref",
                resolved_ref,
                "--platform",
                platform,
            ]
        )
        return source.with_directory("build/evidence", ctr.directory("build/evidence"))
