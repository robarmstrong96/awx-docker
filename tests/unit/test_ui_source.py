"""Static tests for Docker build wiring and small shell helpers."""

import subprocess
from pathlib import Path

import pytest

from awx_docker.config import AwxUiDelivery
from awx_docker.utilities.file_util import load_components_toml

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_prepares_awx_ui_source_before_make_ui() -> None:
    """The pinned UI ref must be checked out before AWX runs make ui."""
    script = (ROOT / "docker/awx-ui/bin/prepare-delivery").read_text()

    prepare = script.index("prepare-awx-ui-source")
    build = script.index("make ui")

    assert prepare < build


def test_dockerfile_supports_sideloaded_ui_delivery() -> None:
    """Sideloaded UI mode should stay in shell helpers, not Dockerfile logic."""
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    awx_build = (ROOT / "src/awx_docker/builds/awx.py").read_text()
    delivery_script = (ROOT / "docker/awx-ui/bin/prepare-delivery").read_text()
    deps_script = (ROOT / "docker/awx-ui/bin/install-build-deps").read_text()
    verifier = (ROOT / "docker/awx/bin/verify-runtime-contract").read_text()

    assert "ARG AWX_UI_DELIVERY=embedded" in dockerfile
    assert "COPY docker/awx-ui/bin/prepare-delivery" in dockerfile
    assert "RUN /usr/local/libexec/awx-docker/install-awx-ui-build-deps" in dockerfile
    assert "RUN /usr/local/libexec/awx-docker/prepare-awx-ui-delivery" in dockerfile
    assert 'case "$AWX_UI_DELIVERY"' not in dockerfile
    assert 'dagger.BuildArg("AWX_UI_DELIVERY", awx_ui_delivery)' in awx_build
    assert "sideloaded)" in delivery_script
    assert "sideloaded)" in deps_script
    assert "sideloaded)" in verifier


def test_component_parser_uses_ui_delivery_enum() -> None:
    """The component manifest should parse UI delivery as an enum."""
    components = load_components_toml((ROOT / "config/components/components.toml").read_text())

    assert components.awx_ui.delivery is AwxUiDelivery.EMBEDDED


def test_component_parser_rejects_unknown_ui_delivery() -> None:
    """Unknown UI delivery modes should fail before Dagger reaches Docker."""
    manifest = (ROOT / "config/components/components.toml").read_text()

    with pytest.raises(ValueError, match="delivery.*embedded, sideloaded"):
        load_components_toml(manifest.replace('delivery = "embedded"', 'delivery = "bad"'))


def test_awx_ui_prepare_script_fetches_requested_ref_without_pull() -> None:
    """The UI source helper should fetch only the requested ref."""
    script = (ROOT / "docker/awx-ui/bin/prepare-source").read_text()

    assert 'git -C "$ui_src" fetch --depth 1 origin "$AWX_UI_REF"' in script
    assert "printf 'embedded\\n'" in script
    assert "git pull" not in script


def test_awx_ui_bundle_dockerfile_exports_static_assets() -> None:
    """The UI Dockerfile should produce a reusable static bundle directory."""
    dockerfile = (ROOT / "docker/awx-ui/Dockerfile").read_text()
    exporter = (ROOT / "docker/awx-ui/bin/export-static-bundle").read_text()

    assert "RUN /usr/local/libexec/awx-docker/export-awx-ui-static-bundle" in dockerfile
    assert "RUN /usr/local/libexec/awx-docker/verify-awx-ui-static-bundle" in dockerfile
    assert 'bundle_dir="${2:-/awx-ui-static}"' in exporter


def test_awx_ee_definition_pins_core_and_runner_once() -> None:
    """Core and runner pins belong in the Ansible Builder definition."""
    definition = (ROOT / "docker/awx-ee/execution-environment.yml").read_text()
    python_requirements = [
        line.strip()
        for line in (ROOT / "docker/awx-ee/requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert "version: 3" in definition
    assert "name: quay.io/ansible/ansible-runner:stable-2.15-devel" in definition
    assert "package_pip: ansible-core==2.15.13" in definition
    assert "package_pip: ansible-runner==2.4.0" in definition
    assert not any(line.startswith("ansible-core==") for line in python_requirements)
    assert not any(line.startswith("ansible-runner==") for line in python_requirements)


def test_dagger_exposes_ui_and_ee_builds() -> None:
    """The Dagger API should expose separate UI and EE build/export calls."""
    dagger_module = (ROOT / "src/awx_docker/main.py").read_text()
    ee_build = (ROOT / "src/awx_docker/builds/awx_ee.py").read_text()

    assert "async def build_ui(" in dagger_module
    assert "async def export_ui(" in dagger_module
    assert "async def build_ee(" in dagger_module
    assert "async def export_ee(" in dagger_module
    assert "ansible-builder" in ee_build


def test_dockerfile_passes_python_constraints_to_awx_requirements() -> None:
    """AWX Python constraints should be copied from config and passed to pip."""
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    installer = (ROOT / "docker/awx/bin/install-awx-python-deps").read_text()

    assert (
        'AWX_PYTHON_CONSTRAINTS="/tmp/requirements/constraints/${AWX_PYTHON_CONSTRAINTS}"'
        in dockerfile
    )
    assert "COPY config/awx/constraints /tmp/requirements/constraints" in dockerfile
    assert 'export PIP_CONSTRAINT="$pip_constraints"' in installer


def test_dockerfile_copies_awx_package_repos_from_config() -> None:
    """AWX-specific RPM repo files should come from config/awx."""
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()

    assert "COPY config/awx/repos/ansible-rsyslog-epel-9.repo" in dockerfile


def test_awx_python_yaml_constraints_render_to_pip_constraints(tmp_path: Path) -> None:
    """The Bash renderer should turn the YAML list into pip constraint lines."""
    source = tmp_path / "constraints.yaml"
    target = tmp_path / "constraints.txt"
    source.write_text(
        "\n".join(
            [
                "---",
                "constraints:",
                '  - "ansible-core==2.16.14"',
                "  - ansible-runner==2.4.0",
                "",
            ]
        )
    )

    subprocess.run(
        [
            "bash",
            str(ROOT / "docker/awx/bin/install-awx-python-deps"),
            "--render-constraints",
            str(source),
            str(target),
        ],
        check=True,
    )

    assert target.read_text().splitlines() == [
        "ansible-core==2.16.14",
        "ansible-runner==2.4.0",
    ]
