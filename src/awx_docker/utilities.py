"""Parsing helpers for the shared component version manifest."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AwxSource:
    """Upstream AWX repository and ref to build."""

    repository: str
    ref: str


@dataclass(frozen=True)
class AwxUiSource:
    """Pinned AWX UI source and delivery mode."""

    repository: str
    ref: str
    delivery: str


@dataclass(frozen=True)
class AwxUiBundleSettings:
    """Defaults for the exported static UI bundle."""

    name: str
    tag: str
    export_path: str


@dataclass(frozen=True)
class AwxEeSettings:
    """Defaults for the starter AWX execution environment image."""

    base: str
    name: str
    tag: str
    platform: str


@dataclass(frozen=True)
class ImageSettings:
    """Defaults for the AWX control-plane image build."""

    base: str
    receptor: str
    name: str
    tag: str
    platform: str


@dataclass(frozen=True)
class PythonSettings:
    """Python dependency knobs owned by this wrapper."""

    constraints: str


@dataclass(frozen=True)
class ToolingSettings:
    """Local tooling versions used by Dagger checks."""

    python: str
    uv_image: str


@dataclass(frozen=True)
class Components:
    """Typed view of config/components/components.toml."""

    schema_version: int
    awx: AwxSource
    awx_ui: AwxUiSource
    awx_ui_bundle: AwxUiBundleSettings
    awx_ee: AwxEeSettings
    images: ImageSettings
    python: PythonSettings
    tooling: ToolingSettings


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
            delivery=_choice(awx_ui, "delivery", {"embedded", "sideloaded"}),
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


def _choice(data: dict[str, Any], key: str, choices: set[str]) -> str:
    """Read a required string that must be one of a known set."""
    value = _string(data, key)
    if value not in choices:
        expected = ", ".join(sorted(choices))
        raise ValueError(f"components field {key!r} must be one of: {expected}")
    return value


def _int(data: dict[str, Any], key: str) -> int:
    """Read a required TOML integer."""
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"components field {key!r} must be an integer")
    return value
