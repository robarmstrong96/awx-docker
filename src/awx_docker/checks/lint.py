"""Lint, format, and unit-test wiring for Dagger."""

import dagger

from awx_docker.checks.tool_container import python_container, tools_container
from awx_docker.utilities.load_configuration import DEFAULT_TOOLING_PYTHON

SHELLCHECK_PATHS = [
    "scripts/runtime-entrypoint.sh",
    "docker/awx-ui/bin/export-static-bundle",
    "docker/awx-ui/bin/install-build-deps",
    "docker/awx-ui/bin/prepare-delivery",
    "docker/awx-ui/bin/prepare-source",
    "docker/awx-ui/bin/verify-static-bundle",
    "docker/awx/bin/install-rpms",
    "docker/awx/bin/prepare-awx-source",
    "docker/awx/bin/install-awx-python-deps",
    "docker/awx/bin/synthesize-awx-dist-info",
    "docker/awx/bin/prepare-runtime-layout",
    "docker/awx/bin/verify-runtime-contract",
]


def uv_python(*args: str) -> list[str]:
    """Build a uv command that runs Python with the configured version.

    Parameters
    ----------
    *args : str
        Arguments passed to Python after uv selects the configured version.

    Returns
    -------
    list[str]
        Command argv suitable for ``Container.with_exec``.
    """
    return ["uv", "run", "--python", DEFAULT_TOOLING_PYTHON, "python", *args]


def format_container(source: dagger.Directory) -> dagger.Container:
    """Attach Ruff formatting to a Python tooling container.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.

    Returns
    -------
    dagger.Container
        Container with Ruff formatting appended.
    """
    return python_container(source).with_exec(["uv", "run", "ruff", "format", "."])


def test_container(source: dagger.Directory) -> dagger.Container:
    """Attach unit tests to a Python tooling container.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.

    Returns
    -------
    dagger.Container
        Container with the unit test command appended.
    """
    return python_container(source).with_exec(uv_python("-m", "pytest", "tests/unit"))


def lint_container(source: dagger.Directory) -> dagger.Container:
    """Attach formatter, linter, and ShellCheck commands to a container.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.

    Returns
    -------
    dagger.Container
        Container with all lint commands appended.
    """
    ctr = tools_container(source)
    ctr = ctr.with_exec(["uv", "run", "ruff", "format", "--check", "."])
    ctr = ctr.with_exec(["uv", "run", "ruff", "check", "."])
    for path in SHELLCHECK_PATHS:
        ctr = ctr.with_exec(["shellcheck", path])
    return ctr


def check_container(source: dagger.Directory) -> dagger.Container:
    """Attach all default checks to a container.

    Parameters
    ----------
    source : dagger.Directory
        Repository source tree mounted into Dagger.

    Returns
    -------
    dagger.Container
        Container with lint and unit test commands appended.
    """
    return lint_container(source).with_exec(uv_python("-m", "pytest", "tests/unit"))
