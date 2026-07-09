import subprocess
from pathlib import Path

from awx_docker.config import DEFAULT_AWX_UI_REF, DEFAULT_AWX_UI_REPO

ROOT = Path(__file__).resolve().parents[2]


def test_default_awx_ui_source_is_version_pinned() -> None:
    assert DEFAULT_AWX_UI_REPO == "https://github.com/ansible/ansible-ui.git"
    assert DEFAULT_AWX_UI_REF.startswith("v")
    assert DEFAULT_AWX_UI_REF != "main"


def test_dockerfile_prepares_awx_ui_source_before_make_ui() -> None:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()

    prepare = dockerfile.index("prepare-awx-ui-source")
    build = dockerfile.index("RUN make ui")

    assert prepare < build
    assert "ARG AWX_UI_REPO" in dockerfile
    assert "ARG AWX_UI_REF" in dockerfile


def test_awx_ui_prepare_script_fetches_requested_ref_without_pull() -> None:
    script = (ROOT / "docker/awx/bin/prepare-awx-ui-source").read_text()

    assert 'git -C "$ui_src" fetch --depth 1 origin "$AWX_UI_REF"' in script
    assert "git pull" not in script


def test_dockerfile_passes_python_constraints_to_awx_requirements() -> None:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    installer = (ROOT / "docker/awx/bin/install-awx-python-deps").read_text()

    assert "COPY docker/awx/constraints /tmp/requirements/constraints" in dockerfile
    assert (
        'AWX_PYTHON_CONSTRAINTS="/tmp/requirements/constraints/${AWX_PYTHON_CONSTRAINTS}"'
        in dockerfile
    )
    assert "render_yaml_constraints" in installer
    assert 'export PIP_CONSTRAINT="$pip_constraints"' in installer


def test_awx_python_yaml_constraints_render_to_pip_constraints(tmp_path: Path) -> None:
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
