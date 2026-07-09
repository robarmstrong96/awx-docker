"""Dagger containers used for local checks."""

import dagger
from dagger import dag

from awx_docker.utilities.load_configuration import DEFAULT_TOOLING_UV_IMAGE


def python_container(source: dagger.Directory) -> dagger.Container:
    """Create the Python tooling container used by Dagger tasks."""
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


def tools_container(source: dagger.Directory) -> dagger.Container:
    """Create the lint container with shell tools installed."""
    return (
        python_container(source)
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
