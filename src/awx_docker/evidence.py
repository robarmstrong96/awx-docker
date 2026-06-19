import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_markdown(path: Path, title: str, rows: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for key, value in rows.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, str) and value.startswith("`") and value.endswith("`"):
            formatted = value
        elif isinstance(value, str):
            formatted = value
        else:
            formatted = str(value)
        lines.append(f"- {label}: {formatted}")
    path.write_text("\n".join(lines) + "\n")


def write_env(path: Path, values: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={str(value).replace(chr(10), ' ')}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n")
