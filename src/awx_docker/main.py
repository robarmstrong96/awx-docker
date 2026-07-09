"""Dagger API facade for AWX Docker builds and checks."""

import dagger
from dagger import function, object_type

from awx_docker.builds.awx import AwxImageBuildRequest, build_awx_image, verify_awx_image
from awx_docker.builds.awx_ee import (
    AwxEeImageBuildRequest,
    build_ee_context,
    build_ee_image,
    verify_ee_image,
)
from awx_docker.builds.awx_ui import (
    UI_STATIC_BUNDLE_PATH,
    AwxUiBundleBuildRequest,
    build_awx_ui_bundle,
)
from awx_docker.checks.lint import check_container, format_container, lint_container, test_container
from awx_docker.checks.tool_container import python_container
from awx_docker.config import Components
from awx_docker.utilities.image_ref import split_image_ref
from awx_docker.utilities.load_configuration import DEFAULT_COMPONENTS


@object_type
class AwxDocker:
    """Dagger API exposed by this repository.

    The methods on this class are the commands Dagger exposes for building,
    testing, verifying, and exporting the AWX Docker artifacts.
    """

    @function
    async def check(self, source: dagger.Directory) -> str:
        """Run lint and unit tests.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.

        Returns
        -------
        str
            Output from the final check command.
        """
        return await check_container(source).stdout()

    @function
    async def format(self, source: dagger.Directory) -> str:
        """Format Python files.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.

        Returns
        -------
        str
            Ruff formatter output.
        """
        return await format_container(source).stdout()

    @function
    async def lint(self, source: dagger.Directory) -> str:
        """Run linters and shell checks.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.

        Returns
        -------
        str
            Output from the final lint command.
        """
        return await lint_container(source).stdout()

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Run unit tests.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.

        Returns
        -------
        str
            Pytest output.
        """
        return await test_container(source).stdout()

    @function
    async def resolve_ref(
        self,
        source: dagger.Directory,
        upstream_repository: str = "",
        upstream_ref: str = "",
    ) -> str:
        """Resolve an AWX branch, tag, or SHA to a concrete upstream SHA.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        upstream_repository : str
            AWX Git repository to query.
        upstream_ref : str
            Branch, tag, or commit SHA to resolve.

        Returns
        -------
        str
            Concrete AWX commit SHA.
        """
        components = DEFAULT_COMPONENTS
        repository = upstream_repository or components.awx.repository
        ref = upstream_ref or components.awx.ref
        return await resolve_upstream_revision(source, repository, ref)

    @function
    async def build(
        self,
        source: dagger.Directory,
        resolved_revision: str = "",
        ssh_auth_sock: str = "",
    ) -> dagger.Container:
        """Build the AWX proof-of-concept image.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        resolved_revision : str
            Optional pre-resolved AWX commit SHA.
        ssh_auth_sock : str
            Optional SSH agent socket used for private Git access.

        Returns
        -------
        dagger.Container
            Built AWX control-plane container.
        """
        components = DEFAULT_COMPONENTS
        resolved_sha = await resolved_awx_revision(source, components, resolved_revision)
        return build_awx_image(awx_image_request(source, components, resolved_sha, ssh_auth_sock))

    @function
    async def verify(
        self,
        source: dagger.Directory,
        resolved_revision: str = "",
        ssh_auth_sock: str = "",
    ) -> str:
        """Build the image and run the runtime contract check.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        resolved_revision : str
            Optional pre-resolved AWX commit SHA.
        ssh_auth_sock : str
            Optional SSH agent socket used for private Git access.

        Returns
        -------
        str
            Output from the runtime contract check.
        """
        components = DEFAULT_COMPONENTS
        image = await self.build(
            source=source,
            resolved_revision=resolved_revision,
            ssh_auth_sock=ssh_auth_sock,
        )
        return await verify_awx_image(image, awx_image_ref(components)).stdout()

    @function
    async def export(
        self,
        source: dagger.Directory,
        image_ref: str = "",
        resolved_revision: str = "",
        ssh_auth_sock: str = "",
    ) -> dagger.File:
        """Build and verify an AWX image, then return it as an OCI tarball.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        image_ref : str
            Image reference to apply to the exported tarball.
        resolved_revision : str
            Optional pre-resolved AWX commit SHA.
        ssh_auth_sock : str
            Optional SSH agent socket used for private Git access.

        Returns
        -------
        dagger.File
            OCI tarball for the verified AWX image.
        """
        components = DEFAULT_COMPONENTS
        export_ref = image_ref or awx_image_ref(components)
        resolved_sha = await resolved_awx_revision(source, components, resolved_revision)
        image = build_awx_image(
            awx_image_request(source, components, resolved_sha, ssh_auth_sock, export_ref)
        )
        return verify_awx_image(image, export_ref).as_tarball()

    @function
    async def build_ui(
        self,
        source: dagger.Directory,
        resolved_revision: str = "",
    ) -> dagger.Directory:
        """Build the pinned AWX UI as a sideloadable static bundle.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        resolved_revision : str
            Optional pre-resolved AWX commit SHA.

        Returns
        -------
        dagger.Directory
            Directory containing the built AWX UI static files.
        """
        components = DEFAULT_COMPONENTS
        resolved_sha = await resolved_awx_revision(source, components, resolved_revision)
        image = build_awx_ui_bundle(awx_ui_bundle_request(source, components, resolved_sha))
        return image.directory(UI_STATIC_BUNDLE_PATH)

    @function
    async def export_ui(
        self,
        source: dagger.Directory,
        resolved_revision: str = "",
    ) -> dagger.Directory:
        """Build and return the AWX UI static bundle directory.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        resolved_revision : str
            Optional pre-resolved AWX commit SHA.

        Returns
        -------
        dagger.Directory
            Directory containing the built AWX UI static files.
        """
        return await self.build_ui(source=source, resolved_revision=resolved_revision)

    @function
    async def build_ee(self, source: dagger.Directory) -> dagger.Container:
        """Build the custom AWX execution environment image.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.

        Returns
        -------
        dagger.Container
            Built AWX execution environment container.
        """
        components = DEFAULT_COMPONENTS
        context = await build_ee_context(python_container(source))
        return build_ee_image(awx_ee_image_request(context, components))

    @function
    async def export_ee(
        self,
        source: dagger.Directory,
        image_ref: str = "",
    ) -> dagger.File:
        """Build and verify the custom AWX EE image as an OCI tarball.

        Parameters
        ----------
        source : dagger.Directory
            Repository source tree mounted into Dagger.
        image_ref : str
            Image reference to apply to the exported tarball.

        Returns
        -------
        dagger.File
            OCI tarball for the verified AWX execution environment image.
        """
        components = DEFAULT_COMPONENTS
        export_ref = image_ref or awx_ee_image_ref(components)
        image_name, image_tag = split_image_ref(export_ref)
        context = await build_ee_context(python_container(source))
        image = build_ee_image(
            awx_ee_image_request(context, components, image_name=image_name, image_tag=image_tag)
        )
        return verify_ee_image(image).as_tarball()


async def resolve_upstream_revision(
    source: dagger.Directory,
    upstream_repository: str,
    upstream_ref: str,
) -> str:
    """Resolve an AWX ref inside the Dagger Python tooling container.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.
    upstream_repository : str
        AWX Git repository to query.
    upstream_ref : str
        Branch, tag, or commit SHA to resolve.

    Returns
    -------
    str
        Concrete AWX commit SHA.
    """
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


async def resolved_awx_revision(
    source: dagger.Directory,
    components: Components,
    resolved_revision: str = "",
) -> str:
    """Return the supplied AWX revision or resolve the configured ref.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.
    components : Components
        Component manifest settings.
    resolved_revision : str
        Optional pre-resolved AWX commit SHA.

    Returns
    -------
    str
        Concrete AWX commit SHA.
    """
    if resolved_revision:
        return resolved_revision
    return await resolve_upstream_revision(source, components.awx.repository, components.awx.ref)


def awx_image_ref(components: Components) -> str:
    """Return the configured AWX image reference.

    Parameters
    ----------
    components : Components
        Component manifest settings.

    Returns
    -------
    str
        Configured AWX image reference.
    """
    return f"{components.images.name}:{components.images.tag}"


def awx_ee_image_ref(components: Components) -> str:
    """Return the configured AWX execution environment image reference.

    Parameters
    ----------
    components : Components
        Component manifest settings.

    Returns
    -------
    str
        Configured AWX execution environment image reference.
    """
    return f"{components.awx_ee.name}:{components.awx_ee.tag}"


def awx_image_request(
    source: dagger.Directory,
    components: Components,
    resolved_sha: str,
    ssh_auth_sock: str = "",
    image_ref: str = "",
) -> AwxImageBuildRequest:
    """Build an AWX image request from configured component settings.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.
    components : Components
        Component manifest settings.
    resolved_sha : str
        Concrete AWX commit SHA.
    ssh_auth_sock : str
        Optional SSH agent socket used for private Git access.
    image_ref : str
        Optional image reference override for export labels.

    Returns
    -------
    AwxImageBuildRequest
        Request object for the AWX image build helper.
    """
    image_name, image_tag = split_image_ref(image_ref or awx_image_ref(components))
    return AwxImageBuildRequest(
        source=source,
        awx_repo=components.awx.repository,
        awx_ref=components.awx.ref,
        resolved_sha=resolved_sha,
        awx_ui_repo=components.awx_ui.repository,
        awx_ui_ref=components.awx_ui.ref,
        awx_ui_delivery=components.awx_ui.delivery.value,
        image_name=image_name,
        image_tag=image_tag,
        platform=components.images.platform,
        base_image=components.images.base,
        receptor_image=components.images.receptor,
        python_constraints=components.python.constraints,
        ssh_auth_sock=ssh_auth_sock,
    )


def awx_ui_bundle_request(
    source: dagger.Directory,
    components: Components,
    resolved_sha: str,
) -> AwxUiBundleBuildRequest:
    """Build an AWX UI bundle request from configured component settings.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.
    components : Components
        Component manifest settings.
    resolved_sha : str
        Concrete AWX commit SHA.

    Returns
    -------
    AwxUiBundleBuildRequest
        Request object for the AWX UI bundle build helper.
    """
    return AwxUiBundleBuildRequest(
        source=source,
        awx_repo=components.awx.repository,
        awx_ref=components.awx.ref,
        resolved_sha=resolved_sha,
        awx_ui_repo=components.awx_ui.repository,
        awx_ui_ref=components.awx_ui.ref,
        bundle_name=components.awx_ui_bundle.name,
        bundle_tag=components.awx_ui_bundle.tag,
        platform=components.images.platform,
        base_image=components.images.base,
    )


def awx_ee_image_request(
    context: dagger.Directory,
    components: Components,
    image_name: str = "",
    image_tag: str = "",
) -> AwxEeImageBuildRequest:
    """Build an AWX EE request from configured component settings.

    Parameters
    ----------
    context : dagger.Directory
        Ansible Builder context directory.
    components : Components
        Component manifest settings.
    image_name : str
        Optional EE image name override.
    image_tag : str
        Optional EE image tag override.

    Returns
    -------
    AwxEeImageBuildRequest
        Request object for the AWX EE image build helper.
    """
    return AwxEeImageBuildRequest(
        context=context,
        image_name=image_name or components.awx_ee.name,
        image_tag=image_tag or components.awx_ee.tag,
        platform=components.awx_ee.platform,
        ee_base_image=components.awx_ee.base,
    )
