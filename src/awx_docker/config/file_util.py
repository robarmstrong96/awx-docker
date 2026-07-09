"""Parser for config/components/components.toml."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any

from awx_docker.config.awx import AwxSource
from awx_docker.config.awx_ee import AwxEeSettings
from awx_docker.config.awx_ui import AwxUiDelivery, AwxUiSource
from awx_docker.config.awx_ui_bundle import AwxUiBundleSettings
from awx_docker.config.components import Components
from awx_docker.config.image import ImageSettings
from awx_docker.config.python import PythonSettings
from awx_docker.config.tooling import ToolingSettings


def load_components_file(path: Path) -> Components:
    """Read and parse a component manifest from disk."""
    return load_components_toml(path.read_text())


def load_components_toml(text: str) -> Components:
    """Parse component TOML into typed settings with simple validation."""
    data = tomllib.loads(text)
    schema_version = _int(data, "schema_version")
    if schema_version != 1:
        raise ValueError(f"unsupported components schema_version: {schema_version}")

    awx = _table(data, "awx")
    awx_ui = _table(data, "awx_ui")
    awx_ui_bundle = _table(data, "awx_ui_bundle")
    awx_ee = _table(data, "awx_ee")
    images = _table(data, "images")
    python = _table(data, "python")
    tooling = _table(data, "tooling")

    return Components(
        schema_version=schema_version,
        awx=AwxSource(
            repository=_string(awx, "repository"),
            ref=_string(awx, "ref"),
        ),
        awx_ui=AwxUiSource(
            repository=_string(awx_ui, "repository"),
            ref=_string(awx_ui, "ref"),
            delivery=_enum(awx_ui, "delivery", AwxUiDelivery),
        ),
        awx_ui_bundle=AwxUiBundleSettings(
            name=_string(awx_ui_bundle, "name"),
            tag=_string(awx_ui_bundle, "tag"),
            export_path=_string(awx_ui_bundle, "export_path"),
        ),
        awx_ee=AwxEeSettings(
            base=_string(awx_ee, "base"),
            name=_string(awx_ee, "name"),
            tag=_string(awx_ee, "tag"),
            platform=_string(awx_ee, "platform"),
        ),
        images=ImageSettings(
            base=_string(images, "base"),
            receptor=_string(images, "receptor"),
            name=_string(images, "name"),
            tag=_string(images, "tag"),
            platform=_string(images, "platform"),
        ),
        python=PythonSettings(
            constraints=_string(python, "constraints"),
        ),
        tooling=ToolingSettings(
            python=_string(tooling, "python"),
            uv_image=_string(tooling, "uv_image"),
        ),
    )


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Read a required TOML table."""
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"components field {key!r} must be a table")
    return value


def _string(data: dict[str, Any], key: str) -> str:
    """Read a required non-empty TOML string."""
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"components field {key!r} must be a non-empty string")
    return value


def _enum[T: Enum](data: dict[str, Any], key: str, enum_type: type[T]) -> T:
    """Read a required string as an enum value."""
    value = _string(data, key)
    try:
        return enum_type(value)
    except ValueError as exc:
        expected = ", ".join(item.value for item in enum_type)
        raise ValueError(f"components field {key!r} must be one of: {expected}") from exc


def _int(data: dict[str, Any], key: str) -> int:
    """Read a required TOML integer."""
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"components field {key!r} must be an integer")
    return value
