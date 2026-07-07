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
