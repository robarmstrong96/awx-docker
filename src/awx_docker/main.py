import dagger
from dagger import dag, function, object_type

from awx_docker.config import (
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_PLATFORM,
    DEFAULT_RECEPTOR_IMAGE,
)


@object_type
class AwxDocker:
    @function
    async def check(self, source: dagger.Directory) -> str:
        """Run fast local quality checks."""
        return await self._check_container(source).stdout()

    @function
    async def strict_check(self, source: dagger.Directory) -> str:
        """Run fast checks plus stricter advisory validation."""
        ctr = self._check_container(source)
        ctr = self._with_strict_tools(ctr)
        ctr = ctr.with_exec(["uv", "run", "pyright", "src", "tests"])
        ctr = ctr.with_exec(["hadolint", "-c", ".hadolint.yaml", "docker/awx/Dockerfile"])
        ctr = ctr.with_exec(["uv", "run", "yamllint", "."])
        ctr = ctr.with_exec(["shfmt", "-d", "scripts", "docker/awx/bin"])
        return await ctr.stdout()

    @function
    async def code_quality(self, source: dagger.Directory) -> str:
        """Run fast formatting, lint, shell, and workflow checks."""
        return await self._code_quality_container(source).stdout()

    @function
    async def policy_tests(self, source: dagger.Directory) -> str:
        """Run unit tests for policy and report behavior."""
        return await self._policy_test_container(source).stdout()

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
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        provider: str = "auto",
        signal_file: str = "",
        resolved_revision: str = "",
        mode: str = "scheduled-build",
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Evaluate upstream repository health and return evidence files."""
        ctr = self._python(source)
        if github_token is not None:
            ctr = ctr.with_secret_variable("GITHUB_TOKEN", github_token)
        args = [
            "uv",
            "run",
            "awx-docker",
            "upstream-health",
            "--upstream-repository",
            upstream_repository,
            "--upstream-ref",
            upstream_ref,
            "--provider",
            provider,
            "--mode",
            mode,
        ]
        if signal_file:
            args.extend(["--signal-file", signal_file])
        if resolved_revision:
            args.extend(["--resolved-revision", resolved_revision])
        ctr = ctr.with_exec(args)
        return ctr.directory("build/evidence")

    @function
    async def resolve_ref(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
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
                    "--awx-repo",
                    awx_repo,
                    "--awx-ref",
                    awx_ref,
                ]
            )
            .stdout()
        ).strip()

    @function
    async def public_hygiene(self, source: dagger.Directory) -> dagger.Directory:
        """Scan public-facing files and return public readiness evidence."""
        return self._with_public_hygiene_evidence(source).directory("build/evidence")

    @function
    async def public_readiness(self, source: dagger.Directory) -> dagger.Directory:
        """Scan public-facing files and return public readiness evidence."""
        return await self.public_hygiene(source)

    @function
    async def image_build(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
        resolved_revision: str = "",
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        ssh_auth_sock: str = "",
    ) -> dagger.Container:
        """Build the AWX proof-of-concept image as a lower-level operation."""
        source, resolved_sha = await self._prepare_image_source(
            source, image_name, image_tag, awx_repo, awx_ref, platform, resolved_revision
        )
        return self._build_image_from_source(
            source,
            awx_repo,
            awx_ref,
            resolved_sha,
            image_name,
            image_tag,
            platform,
            receptor_image,
            ssh_auth_sock,
        )

    def _build_image_from_source(
        self,
        source: dagger.Directory,
        awx_repo: str,
        awx_ref: str,
        resolved_sha: str,
        image_name: str,
        image_tag: str,
        platform: str,
        receptor_image: str,
        ssh_auth_sock: str,
    ) -> dagger.Container:
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
        resolved_revision: str = "",
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        ssh_auth_sock: str = "",
    ) -> dagger.Directory:
        """Build and verify the image as a lower-level operation."""
        source, resolved_sha = await self._prepare_image_source(
            source, image_name, image_tag, awx_repo, awx_ref, platform, resolved_revision
        )
        image = self._build_image_from_source(
            source,
            awx_repo,
            awx_ref,
            resolved_sha,
            image_name,
            image_tag,
            platform,
            receptor_image,
            ssh_auth_sock,
        )
        image_ref = f"{image_name}:{image_tag}"
        verified = image.with_exec(
            ["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref]
        )
        return source.with_directory(
            "build/evidence",
            verified.directory("/tmp/awx-docker-evidence"),
        ).directory("build/evidence")

    @function
    async def image_pipeline(
        self,
        source: dagger.Directory,
        upstream_repository: str = DEFAULT_AWX_REPO,
        upstream_ref: str = DEFAULT_AWX_REF,
        provider: str = "auto",
        signal_file: str = "",
        resolved_revision: str = "",
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
        receptor_image: str = DEFAULT_RECEPTOR_IMAGE,
        ssh_auth_sock: str = "",
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Resolve once, check upstream, build, verify, and return evidence."""
        resolved_sha = resolved_revision or await self._resolve_upstream_revision(
            source, upstream_repository, upstream_ref
        )
        source = await self._write_upstream_ref(
            source,
            upstream_repository,
            upstream_ref,
            resolved_sha,
        )
        source = self._with_upstream_health_evidence(
            source,
            upstream_repository,
            upstream_ref,
            provider,
            signal_file,
            resolved_sha,
            "scheduled-build",
            github_token,
        )
        source = await self._write_metadata(
            source,
            image_name,
            image_tag,
            upstream_repository,
            upstream_ref,
            resolved_sha,
            platform,
        )
        image = self._build_image_from_source(
            source,
            upstream_repository,
            upstream_ref,
            resolved_sha,
            image_name,
            image_tag,
            platform,
            receptor_image,
            ssh_auth_sock,
        )
        image_ref = f"{image_name}:{image_tag}"
        verified = image.with_exec(
            ["/usr/local/libexec/awx-docker/verify-runtime-contract", image_ref]
        )
        source = source.with_directory(
            "build/evidence",
            verified.directory("/tmp/awx-docker-evidence"),
        )
        source = await self._write_image_pipeline(
            source,
            upstream_repository,
            upstream_ref,
            resolved_sha,
            image_name,
            image_tag,
            platform,
        )
        return source.directory("build/evidence")

    @function
    async def release_check(
        self,
        source: dagger.Directory,
        upstream_ref: str = DEFAULT_AWX_REF,
        upstream_repository: str = DEFAULT_AWX_REPO,
        provider: str = "auto",
        signal_file: str = "",
        resolved_revision: str = "",
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Run checks required before making the repository or image public."""
        ctr = self._python(source)
        if github_token is not None:
            ctr = ctr.with_secret_variable("GITHUB_TOKEN", github_token)
        args = [
            "uv",
            "run",
            "awx-docker",
            "release-check",
            "--upstream-repository",
            upstream_repository,
            "--upstream-ref",
            upstream_ref,
            "--provider",
            provider,
        ]
        if signal_file:
            args.extend(["--signal-file", signal_file])
        if resolved_revision:
            args.extend(["--resolved-revision", resolved_revision])
        ctr = ctr.with_exec(args)
        return ctr.directory("build/evidence")

    @function
    async def publication_gate(
        self,
        source: dagger.Directory,
        upstream_ref: str = DEFAULT_AWX_REF,
        upstream_repository: str = DEFAULT_AWX_REPO,
        provider: str = "auto",
        signal_file: str = "",
        resolved_revision: str = "",
        github_token: dagger.Secret | None = None,
    ) -> dagger.Directory:
        """Run checks required before public repository or image publication."""
        return await self.release_check(
            source,
            upstream_ref,
            upstream_repository,
            provider,
            signal_file,
            resolved_revision,
            github_token,
        )

    @function
    async def evidence(
        self,
        source: dagger.Directory,
        awx_repo: str = DEFAULT_AWX_REPO,
        awx_ref: str = DEFAULT_AWX_REF,
        image_name: str = DEFAULT_IMAGE_NAME,
        image_tag: str = DEFAULT_IMAGE_TAG,
        platform: str = DEFAULT_PLATFORM,
    ) -> dagger.Directory:
        """Generate lightweight evidence files and return the evidence directory."""
        source, _ = await self._prepare_image_source(
            source, image_name, image_tag, awx_repo, awx_ref, platform
        )
        return self._with_public_hygiene_evidence(source).directory("build/evidence")

    def _with_public_hygiene_evidence(self, source: dagger.Directory) -> dagger.Container:
        return self._python(source).with_exec(["uv", "run", "awx-docker", "public-hygiene"])

    def _check_container(self, source: dagger.Directory) -> dagger.Container:
        return self._policy_test_container(source).with_exec(
            ["uv", "run", "awx-docker", "public-hygiene"]
        )

    def _code_quality_container(self, source: dagger.Directory) -> dagger.Container:
        ctr = self._tools(source)
        ctr = ctr.with_exec(["uv", "run", "ruff", "format", "--check", "."])
        ctr = ctr.with_exec(["uv", "run", "ruff", "check", "."])
        ctr = ctr.with_exec(["shellcheck", "scripts/runtime-entrypoint.sh"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-rpms"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-awx-source"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/install-awx-python-deps"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/synthesize-awx-dist-info"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/prepare-runtime-layout"])
        ctr = ctr.with_exec(["shellcheck", "docker/awx/bin/verify-runtime-contract"])
        return ctr.with_exec(["actionlint"])

    def _policy_test_container(self, source: dagger.Directory) -> dagger.Container:
        return self._code_quality_container(source).with_exec(["uv", "run", "pytest", "tests/unit"])

    def _with_strict_tools(self, ctr: dagger.Container) -> dagger.Container:
        hadolint_url = (
            "https://github.com/hadolint/hadolint/releases/download/v2.14.0/hadolint-Linux-x86_64"
        )
        return (
            ctr.with_exec(["apt-get", "update"])
            .with_exec(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    "libatomic1",
                    "shfmt",
                ]
            )
            .with_exec(["curl", "-fsSL", "-o", "/usr/local/bin/hadolint", hadolint_url])
            .with_exec(["chmod", "+x", "/usr/local/bin/hadolint"])
        )

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
                    "make",
                ]
            )
            .with_exec(["uv", "sync", "--all-groups"])
        )

    def _tools(self, source: dagger.Directory) -> dagger.Container:
        actionlint_url = (
            "https://github.com/rhysd/actionlint/releases/download/v1.7.7/"
            "actionlint_1.7.7_linux_amd64.tar.gz"
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
            .with_exec(["chmod", "+x", "/usr/local/bin/actionlint"])
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

    async def _write_upstream_ref(
        self,
        source: dagger.Directory,
        upstream_repository: str,
        upstream_ref: str,
        resolved_revision: str,
    ) -> dagger.Directory:
        ctr = self._python(source).with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "write-upstream-ref",
                "--upstream-repository",
                upstream_repository,
                "--upstream-ref",
                upstream_ref,
                "--resolved-revision",
                resolved_revision,
            ]
        )
        return source.with_directory("build/evidence", ctr.directory("build/evidence"))

    def _with_upstream_health_evidence(
        self,
        source: dagger.Directory,
        upstream_repository: str,
        upstream_ref: str,
        provider: str,
        signal_file: str,
        resolved_revision: str,
        mode: str,
        github_token: dagger.Secret | None,
    ) -> dagger.Directory:
        args = [
            "uv",
            "run",
            "awx-docker",
            "upstream-health",
            "--upstream-repository",
            upstream_repository,
            "--upstream-ref",
            upstream_ref,
            "--provider",
            provider,
            "--resolved-revision",
            resolved_revision,
            "--mode",
            mode,
        ]
        if signal_file:
            args.extend(["--signal-file", signal_file])
        ctr = self._python(source)
        if github_token is not None:
            ctr = ctr.with_secret_variable("GITHUB_TOKEN", github_token)
        ctr = ctr.with_exec(args)
        return source.with_directory("build/evidence", ctr.directory("build/evidence"))

    async def _write_image_pipeline(
        self,
        source: dagger.Directory,
        upstream_repository: str,
        upstream_ref: str,
        resolved_revision: str,
        image_name: str,
        image_tag: str,
        platform: str,
    ) -> dagger.Directory:
        ctr = self._python(source).with_exec(
            [
                "uv",
                "run",
                "awx-docker",
                "write-image-pipeline",
                "--upstream-repository",
                upstream_repository,
                "--upstream-ref",
                upstream_ref,
                "--resolved-revision",
                resolved_revision,
                "--image-name",
                image_name,
                "--image-tag",
                image_tag,
                "--platform",
                platform,
            ]
        )
        return source.with_directory("build/evidence", ctr.directory("build/evidence"))

    async def _prepare_image_source(
        self,
        source: dagger.Directory,
        image_name: str,
        image_tag: str,
        awx_repo: str,
        requested_ref: str,
        platform: str,
        resolved_ref: str = "",
    ) -> tuple[dagger.Directory, str]:
        resolved_ref = resolved_ref or await self._resolve_upstream_revision(
            source, awx_repo, requested_ref
        )
        source = await self._write_metadata(
            source,
            image_name,
            image_tag,
            awx_repo,
            requested_ref,
            resolved_ref,
            platform,
        )
        return source, resolved_ref

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
                    "--awx-repo",
                    upstream_repository,
                    "--awx-ref",
                    upstream_ref,
                ]
            )
            .stdout()
        ).strip()
