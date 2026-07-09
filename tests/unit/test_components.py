import re
from pathlib import Path

import pytest

from awx_docker.components import load_components_file, load_components_toml
from awx_docker.config import (
    DEFAULT_AWX_PYTHON_CONSTRAINTS,
    DEFAULT_AWX_REF,
    DEFAULT_AWX_REPO,
    DEFAULT_AWX_UI_REF,
    DEFAULT_AWX_UI_REPO,
    DEFAULT_BASE_IMAGE,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_PLATFORM,
    DEFAULT_RECEPTOR_IMAGE,
)

ROOT = Path(__file__).resolve().parents[2]


def dockerfile_arg_defaults() -> dict[str, str]:
    dockerfile = (ROOT / "docker/awx/Dockerfile").read_text()
    return dict(re.findall(r"^ARG ([A-Z0-9_]+)=([^\n]+)$", dockerfile, flags=re.MULTILINE))


def test_components_manifest_is_default_version_source() -> None:
    components = load_components_file(ROOT / "components.toml")

    assert DEFAULT_AWX_REPO == components.awx.repository
    assert DEFAULT_AWX_REF == components.awx.ref
    assert DEFAULT_AWX_UI_REPO == components.awx_ui.repository
    assert DEFAULT_AWX_UI_REF == components.awx_ui.ref
    assert DEFAULT_BASE_IMAGE == components.images.base
    assert DEFAULT_RECEPTOR_IMAGE == components.images.receptor
    assert DEFAULT_IMAGE_NAME == components.images.name
    assert DEFAULT_IMAGE_TAG == components.images.tag
    assert DEFAULT_PLATFORM == components.images.platform
    assert DEFAULT_AWX_PYTHON_CONSTRAINTS == components.python.constraints


def test_dockerfile_fallback_args_match_components_manifest() -> None:
    components = load_components_file(ROOT / "components.toml")
    args = dockerfile_arg_defaults()

    assert args["CENTOS_STREAM_IMAGE"] == components.images.base
    assert args["AWX_REPO"] == components.awx.repository
    assert args["AWX_REF"] == components.awx.ref
    assert args["AWX_REQUESTED_REF"] == components.awx.ref
    assert args["AWX_UI_REPO"] == components.awx_ui.repository
    assert args["AWX_UI_REF"] == components.awx_ui.ref
    assert args["RECEPTOR_IMAGE"] == components.images.receptor
    assert args["AWX_PYTHON_CONSTRAINTS"] == components.python.constraints


def test_components_manifest_rejects_unsupported_schema() -> None:
    with pytest.raises(ValueError, match="unsupported components schema_version"):
        load_components_toml("schema_version = 2\n")
