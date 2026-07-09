import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_prepares_awx_ui_source_before_make_ui() -> None:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()

    prepare = dockerfile.index("prepare-awx-ui-source")
    build = dockerfile.index("make ui ;;")

    assert prepare < build


def test_dockerfile_supports_sideloaded_ui_delivery() -> None:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    dagger_module = (ROOT / "src/awx_docker/main.py").read_text()
    verifier = (ROOT / "docker/awx/bin/verify-runtime-contract").read_text()

    assert "ARG AWX_UI_DELIVERY=embedded" in dockerfile
    assert 'dagger.BuildArg("AWX_UI_DELIVERY", awx_ui_delivery)' in dagger_module
    assert "sideloaded)" in dockerfile
    assert "make ui ;;" in dockerfile
    assert "sideloaded)" in verifier


def test_awx_ui_prepare_script_fetches_requested_ref_without_pull() -> None:
    script = (ROOT / "docker/awx/bin/prepare-awx-ui-source").read_text()

    assert 'git -C "$ui_src" fetch --depth 1 origin "$AWX_UI_REF"' in script
    assert "printf 'embedded\\n'" in script
    assert "git pull" not in script


def test_dockerfile_passes_python_constraints_to_awx_requirements() -> None:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    installer = (ROOT / "docker/awx/bin/install-awx-python-deps").read_text()

    assert (
        'AWX_PYTHON_CONSTRAINTS="/tmp/requirements/constraints/${AWX_PYTHON_CONSTRAINTS}"'
        in dockerfile
    )
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
