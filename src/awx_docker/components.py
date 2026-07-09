from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AwxSource:
    repository: str
    ref: str


@dataclass(frozen=True)
class AwxUiSource:
    repository: str
    ref: str
    delivery: str


@dataclass(frozen=True)
class ImageSettings:
    base: str
    receptor: str
    name: str
    tag: str
    platform: str


@dataclass(frozen=True)
class PythonSettings:
    constraints: str


@dataclass(frozen=True)
class ExecutionEnvironmentSettings:
    requirements: str


@dataclass(frozen=True)
class Components:
    schema_version: int
    awx: AwxSource
    awx_ui: AwxUiSource
    images: ImageSettings
    python: PythonSettings
    execution_environment: ExecutionEnvironmentSettings


def load_components_file(path: Path) -> Components:
    return load_components_toml(path.read_text())


def load_components_toml(text: str) -> Components:
    data = tomllib.loads(text)
    schema_version = _int(data, "schema_version")
    if schema_version != 1:
        raise ValueError(f"unsupported components schema_version: {schema_version}")

    awx = _table(data, "awx")
    awx_ui = _table(data, "awx_ui")
    images = _table(data, "images")
    python = _table(data, "python")
    execution_environment = _table(data, "execution_environment")

    return Components(
        schema_version=schema_version,
        awx=AwxSource(
            repository=_string(awx, "repository"),
            ref=_string(awx, "ref"),
        ),
        awx_ui=AwxUiSource(
            repository=_string(awx_ui, "repository"),
            ref=_string(awx_ui, "ref"),
            delivery=_string(awx_ui, "delivery"),
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
        execution_environment=ExecutionEnvironmentSettings(
            requirements=_string(execution_environment, "requirements"),
        ),
    )


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"components field {key!r} must be a table")
    return value


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"components field {key!r} must be a non-empty string")
    return value


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"components field {key!r} must be an integer")
    return value
